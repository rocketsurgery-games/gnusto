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

from grue.render import evaluate_render_spec, has_render_spec, get_render_spec, RenderResult, ObjectRef, ContentsMarker
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
        verbose: bool = False,
    ):
        """Initialize the scene renderer.

        Args:
            runtime: The Grue game runtime
            renders_dir: Base directory for renders (frozen + cache)
            assets_dir: Directory for asset files (reference images)
            model_version: Model version for cache invalidation
            default_ref_size: Default size for reference images
            pipeline: Optional pre-loaded filfre pipeline (for performance)
            verbose: Print render request details (prompt, refs, etc.)
        """
        self.runtime = runtime
        self.cache = RenderCache(renders_dir, model_version=model_version)
        self.assets_dir = Path(assets_dir) if assets_dir else None
        self.verbose = verbose
        self.default_ref_size = default_ref_size
        self._pipeline = pipeline
        self._render_depth = 0  # Track recursion depth
        self._max_depth = 3  # Max composition layers

    def _log(self, msg: str, indent: int = 0) -> None:
        """Print verbose log message if verbose mode enabled."""
        if self.verbose:
            prefix = "  " * indent
            print(f"{prefix}{msg}")

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

    def render_reference(self, ref_id: str) -> Path | None:
        """Render an illustration for a static reference.

        Args:
            ref_id: The reference identifier (e.g., "@terminal-room-bg")

        Returns:
            Path to the rendered image, or None if no render spec or rendering failed
        """
        ref = self.runtime.world.references.get(ref_id)
        if not ref or not has_render_spec(ref):
            return None

        return self._render_entity(ref_id, ref)

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
        depth_indent = self._render_depth

        # Check recursion depth
        if self._render_depth >= self._max_depth:
            self._log(f"Max depth reached for {entity_id}", depth_indent)
            return None

        spec = get_render_spec(entity)
        if spec is None:
            self._log(f"No render spec for {entity_id}", depth_indent)
            return None

        self._log(f"Evaluating render spec for {entity_id}", depth_indent)
        self._log(f"Raw spec: {spec}", depth_indent + 1)

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

        self._log(f"Evaluated result:", depth_indent + 1)
        self._log(f"  prompt_parts: {self._format_prompt_parts(result.prompt_parts)}", depth_indent + 1)
        self._log(f"  ref_paths: {result.ref_paths}", depth_indent + 1)

        # Build the render request (assembles prompt from parts)
        request = self._build_request(entity_id, result)

        if not request.prompt:
            print(f"Warning: No prompt assembled for {entity_id}")
            print(f"  Hint: Ensure referenced entities have :description fields")
            return None

        self._log(f"Built request:", depth_indent + 1)
        self._log(f"  final prompt: {request.prompt[:200]}{'...' if len(request.prompt) > 200 else ''}", depth_indent + 1)
        self._log(f"  ref_paths: {request.ref_paths}", depth_indent + 1)
        self._log(f"  ref_images: {len(request.ref_images)} image(s)", depth_indent + 1)

        # Check cache
        cache_key, ref_hashes = self._compute_cache_key(request)
        cached = self.cache.get(cache_key, entity=entity_id)
        if cached:
            self._log(f"Cache hit: {cached}", depth_indent + 1)
            return cached

        self._log(f"Cache miss, generating...", depth_indent + 1)

        # Generate the image
        image = self._generate_image(request)
        if image is None:
            return None

        # Save to cache with logging
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            image.save(f.name)
            result_path = self.cache.put(
                cache_key,
                entity=entity_id,
                image_path=f.name,
                prompt=request.prompt,
                ref_paths=request.ref_paths,
                ref_hashes=ref_hashes,
                copy=False,
            )
            self._log(f"Saved to cache: {result_path}", depth_indent + 1)
            return result_path

    def _format_prompt_parts(self, parts: list) -> str:
        """Format prompt_parts for verbose logging."""
        formatted = []
        for part in parts:
            if isinstance(part, str):
                text = part[:30] + "..." if len(part) > 30 else part
                formatted.append(f'"{text}"')
            elif isinstance(part, ObjectRef):
                formatted.append(part.name)
            elif isinstance(part, ContentsMarker):
                formatted.append(":contents")
            else:
                formatted.append(str(part))
        return "[" + ", ".join(formatted) + "]"

    def _build_request(self, entity_id: str, result: RenderResult) -> RenderRequest:
        """Build a RenderRequest from a RenderResult.

        Assembles the prompt from prompt_parts by resolving:
        - Strings: added directly to prompt
        - ObjectRefs: contribute :description to prompt + rendered image as ref
        - ContentsMarker: contributes contained objects' :descriptions + images
        """
        request = RenderRequest(
            entity_name=entity_id,
            prompt="",  # Will be assembled below
            ref_size=result.ref_size or self.default_ref_size,
        )

        # Resolve static reference paths (these don't contribute to prompt)
        for ref_path in result.ref_paths:
            full_path = self._resolve_ref_path(ref_path)
            if full_path and full_path.exists():
                request.ref_paths.append(str(full_path))

        # Assemble prompt from parts and collect reference images
        prompt_texts: list[str] = []

        self._render_depth += 1
        try:
            for part in result.prompt_parts:
                if isinstance(part, str):
                    # Literal text
                    prompt_texts.append(part)

                elif isinstance(part, ObjectRef):
                    # Get :description and render image
                    desc = self._get_entity_description(part.name)
                    if desc:
                        prompt_texts.append(desc)

                    ref_image = self._resolve_object_ref(part.name)
                    if ref_image:
                        request.ref_images.append(ref_image)

                elif isinstance(part, ContentsMarker):
                    # Get contained objects' descriptions and images
                    content_descs, content_images = self._resolve_contents(entity_id)
                    if content_descs:
                        prompt_texts.append(", ".join(content_descs))
                    request.ref_images.extend(content_images)

        finally:
            self._render_depth -= 1

        # Resolve anchors (re-include atomic refs)
        for anchor in result.anchors:
            anchor_image = self._resolve_object_ref(anchor)
            if anchor_image:
                request.ref_images.append(anchor_image)

        # Join prompt parts
        prompt = " ".join(text.strip() for text in prompt_texts if text.strip())

        # Prepend world render style if configured
        if prompt and self.runtime.world.render_style:
            prompt = f"STYLE: {self.runtime.world.render_style}\n{prompt}"

        request.prompt = prompt
        return request

    def _get_entity_description(self, entity_id: str) -> str | None:
        """Get the :description from an entity.

        For objects/rooms, uses their :description field.
        For references, uses their :description field.

        Args:
            entity_id: The entity identifier (e.g., "@terminal-room-bg")

        Returns:
            The description string, or None if not found
        """
        # Check objects first
        obj = self.runtime.world.objects.get(entity_id)
        if obj and obj.description:
            # Evaluate if it's a function
            desc = self._eval_description(obj.description, entity_id)
            if desc:
                return desc

        # Check references
        ref = self.runtime.world.references.get(entity_id)
        if ref and ref.description:
            return ref.description

        # Check rooms
        room = self.runtime.world.rooms.get(entity_id)
        if room and room.description:
            desc = self._eval_description(room.description, entity_id)
            if desc:
                return desc

        return None

    def _eval_description(self, desc_expr, entity_id: str) -> str | None:
        """Evaluate a description expression (might be string or fn)."""
        if isinstance(desc_expr, str):
            return desc_expr

        # If it's a function expression, evaluate it
        from grue.sexpr import SList, Symbol
        if isinstance(desc_expr, SList) and len(desc_expr) >= 1:
            first = desc_expr[0]
            if isinstance(first, Symbol) and first.name == "fn":
                from grue.expr import ExprEvaluator, Environment
                evaluator = ExprEvaluator(
                    self.runtime,
                    self.runtime._functions if hasattr(self.runtime, '_functions') else {}
                )
                env = Environment(bindings={"self": entity_id})
                try:
                    result = evaluator.eval(desc_expr, env)
                    # Result should be a callable, call it with no args
                    if callable(result):
                        return str(result())
                    return str(result) if result else None
                except Exception:
                    return None

        return str(desc_expr) if desc_expr else None

    def _resolve_contents(self, location_id: str) -> tuple[list[str], list["Image"]]:
        """Resolve contained objects to descriptions and images.

        Args:
            location_id: The location (room) ID

        Returns:
            Tuple of (descriptions, images)
        """
        descriptions: list[str] = []
        images: list["Image"] = []

        for obj_name, obj in self.runtime.world.objects.items():
            if obj.location == location_id:
                # Get description
                desc = self._get_entity_description(obj_name)
                if desc:
                    descriptions.append(desc)

                # Render object
                if has_render_spec(obj):
                    ref_image = self._resolve_object_ref(obj_name)
                    if ref_image:
                        images.append(ref_image)

        return descriptions, images

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

        This may trigger recursive rendering if the object/reference has a render spec.
        Checks objects first, then references, then falls back to static assets.
        """
        from PIL import Image

        # First, try to render the object (recursive)
        obj = self.runtime.world.objects.get(object_id)
        if obj and has_render_spec(obj):
            rendered_path = self._render_entity(object_id, obj)
            if rendered_path:
                return Image.open(rendered_path).convert("RGB")

        # Try to render a reference (static render asset)
        ref = self.runtime.world.references.get(object_id)
        if ref and has_render_spec(ref):
            rendered_path = self._render_entity(object_id, ref)
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
            self._pipeline, _ = get_pipeline(dtype="bf16", quiet=True)
            return self._pipeline
        except Exception as e:
            print(f"Warning: Failed to load filfre pipeline: {e}")
            return None

    def set_pipeline(self, pipeline) -> None:
        """Set a pre-loaded pipeline (for sharing across renders)."""
        self._pipeline = pipeline
