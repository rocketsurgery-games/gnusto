"""
Scene renderer for generating illustrations from render specs.

This module bridges the Grue render spec system with the filfre image generator,
handling recursive object resolution, caching, and integration with the game loop.

Usage:
    renderer = SceneRenderer(
        runtime=game_runtime,
        cache_dir="cache/renders",
        assets_dir="games/mygame/assets",
    )

    # Render the current room
    image_path = renderer.render_room("@cellar")

    # Render a specific object
    image_path = renderer.render_object("@lantern")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Callable
import hashlib

from grue.render import evaluate_render_spec, has_render_spec, get_render_spec, RenderResult
from grue.render_cache import RenderCache, hash_pil_image

if TYPE_CHECKING:
    from grue.runtime import GrueRuntime
    from PIL import Image


@dataclass
class RenderRequest:
    """Request to render an entity (room or object)."""
    entity_name: str
    prompt: str
    ref_paths: list[str] = field(default_factory=list)
    ref_images: list["Image"] = field(default_factory=list)  # PIL images from recursive renders
    ref_size: int = 384
    include_contents: bool = False


class SceneRenderer:
    """Renders scenes from Grue render specs using filfre."""

    def __init__(
        self,
        runtime: "GrueRuntime",
        renders_dir: str | Path = "assets/renders",
        assets_dir: str | Path | None = None,
        model_version: str = "flux2-klein-4b",
        default_ref_size: int = 384,
        pipeline: Optional[Callable] = None,
    ):
        """Initialize the scene renderer.

        Args:
            runtime: The Grue game runtime
            renders_dir: Base directory for renders (frozen + cache)
            assets_dir: Directory for asset files (reference images)
            model_version: Model version for cache invalidation
            default_ref_size: Default size for reference images
            pipeline: Optional pre-loaded filfre pipeline (for performance)
        """
        self.runtime = runtime
        self.cache = RenderCache(renders_dir, model_version=model_version)
        self.assets_dir = Path(assets_dir) if assets_dir else None
        self.default_ref_size = default_ref_size
        self._pipeline = pipeline
        self._render_depth = 0  # Track recursion depth
        self._max_depth = 3  # Max composition layers

    def render_room(self, room_id: str) -> Path | None:
        """Render an illustration for a room.

        Args:
            room_id: The room identifier (e.g., "@cellar")

        Returns:
            Path to the rendered image, or None if no render spec or rendering failed
        """
        room = self.runtime.world.rooms.get(room_id)
        if not room or not has_render_spec(room):
            return None

        return self._render_entity(room_id, room)

    def render_object(self, object_id: str) -> Path | None:
        """Render an illustration for an object.

        Args:
            object_id: The object identifier (e.g., "@lantern")

        Returns:
            Path to the rendered image, or None if no render spec or rendering failed
        """
        obj = self.runtime.world.objects.get(object_id)
        if not obj or not has_render_spec(obj):
            return None

        return self._render_entity(object_id, obj)

    def render_current_room(self) -> Path | None:
        """Render the player's current room.

        Returns:
            Path to the rendered image, or None if not renderable
        """
        room_id = self.runtime.get_player_room()
        return self.render_room(room_id)

    def _render_entity(self, entity_id: str, entity) -> Path | None:
        """Render an entity (room or object) from its render spec.

        Args:
            entity_id: The entity identifier
            entity: The GrueRoom or GrueObject

        Returns:
            Path to the rendered image, or None on failure
        """
        # Check recursion depth
        if self._render_depth >= self._max_depth:
            return None

        spec = get_render_spec(entity)
        if spec is None:
            return None

        # Evaluate the render spec
        try:
            result = evaluate_render_spec(
                spec,
                entity_id,
                self.runtime,
                functions=self.runtime._functions if hasattr(self.runtime, '_functions') else None,
            )
        except Exception as e:
            print(f"Warning: Failed to evaluate render spec for {entity_id}: {e}")
            return None

        if not result.prompt:
            return None

        # Build the render request
        request = self._build_request(entity_id, result)

        # Check cache
        cache_key, ref_hashes = self._compute_cache_key(request)
        cached = self.cache.get(cache_key, entity=entity_id)
        if cached:
            return cached

        # Generate the image
        image = self._generate_image(request)
        if image is None:
            return None

        # Save to cache with logging
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            image.save(f.name)
            return self.cache.put(
                cache_key,
                entity=entity_id,
                image_path=f.name,
                prompt=request.prompt,
                ref_paths=request.ref_paths,
                ref_hashes=ref_hashes,
                copy=False,
            )

    def _build_request(self, entity_id: str, result: RenderResult) -> RenderRequest:
        """Build a RenderRequest from a RenderResult.

        Resolves object references recursively.
        """
        # Prepend world render style if configured
        prompt = result.prompt
        if self.runtime.world.render_style:
            prompt = f"{self.runtime.world.render_style} {prompt}"

        request = RenderRequest(
            entity_name=entity_id,
            prompt=prompt,
            ref_size=result.ref_size or self.default_ref_size,
            include_contents=result.include_contents,
        )

        # Resolve static reference paths
        for ref_path in result.ref_paths:
            full_path = self._resolve_ref_path(ref_path)
            if full_path and full_path.exists():
                request.ref_paths.append(str(full_path))

        # Resolve object references recursively
        self._render_depth += 1
        try:
            for obj_ref in result.object_refs:
                ref_image = self._resolve_object_ref(obj_ref.name)
                if ref_image:
                    request.ref_images.append(ref_image)
        finally:
            self._render_depth -= 1

        # Resolve anchors (re-include atomic refs)
        for anchor in result.anchors:
            anchor_image = self._resolve_object_ref(anchor)
            if anchor_image:
                request.ref_images.append(anchor_image)

        # Include contents if requested (for rooms)
        if result.include_contents:
            self._add_contents(entity_id, request)

        return request

    def _resolve_ref_path(self, ref_path: str) -> Path | None:
        """Resolve a reference path to an absolute path."""
        if self.assets_dir:
            full = self.assets_dir / ref_path
            if full.exists():
                return full
        # Try as-is
        path = Path(ref_path)
        if path.exists():
            return path
        return None

    def _resolve_object_ref(self, object_id: str) -> "Image | None":
        """Resolve an object reference to a PIL Image.

        This may trigger recursive rendering if the object has a render spec.
        """
        from PIL import Image

        # First, try to render the object (recursive)
        obj = self.runtime.world.objects.get(object_id)
        if obj and has_render_spec(obj):
            rendered_path = self._render_entity(object_id, obj)
            if rendered_path:
                return Image.open(rendered_path).convert("RGB")

        # Fall back to static asset
        if self.assets_dir:
            # Try common naming conventions
            base_name = object_id.lstrip("@")
            for ext in (".png", ".jpg", ".jpeg"):
                for subdir in ("objects", "atomics", ""):
                    path = self.assets_dir / subdir / f"{base_name}{ext}"
                    if path.exists():
                        return Image.open(path).convert("RGB")

        return None

    def _add_contents(self, room_id: str, request: RenderRequest) -> None:
        """Add rendered images of objects in a room to the request."""
        from PIL import Image

        # Get objects at this location
        for obj_name, obj in self.runtime.world.objects.items():
            if obj.location == room_id:
                obj_image = self._resolve_object_ref(obj_name)
                if obj_image:
                    request.ref_images.append(obj_image)

    def _compute_cache_key(self, request: RenderRequest) -> tuple[str, list[str]]:
        """Compute cache key for a render request.

        Returns:
            Tuple of (cache_key, ref_hashes) - ref_hashes needed for logging
        """
        # Collect hashes for reference images
        ref_hashes = []

        # Hash static ref paths
        for path in request.ref_paths:
            ref_hashes.append(self.cache._hash_file(Path(path)))

        # Hash PIL images
        for img in request.ref_images:
            ref_hashes.append(hash_pil_image(img))

        key = self.cache.compute_key(
            prompt=request.prompt,
            ref_hashes=ref_hashes if ref_hashes else None,
        )
        return key, ref_hashes

    def _generate_image(self, request: RenderRequest) -> "Image | None":
        """Generate an image using filfre.

        Args:
            request: The render request

        Returns:
            PIL Image or None on failure
        """
        from PIL import Image
        import torch

        # Get or load the pipeline
        pipeline = self._get_pipeline()
        if pipeline is None:
            return None

        # Prepare reference images
        refs = []

        # Load static refs
        for path in request.ref_paths:
            img = Image.open(path).convert("RGB")
            img = img.resize((request.ref_size, request.ref_size), Image.LANCZOS)
            refs.append(img)

        # Resize dynamic refs
        for img in request.ref_images:
            resized = img.resize((request.ref_size, request.ref_size), Image.LANCZOS)
            refs.append(resized)

        # Generate
        try:
            generator = torch.Generator(device="cuda").manual_seed(0)
            kwargs = {
                "prompt": request.prompt,
                "height": 512,
                "width": 512,
                "num_inference_steps": 4,
                "generator": generator,
            }
            if refs:
                kwargs["image"] = refs if len(refs) > 1 else refs[0]

            result = pipeline(**kwargs)
            return result.images[0]

        except Exception as e:
            print(f"Warning: Image generation failed: {e}")
            return None

    def _get_pipeline(self):
        """Get or lazily load the filfre pipeline."""
        if self._pipeline is not None:
            return self._pipeline

        try:
            from filfre.cli import get_pipeline
            self._pipeline, _ = get_pipeline(dtype="bf16", verbose=False)
            return self._pipeline
        except Exception as e:
            print(f"Warning: Failed to load filfre pipeline: {e}")
            return None

    def set_pipeline(self, pipeline) -> None:
        """Set a pre-loaded pipeline (for sharing across renders)."""
        self._pipeline = pipeline
