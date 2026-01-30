"""Tests for render caching."""

import pytest
import tempfile
from pathlib import Path

from grue.render_cache import (
    RenderCache,
    hash_image_data,
    hash_pil_image,
)


class TestRenderCacheKeyComputation:
    """Test cache key computation."""

    def test_same_inputs_same_key(self):
        """Same prompt and refs produce same key."""
        cache = RenderCache("/tmp/cache")

        key1 = cache.compute_key("A brass lantern", ref_hashes=["abc123"])
        key2 = cache.compute_key("A brass lantern", ref_hashes=["abc123"])

        assert key1 == key2

    def test_different_prompt_different_key(self):
        """Different prompts produce different keys."""
        cache = RenderCache("/tmp/cache")

        key1 = cache.compute_key("A brass lantern")
        key2 = cache.compute_key("A wooden table")

        assert key1 != key2

    def test_different_refs_different_key(self):
        """Different reference hashes produce different keys."""
        cache = RenderCache("/tmp/cache")

        key1 = cache.compute_key("A scene", ref_hashes=["abc123"])
        key2 = cache.compute_key("A scene", ref_hashes=["def456"])

        assert key1 != key2

    def test_different_model_version_different_key(self):
        """Different model versions produce different keys."""
        cache1 = RenderCache("/tmp/cache", model_version="v1")
        cache2 = RenderCache("/tmp/cache", model_version="v2")

        key1 = cache1.compute_key("A brass lantern")
        key2 = cache2.compute_key("A brass lantern")

        assert key1 != key2

    def test_ref_order_does_not_matter(self):
        """Reference order doesn't affect key (sorted internally)."""
        cache = RenderCache("/tmp/cache")

        key1 = cache.compute_key("A scene", ref_hashes=["aaa", "bbb", "ccc"])
        key2 = cache.compute_key("A scene", ref_hashes=["ccc", "aaa", "bbb"])

        assert key1 == key2

    def test_whitespace_normalization(self):
        """Prompt whitespace is normalized."""
        cache = RenderCache("/tmp/cache")

        key1 = cache.compute_key("A brass lantern")
        key2 = cache.compute_key("A   brass   lantern")
        key3 = cache.compute_key("A brass\n\t lantern")

        assert key1 == key2 == key3

    def test_key_length(self):
        """Key length matches configured hash_length."""
        cache = RenderCache("/tmp/cache", hash_length=20)
        key = cache.compute_key("A brass lantern")

        assert len(key) == 20

    def test_no_refs_works(self):
        """Cache key works with no references."""
        cache = RenderCache("/tmp/cache")
        key = cache.compute_key("A brass lantern")

        assert len(key) == 16  # Default hash_length


class TestRenderCacheOperations:
    """Test cache get/put/has operations."""

    def test_has_returns_false_for_missing(self):
        """has() returns False for missing keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)
            assert cache.has("nonexistent") is False

    def test_get_returns_none_for_missing(self):
        """get() returns None for missing keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)
            assert cache.get("nonexistent") is None

    def test_put_and_get(self):
        """put() stores image and get() retrieves it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)

            # Create a test image file
            test_image = Path(tmpdir) / "test.png"
            test_image.write_bytes(b"fake png data")

            key = "test123"
            cache.put(key, test_image)

            assert cache.has(key)
            cached_path = cache.get(key)
            assert cached_path is not None
            assert cached_path.exists()
            assert cached_path.read_bytes() == b"fake png data"

    def test_put_creates_cache_dir(self):
        """put() creates cache directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "nested" / "cache"
            cache = RenderCache(cache_dir)

            test_image = Path(tmpdir) / "test.png"
            test_image.write_bytes(b"fake png data")

            cache.put("key123", test_image)

            assert cache_dir.exists()
            assert cache.has("key123")

    def test_put_copy_preserves_original(self):
        """put(copy=True) preserves the original file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)

            test_image = Path(tmpdir) / "original.png"
            test_image.write_bytes(b"fake png data")

            cache.put("key123", test_image, copy=True)

            assert test_image.exists()  # Original preserved

    def test_put_move_removes_original(self):
        """put(copy=False) moves the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(Path(tmpdir) / "cache")

            test_image = Path(tmpdir) / "original.png"
            test_image.write_bytes(b"fake png data")

            cache.put("key123", test_image, copy=False)

            assert not test_image.exists()  # Original moved


class TestRenderCacheWithFiles:
    """Test cache with actual file hashing."""

    def test_compute_key_with_file_paths(self):
        """compute_key() hashes actual files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)

            # Create test reference files
            ref1 = Path(tmpdir) / "ref1.png"
            ref2 = Path(tmpdir) / "ref2.png"
            ref1.write_bytes(b"image data 1")
            ref2.write_bytes(b"image data 2")

            key = cache.compute_key("A scene", ref_paths=[ref1, ref2])
            assert len(key) == 16

    def test_file_content_change_changes_key(self):
        """Changing file content changes the key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)

            ref = Path(tmpdir) / "ref.png"
            ref.write_bytes(b"original content")

            key1 = cache.compute_key("A scene", ref_paths=[ref])

            ref.write_bytes(b"modified content")

            key2 = cache.compute_key("A scene", ref_paths=[ref])

            assert key1 != key2


class TestRenderCacheStats:
    """Test cache statistics and management."""

    def test_stats_empty_cache(self):
        """stats() works on empty/nonexistent cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(Path(tmpdir) / "nonexistent")
            stats = cache.stats()

            assert stats["count"] == 0
            assert stats["size_bytes"] == 0

    def test_stats_with_files(self):
        """stats() counts files and sizes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(Path(tmpdir) / "cache")

            # Add some cached files
            test_image = Path(tmpdir) / "test.png"
            test_image.write_bytes(b"x" * 100)

            cache.put("key1", test_image)
            cache.put("key2", test_image)

            stats = cache.stats()
            assert stats["count"] == 2
            assert stats["size_bytes"] == 200

    def test_clear_removes_all(self):
        """clear() removes all cached files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(Path(tmpdir) / "cache")

            test_image = Path(tmpdir) / "test.png"
            test_image.write_bytes(b"data")

            cache.put("key1", test_image)
            cache.put("key2", test_image)

            count = cache.clear()
            assert count == 2
            assert cache.stats()["count"] == 0


class TestImageHashing:
    """Test image hashing utilities."""

    def test_hash_image_data(self):
        """hash_image_data() produces consistent hashes."""
        data = b"fake image data"
        hash1 = hash_image_data(data)
        hash2 = hash_image_data(data)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex

    def test_hash_image_data_different_content(self):
        """Different content produces different hashes."""
        hash1 = hash_image_data(b"data 1")
        hash2 = hash_image_data(b"data 2")

        assert hash1 != hash2

    def test_hash_pil_image(self):
        """hash_pil_image() hashes PIL images."""
        pytest.importorskip("PIL")
        from PIL import Image

        # Create a simple test image
        img = Image.new("RGB", (10, 10), color="red")
        hash1 = hash_pil_image(img)
        hash2 = hash_pil_image(img)

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_hash_pil_image_different_content(self):
        """Different images produce different hashes."""
        pytest.importorskip("PIL")
        from PIL import Image

        img1 = Image.new("RGB", (10, 10), color="red")
        img2 = Image.new("RGB", (10, 10), color="blue")

        assert hash_pil_image(img1) != hash_pil_image(img2)
