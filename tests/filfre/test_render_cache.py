"""Tests for render caching."""

import pytest
import tempfile
from pathlib import Path

from filfre.render_cache import (
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

        assert len(key) == 8  # Default hash_length is now 8


class TestRenderCacheOperations:
    """Test cache get/put/has operations."""

    def test_has_returns_false_for_missing(self):
        """has() returns False for missing keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)
            assert cache.has("nonexistent", "@test-entity") is False

    def test_get_returns_none_for_missing(self):
        """get() returns None for missing keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)
            assert cache.get("nonexistent", "@test-entity") is None

    def test_put_and_get(self):
        """put() stores image and get() retrieves it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)

            # Create a test image file
            test_image = Path(tmpdir) / "test.png"
            test_image.write_bytes(b"fake png data")

            key = "test1234"
            cache.put(key, "@test-entity", test_image, prompt="A test image")

            assert cache.has(key, "@test-entity")
            cached_path = cache.get(key, "@test-entity")
            assert cached_path is not None
            assert cached_path.exists()
            assert cached_path.read_bytes() == b"fake png data"

    def test_put_creates_cache_dir(self):
        """put() creates cache directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            renders_dir = Path(tmpdir) / "nested" / "renders"
            cache = RenderCache(renders_dir)

            test_image = Path(tmpdir) / "test.png"
            test_image.write_bytes(b"fake png data")

            cache.put("key12345", "@test-entity", test_image, prompt="Test")

            assert cache.cache_dir.exists()
            assert cache.has("key12345", "@test-entity")

    def test_put_copy_preserves_original(self):
        """put(copy=True) preserves the original file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)

            test_image = Path(tmpdir) / "original.png"
            test_image.write_bytes(b"fake png data")

            cache.put("key12345", "@test-entity", test_image, prompt="Test", copy=True)

            assert test_image.exists()  # Original preserved

    def test_put_move_removes_original(self):
        """put(copy=False) moves the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(Path(tmpdir) / "renders")

            test_image = Path(tmpdir) / "original.png"
            test_image.write_bytes(b"fake png data")

            cache.put("key12345", "@test-entity", test_image, prompt="Test", copy=False)

            assert not test_image.exists()  # Original moved


class TestRenderCacheTwoTier:
    """Test two-tier frozen/cache lookup."""

    def test_frozen_takes_priority(self):
        """Frozen renders are returned over cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)

            # Create both frozen and cached versions
            frozen_path = cache._frozen_path("@test-entity", "key12345")
            cached_path = cache._cache_path("@test-entity", "key12345")

            frozen_path.parent.mkdir(parents=True, exist_ok=True)
            cached_path.parent.mkdir(parents=True, exist_ok=True)

            frozen_path.write_bytes(b"frozen data")
            cached_path.write_bytes(b"cached data")

            # get() should return frozen
            result = cache.get("key12345", "@test-entity")
            assert result == frozen_path
            assert result.read_bytes() == b"frozen data"

    def test_cache_used_when_no_frozen(self):
        """Cached renders are returned when no frozen exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)

            # Create only cached version
            cached_path = cache._cache_path("@test-entity", "key12345")
            cached_path.parent.mkdir(parents=True, exist_ok=True)
            cached_path.write_bytes(b"cached data")

            result = cache.get("key12345", "@test-entity")
            assert result == cached_path

    def test_entity_prefixed_filename(self):
        """Filenames include entity prefix."""
        cache = RenderCache("/tmp/renders")

        filename = cache._filename("@terminal-room", "abc12345")
        assert filename == "terminal-room-abc12345.png"

        filename = cache._filename("@hacker", "xyz98765")
        assert filename == "hacker-xyz98765.png"


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
            assert len(key) == 8  # Default hash_length

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

            assert stats["frozen_count"] == 0
            assert stats["cache_count"] == 0

    def test_stats_with_files(self):
        """stats() counts files and sizes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(Path(tmpdir) / "renders")

            # Add some cached files
            test_image = Path(tmpdir) / "test.png"
            test_image.write_bytes(b"x" * 100)

            cache.put("key12345", "@entity1", test_image, prompt="Test 1")
            cache.put("key67890", "@entity2", test_image, prompt="Test 2")

            stats = cache.stats()
            assert stats["cache_count"] == 2
            assert stats["cache_size_bytes"] == 200

    def test_clear_cache_removes_cached_only(self):
        """clear_cache() removes cached files but not frozen."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(Path(tmpdir) / "renders")

            test_image = Path(tmpdir) / "test.png"
            test_image.write_bytes(b"data")

            # Add cached file
            cache.put("key12345", "@entity", test_image, prompt="Test")

            # Add frozen file manually
            frozen_path = cache._frozen_path("@entity", "frozen12")
            frozen_path.parent.mkdir(parents=True, exist_ok=True)
            frozen_path.write_bytes(b"frozen data")

            count = cache.clear_cache()
            assert count == 1

            stats = cache.stats()
            assert stats["cache_count"] == 0
            assert stats["frozen_count"] == 1


class TestRenderLog:
    """Test render logging."""

    def test_put_logs_render(self):
        """put() appends to render log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)

            test_image = Path(tmpdir) / "test.png"
            test_image.write_bytes(b"data")

            cache.put(
                "key12345",
                "@terminal-room",
                test_image,
                prompt="A computer lab",
                ref_paths=["assets/bg.png"],
                ref_hashes=["abc123"],
            )

            entries = cache.read_log()
            assert len(entries) == 1
            assert entries[0]["hash"] == "key12345"
            assert entries[0]["entity"] == "@terminal-room"
            assert entries[0]["prompt"] == "A computer lab"
            assert entries[0]["refs"] == ["assets/bg.png"]
            assert entries[0]["ref_hashes"] == ["abc123"]
            assert "timestamp" in entries[0]

    def test_read_log_with_limit(self):
        """read_log() respects limit parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = RenderCache(tmpdir)

            test_image = Path(tmpdir) / "test.png"
            test_image.write_bytes(b"data")

            for i in range(5):
                cache.put(f"key{i:05d}", "@entity", test_image, prompt=f"Prompt {i}")

            entries = cache.read_log(limit=2)
            assert len(entries) == 2
            assert entries[0]["prompt"] == "Prompt 3"
            assert entries[1]["prompt"] == "Prompt 4"


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
