"""
Content-addressed cache for rendered images.

The cache key is computed from:
- Model version (for invalidation when model changes)
- Canonical prompt text
- Content hashes of all reference images

This ensures that:
- Prompt changes → new cache key
- Reference image changes → new cache key (content-addressed)
- Model version changes → new cache key

Usage:
    cache = RenderCache("cache/renders", model_version="flux2-klein-4b")

    key = cache.compute_key(
        prompt="A brass lantern on a wooden table",
        ref_paths=["assets/lantern.png", "assets/table.png"]
    )

    if cache.has(key):
        image_path = cache.get(key)
    else:
        # Generate image...
        cache.put(key, generated_image_path)

Pre-caching:
    Known-good renders can be committed to the repo. The cache will find them
    automatically if they're in the cache directory with the correct key name.
"""

import hashlib
import shutil
from pathlib import Path
from typing import Optional


class RenderCache:
    """Content-addressed cache for rendered images."""

    def __init__(
        self,
        cache_dir: str | Path,
        model_version: str = "flux2-klein-4b",
        hash_length: int = 16,
    ):
        """Initialize the render cache.

        Args:
            cache_dir: Directory to store cached renders
            model_version: Model identifier for cache invalidation
            hash_length: Length of hash to use in filenames (default 16)
        """
        self.cache_dir = Path(cache_dir)
        self.model_version = model_version
        self.hash_length = hash_length

    def compute_key(
        self,
        prompt: str,
        ref_paths: list[str | Path] | None = None,
        ref_hashes: list[str] | None = None,
    ) -> str:
        """Compute a cache key from prompt and reference images.

        Args:
            prompt: The text prompt for generation
            ref_paths: List of paths to reference images (will be hashed)
            ref_hashes: Pre-computed hashes for references (if paths unavailable)
                        Use this when references are in-memory or from other objects

        Returns:
            A hex string cache key

        Note:
            Either ref_paths or ref_hashes can be provided, not both.
            If both are provided, ref_paths takes precedence.
        """
        hasher = hashlib.sha256()

        # Include model version
        hasher.update(self.model_version.encode("utf-8"))
        hasher.update(b"\x00")  # Separator

        # Include canonical prompt (normalized whitespace)
        canonical_prompt = " ".join(prompt.split())
        hasher.update(canonical_prompt.encode("utf-8"))
        hasher.update(b"\x00")

        # Include reference image hashes (sorted for determinism)
        if ref_paths:
            hashes = sorted(self._hash_file(Path(p)) for p in ref_paths)
        elif ref_hashes:
            hashes = sorted(ref_hashes)
        else:
            hashes = []

        for h in hashes:
            hasher.update(h.encode("utf-8"))
            hasher.update(b"\x00")

        return hasher.hexdigest()[: self.hash_length]

    def _hash_file(self, path: Path) -> str:
        """Compute SHA256 hash of a file's contents."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def has(self, key: str) -> bool:
        """Check if a cached render exists for the given key."""
        return self._cache_path(key).exists()

    def get(self, key: str) -> Path | None:
        """Get the path to a cached render, or None if not cached.

        Args:
            key: The cache key

        Returns:
            Path to the cached image, or None if not found
        """
        path = self._cache_path(key)
        if path.exists():
            return path
        return None

    def put(self, key: str, image_path: str | Path, copy: bool = True) -> Path:
        """Store an image in the cache.

        Args:
            key: The cache key
            image_path: Path to the image to cache
            copy: If True, copy the file; if False, move it

        Returns:
            Path to the cached image
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        dest = self._cache_path(key)

        if copy:
            shutil.copy2(image_path, dest)
        else:
            shutil.move(str(image_path), dest)

        return dest

    def _cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{key}.png"

    def clear(self) -> int:
        """Clear all cached renders.

        Returns:
            Number of files removed
        """
        if not self.cache_dir.exists():
            return 0

        count = 0
        for path in self.cache_dir.glob("*.png"):
            path.unlink()
            count += 1
        return count

    def stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dict with 'count' and 'size_bytes' keys
        """
        if not self.cache_dir.exists():
            return {"count": 0, "size_bytes": 0}

        files = list(self.cache_dir.glob("*.png"))
        total_size = sum(f.stat().st_size for f in files)

        return {
            "count": len(files),
            "size_bytes": total_size,
        }


def hash_image_data(data: bytes) -> str:
    """Compute SHA256 hash of image data (for in-memory images).

    Args:
        data: Raw image bytes

    Returns:
        Hex string hash
    """
    return hashlib.sha256(data).hexdigest()


def hash_pil_image(image) -> str:
    """Compute SHA256 hash of a PIL Image.

    Args:
        image: PIL Image object

    Returns:
        Hex string hash
    """
    import io

    buffer = io.BytesIO()
    # Use PNG for lossless, deterministic encoding
    image.save(buffer, format="PNG")
    return hash_image_data(buffer.getvalue())
