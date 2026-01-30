"""
Content-addressed cache for rendered images.

The cache key is computed from:
- Model version (for invalidation when model changes)
- Canonical prompt text
- Content hashes of all reference images

Directory structure:
    assets/renders/              # Frozen renders (checked in)
        terminal-room-a1b2c3d4.png
        kitchen-e5f6g7h8.png
    assets/renders/cache/        # Working cache (gitignored)
        terminal-room-i9j0k1l2.png
    assets/renders/render-log.jsonl  # Append-only audit log

Lookup order:
    1. Frozen: assets/renders/{entity}-{hash}.png
    2. Cache: assets/renders/cache/{entity}-{hash}.png
    3. Generate

Usage:
    cache = RenderCache("assets/renders", model_version="flux2-klein-4b")

    key = cache.compute_key(
        prompt="A brass lantern on a wooden table",
        ref_paths=["assets/backgrounds/lab.png"]
    )

    if cached := cache.get(key, entity="@terminal-room"):
        image_path = cached
    else:
        # Generate image...
        cache.put(key, entity="@terminal-room", image_path=generated_path,
                  prompt="...", ref_paths=[...])
"""

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class RenderCache:
    """Content-addressed cache for rendered images with two-tier storage."""

    def __init__(
        self,
        renders_dir: str | Path,
        model_version: str = "flux2-klein-4b",
        hash_length: int = 8,
    ):
        """Initialize the render cache.

        Args:
            renders_dir: Base directory for renders (e.g., "assets/renders")
            model_version: Model identifier for cache invalidation
            hash_length: Length of hash to use in filenames (default 8)
        """
        self.renders_dir = Path(renders_dir)
        self.cache_dir = self.renders_dir / "cache"
        self.log_path = self.renders_dir / "render-log.jsonl"
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

        Returns:
            A hex string cache key
        """
        hasher = hashlib.sha256()

        # Include model version
        hasher.update(self.model_version.encode("utf-8"))
        hasher.update(b"\x00")

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
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _entity_stem(self, entity: str) -> str:
        """Convert entity ID to filename stem (strip @ prefix)."""
        return entity.lstrip("@")

    def _filename(self, entity: str, key: str) -> str:
        """Build filename for an entity render."""
        return f"{self._entity_stem(entity)}-{key}.png"

    def _frozen_path(self, entity: str, key: str) -> Path:
        """Get path for a frozen render."""
        return self.renders_dir / self._filename(entity, key)

    def _cache_path(self, entity: str, key: str) -> Path:
        """Get path for a cached render."""
        return self.cache_dir / self._filename(entity, key)

    def get(self, key: str, entity: str) -> Path | None:
        """Get the path to a render, checking frozen first, then cache.

        Args:
            key: The cache key
            entity: The entity ID (e.g., "@terminal-room")

        Returns:
            Path to the image, or None if not found
        """
        # Check frozen first
        frozen = self._frozen_path(entity, key)
        if frozen.exists():
            return frozen

        # Then check cache
        cached = self._cache_path(entity, key)
        if cached.exists():
            return cached

        return None

    def has(self, key: str, entity: str) -> bool:
        """Check if a render exists (frozen or cached)."""
        return self.get(key, entity) is not None

    def put(
        self,
        key: str,
        entity: str,
        image_path: str | Path,
        prompt: str,
        ref_paths: list[str] | None = None,
        ref_hashes: list[str] | None = None,
        copy: bool = True,
    ) -> Path:
        """Store an image in the working cache and log it.

        Args:
            key: The cache key
            entity: The entity ID (e.g., "@terminal-room")
            image_path: Path to the image to cache
            prompt: The prompt used for generation (for logging)
            ref_paths: Reference image paths (for logging)
            ref_hashes: Reference image hashes (for logging)
            copy: If True, copy the file; if False, move it

        Returns:
            Path to the cached image
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        dest = self._cache_path(entity, key)

        if copy:
            shutil.copy2(image_path, dest)
        else:
            shutil.move(str(image_path), dest)

        # Log the render
        self._log_render(
            key=key,
            entity=entity,
            prompt=prompt,
            ref_paths=ref_paths or [],
            ref_hashes=ref_hashes or [],
        )

        return dest

    def _log_render(
        self,
        key: str,
        entity: str,
        prompt: str,
        ref_paths: list[str],
        ref_hashes: list[str],
    ) -> None:
        """Append a render entry to the log file."""
        self.renders_dir.mkdir(parents=True, exist_ok=True)

        entry = {
            "hash": key,
            "entity": entity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt,
            "refs": ref_paths,
            "ref_hashes": ref_hashes,
            "filename": self._filename(entity, key),
        }

        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def read_log(self, limit: int | None = None) -> list[dict]:
        """Read entries from the render log.

        Args:
            limit: Max entries to return (from end), None for all

        Returns:
            List of log entries (most recent last)
        """
        if not self.log_path.exists():
            return []

        entries = []
        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        if limit:
            return entries[-limit:]
        return entries

    def clear_cache(self) -> int:
        """Clear the working cache (not frozen renders).

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
            Dict with counts and sizes for frozen and cached renders
        """
        frozen_files = list(self.renders_dir.glob("*.png")) if self.renders_dir.exists() else []
        cache_files = list(self.cache_dir.glob("*.png")) if self.cache_dir.exists() else []

        return {
            "frozen_count": len(frozen_files),
            "frozen_size_bytes": sum(f.stat().st_size for f in frozen_files),
            "cache_count": len(cache_files),
            "cache_size_bytes": sum(f.stat().st_size for f in cache_files),
        }

    def list_renders(self, include_cache: bool = True) -> list[dict]:
        """List all available renders with metadata from log.

        Args:
            include_cache: Include working cache, not just frozen

        Returns:
            List of render info dicts with path, entity, hash, frozen status
        """
        # Build lookup from log
        log_by_filename = {}
        for entry in self.read_log():
            log_by_filename[entry["filename"]] = entry

        renders = []

        # Frozen renders
        if self.renders_dir.exists():
            for path in self.renders_dir.glob("*.png"):
                info = {"path": str(path), "frozen": True}
                if path.name in log_by_filename:
                    info.update(log_by_filename[path.name])
                else:
                    # Parse from filename
                    stem = path.stem
                    if "-" in stem:
                        entity, hash_part = stem.rsplit("-", 1)
                        info["entity"] = f"@{entity}"
                        info["hash"] = hash_part
                renders.append(info)

        # Cached renders
        if include_cache and self.cache_dir.exists():
            for path in self.cache_dir.glob("*.png"):
                info = {"path": str(path), "frozen": False}
                if path.name in log_by_filename:
                    info.update(log_by_filename[path.name])
                else:
                    stem = path.stem
                    if "-" in stem:
                        entity, hash_part = stem.rsplit("-", 1)
                        info["entity"] = f"@{entity}"
                        info["hash"] = hash_part
                renders.append(info)

        return renders


def hash_image_data(data: bytes) -> str:
    """Compute SHA256 hash of image data (for in-memory images)."""
    return hashlib.sha256(data).hexdigest()


def hash_pil_image(image) -> str:
    """Compute SHA256 hash of a PIL Image."""
    import io

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return hash_image_data(buffer.getvalue())
