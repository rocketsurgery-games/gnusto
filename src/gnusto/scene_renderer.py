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

from grue.render import evaluate_render_spec, has_render_spec, get_render_spec, RenderResult, ObjectRef, ContentsMarker, ThroughMarker
from grue.render_cache import RenderCache, hash_pil_image
from gnusto.terminal_images import display_image, display_pil_image, is_supported as terminal_images_supported

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
    ref_image_names: list[str] = field(default_factory=list)  # Entity IDs for ref_images
    ref_size: int = 384


class SceneRenderer:
    """Renders scenes from Grue render specs using image generation backends."""

    def __init__(
        self,
        runtime: "GrueRuntime",
        renders_dir: str | Path = "assets/renders",
        assets_dir: str | Path | None = None,
        model: str = "nanobanana",
        default_ref_size: int = 384,
        pipeline: Optional[Callable] = None,
        verbose: bool = False,
    ):
        """Initialize the scene renderer.

        Args:
            runtime: The Grue game runtime
            renders_dir: Base directory for renders (frozen + cache)
            assets_dir: Directory for asset files (reference images)
            model: Image generation model ("flux" or "nanobanana")
            default_ref_size: Default size for reference images
            pipeline: Optional pre-loaded filfre pipeline (for flux)
            verbose: Print render request details (prompt, refs, etc.)
        """
        from filfre.cli import MODEL_VERSIONS
        self.runtime = runtime
        self.model = model
        model_version = MODEL_VERSIONS.get(model, model)
        self.cache = RenderCache(renders_dir, model_version=model_version)
        self.assets_dir = Path(assets_dir) if assets_dir else None
        self.verbose = verbose
        self.default_ref_size = default_ref_size
        self._pipeline = pipeline
        self._render_depth = 0  # Track recursion depth
        self._max_depth = 5  # Max composition layers (room -> through -> room -> contents -> object)

    def _log(self, msg: str, indent: int = 0) -> None:
        """Print verbose log message if verbose mode enabled."""
        if self.verbose:
            prefix = "  " * indent
            print(f"{prefix}{msg}")

    def _log_render_request(self, entity_id: str, request: "RenderRequest", indent: int = 0) -> None:
        """Log a render request in a clean, readable format with image previews."""
        if not self.verbose:
            return

        prefix = "  " * indent

        # Show full prompt for top-level, truncated for sub-renders
        prompt = request.prompt
        if indent > 0 and len(prompt) > 300:
            prompt = prompt[:300] + "..."

        print(f"{prefix}{entity_id}:")
        print(f"{prefix}  prompt: {prompt}")

        # Show reference images with previews
        has_refs = request.ref_paths or request.ref_images
        if has_refs:
            print(f"{prefix}  refs:")

            # Show static ref paths with thumbnails
            for path in request.ref_paths:
                name = Path(path).name
                print(f"{prefix}    - {name}")
                if terminal_images_supported():
                    display_image(path, width=20)

            # Show rendered ref images with thumbnails
            for i, img in enumerate(request.ref_images):
                name = request.ref_image_names[i] if i < len(request.ref_image_names) else f"[rendered #{i+1}]"
                print(f"{prefix}    - {name}")
                if terminal_images_supported():
                    # Resize to half for preview
                    thumb = img.copy()
                    thumb.thumbnail((256, 256))
                    display_pil_image(thumb, width=20)
        else:
            print(f"{prefix}  refs: none")

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

        # Build the render request (assembles prompt from parts)
        request = self._build_request(entity_id, result)

        # Handle pure :ref specs (static image, no generation needed)
        if not request.prompt and request.ref_paths:
            # The entity's "render" is just a static file reference
            static_path = Path(request.ref_paths[0])
            if static_path.exists():
                self._log(f"{entity_id}: static {static_path.name}", depth_indent)
                return static_path
            else:
                print(f"Warning: Static ref not found for {entity_id}: {request.ref_paths[0]}")
                return None

        if not request.prompt:
            print(f"Warning: No prompt assembled for {entity_id}")
            print(f"  Hint: Ensure referenced entities have :description fields")
            return None

        # Always log the top-level render request (before cache check)
        if self._render_depth == 0:
            self._log_render_request(entity_id, request, depth_indent)

        # Check cache
        cache_key, ref_hashes = self._compute_cache_key(request)
        cached = self.cache.get(cache_key, entity=entity_id)
        if cached:
            self._log(f"{entity_id}: cached", depth_indent)
            return cached

        # Log the render request (sub-entities, on cache miss only)
        if self._render_depth > 0:
            self._log_render_request(entity_id, request, depth_indent)

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
            self._log(f"{entity_id}: saved {result_path.name}", depth_indent)
            return result_path

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
                        request.ref_image_names.append(part.name)

                elif isinstance(part, ContentsMarker):
                    # Get contained objects' descriptions and images
                    content_descs, content_images, content_names = self._resolve_contents(entity_id)
                    if content_descs:
                        prompt_texts.append(", ".join(content_descs))
                    request.ref_images.extend(content_images)
                    request.ref_image_names.extend(content_names)

                elif isinstance(part, ThroughMarker):
                    # Check if portal is open (use runtime state, not world definition)
                    portal_state = self.runtime.state.objects.get(part.portal)
                    if portal_state and portal_state.properties.get("open", False):
                        # Get descriptions for context
                        portal_desc = self._get_entity_description(part.portal) or "opening"
                        target_desc = self._get_entity_description(part.target) or part.target

                        prompt_texts.append(f"through the open {portal_desc} you can see {target_desc}")

                        # Render target room and include as reference
                        target_entity = (self.runtime.world.rooms.get(part.target) or
                                         self.runtime.world.objects.get(part.target) or
                                         self.runtime.world.references.get(part.target))
                        if target_entity and has_render_spec(target_entity):
                            target_image = self._resolve_object_ref(part.target)
                            if target_image:
                                request.ref_images.append(target_image)
                                request.ref_image_names.append(part.target)

        finally:
            self._render_depth -= 1

        # Resolve anchors (re-include atomic refs)
        for anchor in result.anchors:
            anchor_image = self._resolve_object_ref(anchor)
            if anchor_image:
                request.ref_images.append(anchor_image)
                request.ref_image_names.append(anchor)

        # Join prompt parts
        prompt = " ".join(text.strip() for text in prompt_texts if text.strip())

        # Prepend world render style if configured
        if prompt and self.runtime.world.render_style:
            prompt = f"STYLE: {self.runtime.world.render_style}\n{prompt}"

        request.prompt = prompt
        return request

    def _get_entity_description(self, entity_id: str) -> str | None:
        """Get render description from an entity, for use in image generation prompts.

        Prefers :rdesc (render description) over :description. This allows entities
        to have state-aware visual descriptions separate from player-facing text.

        For objects/rooms, checks :rdesc first, then falls back to :description.
        References have no description - they contribute only images, not text.

        Args:
            entity_id: The entity identifier (e.g., "@terminal-room-bg")

        Returns:
            The description string, or None if not found
        """
        # Check objects first
        obj = self.runtime.world.objects.get(entity_id)
        if obj:
            # Prefer :rdesc over :description for render prompts
            if obj.rdesc:
                desc = self._eval_description(obj.rdesc, entity_id)
                if desc:
                    return desc
            if obj.description:
                desc = self._eval_description(obj.description, entity_id)
                if desc:
                    return desc

        # References have no description - they contribute only images
        # The caller wraps references with descriptive text as needed

        # Check rooms
        room = self.runtime.world.rooms.get(entity_id)
        if room:
            # Prefer :rdesc over :description for render prompts
            if room.rdesc:
                desc = self._eval_description(room.rdesc, entity_id)
                if desc:
                    return desc
            if room.description:
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
        from grue.expr import ExprEvaluator, Environment, GrueFn

        if isinstance(desc_expr, SList) and len(desc_expr) >= 1:
            first = desc_expr[0]
            if isinstance(first, Symbol) and first.name == "fn":
                evaluator = ExprEvaluator(
                    self.runtime,
                    self.runtime._functions if hasattr(self.runtime, '_functions') else {}
                )
                env = Environment(bindings={"self": entity_id})
                try:
                    # Evaluate the (fn ...) expression to get a GrueFn
                    fn = evaluator.eval(desc_expr, env)
                    if isinstance(fn, GrueFn):
                        # Call the function with no args
                        result = evaluator.call_fn(fn, [])
                        return str(result) if result else None
                    return str(fn) if fn else None
                except Exception:
                    return None

        return str(desc_expr) if desc_expr else None

    def _resolve_contents(self, location_id: str) -> tuple[list[str], list["Image"], list[str]]:
        """Resolve contained objects to descriptions and images.

        Args:
            location_id: The location (room) ID

        Returns:
            Tuple of (descriptions, images, image_names)
        """
        descriptions: list[str] = []
        images: list["Image"] = []
        names: list[str] = []

        for obj_name, obj in self.runtime.world.objects.items():
            if obj.location == location_id:
                # Get description
                desc = self._get_entity_description(obj_name)
                if desc:
                    descriptions.append(desc)

                # Get object image (render spec or static asset)
                ref_image = self._resolve_object_ref(obj_name)
                if ref_image:
                    images.append(ref_image)
                    names.append(obj_name)

        return descriptions, images, names

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

        This may trigger recursive rendering if the entity has a render spec.
        Checks rooms, objects, then references. No implicit fallback - entities
        must have explicit :render specs (which can use :ref for static images).
        """
        from PIL import Image

        # Try to render a room
        room = self.runtime.world.rooms.get(object_id)
        if room and has_render_spec(room):
            rendered_path = self._render_entity(object_id, room)
            if rendered_path:
                return Image.open(rendered_path).convert("RGB")

        # Try to render an object
        obj = self.runtime.world.objects.get(object_id)
        if obj and has_render_spec(obj):
            rendered_path = self._render_entity(object_id, obj)
            if rendered_path:
                return Image.open(rendered_path).convert("RGB")

        # Try to render a reference (references always have render specs)
        ref = self.runtime.world.references.get(object_id)
        if ref:
            rendered_path = self._render_entity(object_id, ref)
            if rendered_path:
                return Image.open(rendered_path).convert("RGB")

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
        """Generate an image using the configured model backend.

        Args:
            request: The render request

        Returns:
            PIL Image or None on failure
        """
        from filfre.cli import MODEL_NANOBANANA

        if self.model == MODEL_NANOBANANA:
            return self._generate_image_nanobanana(request)
        else:
            return self._generate_image_flux(request)

    def _generate_image_nanobanana(self, request: RenderRequest) -> "Image | None":
        """Generate an image using NanoBanana (Gemini cloud API)."""
        from PIL import Image as PILImage

        # Collect all reference images (no resizing needed for API)
        refs = []
        for path in request.ref_paths:
            img = PILImage.open(path).convert("RGB")
            refs.append(img)
        for img in request.ref_images:
            refs.append(img)

        try:
            from filfre.cli import generate_image_nanobanana
            return generate_image_nanobanana(
                prompt=request.prompt,
                reference_images=refs if refs else None,
            )
        except Exception as e:
            print(f"Warning: NanoBanana image generation failed: {e}")
            return None

    def _generate_image_flux(self, request: RenderRequest) -> "Image | None":
        """Generate an image using FLUX.2 Klein (local pipeline)."""
        from PIL import Image as PILImage
        import torch

        # Get or load the pipeline
        pipeline = self._get_pipeline()
        if pipeline is None:
            return None

        # Prepare reference images
        refs = []

        # Load static refs
        for path in request.ref_paths:
            img = PILImage.open(path).convert("RGB")
            img = img.resize((request.ref_size, request.ref_size), PILImage.LANCZOS)
            refs.append(img)

        # Resize dynamic refs
        for img in request.ref_images:
            resized = img.resize((request.ref_size, request.ref_size), PILImage.LANCZOS)
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
            print(f"Warning: Flux image generation failed: {e}")
            return None

    def _get_pipeline(self):
        """Get or lazily load the filfre pipeline (flux only)."""
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
        """Set a pre-loaded pipeline (for sharing across renders with flux)."""
        self._pipeline = pipeline
