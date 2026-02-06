"""Tests for repository layer components."""
import pytest
import json
import os
import tempfile
import tarfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from repositories.file_repository import FileRepository
from repositories.cache_repository import CacheRepository, CacheEntry


class TestFileRepository:
    """Test cases for FileRepository."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def file_repo(self, temp_dir):
        """Create a FileRepository instance with temp directory."""
        return FileRepository(base_dir=temp_dir)
    
    def test_initialization_with_base_dir(self, temp_dir):
        """Test repository initialization with base directory."""
        repo = FileRepository(base_dir=temp_dir)
        assert repo.base_dir == Path(temp_dir)
    
    def test_initialization_without_base_dir(self):
        """Test repository initialization without base directory."""
        repo = FileRepository()
        assert repo.base_dir == Path.cwd()
    
    def test_read_json_success(self, file_repo, temp_dir):
        """Test reading JSON file successfully."""
        test_file = Path(temp_dir) / "test.json"
        test_data = {"key": "value", "number": 123}
        test_file.write_text(json.dumps(test_data))
        
        result = file_repo.read_json("test.json")
        assert result == test_data
    
    def test_read_json_absolute_path(self, file_repo, temp_dir):
        """Test reading JSON with absolute path."""
        test_file = Path(temp_dir) / "absolute.json"
        test_data = {"absolute": True}
        test_file.write_text(json.dumps(test_data))
        
        result = file_repo.read_json(str(test_file))
        assert result == test_data
    
    def test_read_json_file_not_found(self, file_repo):
        """Test reading non-existent JSON file."""
        result = file_repo.read_json("nonexistent.json")
        assert result is None
    
    def test_read_json_invalid_json(self, file_repo, temp_dir):
        """Test reading invalid JSON file."""
        test_file = Path(temp_dir) / "invalid.json"
        test_file.write_text("not valid json {")
        
        result = file_repo.read_json("invalid.json")
        assert result is None
    
    def test_write_json_success(self, file_repo, temp_dir):
        """Test writing JSON file successfully."""
        test_data = {"key": "value", "list": [1, 2, 3]}
        file_repo.write_json("output.json", test_data)
        
        written_file = Path(temp_dir) / "output.json"
        assert written_file.exists()
        
        with open(written_file) as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data
    
    def test_write_json_creates_directory(self, file_repo, temp_dir):
        """Test that write_json creates parent directories."""
        nested_path = "subdir/nested/data.json"
        test_data = {"nested": True}
        
        file_repo.write_json(nested_path, test_data)
        
        written_file = Path(temp_dir) / nested_path
        assert written_file.exists()
        assert written_file.parent.exists()
    
    def test_write_json_custom_indent(self, file_repo, temp_dir):
        """Test writing JSON with custom indent."""
        test_data = {"key": "value"}
        file_repo.write_json("indent.json", test_data, indent=4)
        
        written_file = Path(temp_dir) / "indent.json"
        content = written_file.read_text()
        assert "    " in content  # 4-space indent
    
    def test_read_text_success(self, file_repo, temp_dir):
        """Test reading text file successfully."""
        test_file = Path(temp_dir) / "test.txt"
        test_content = "Hello, World!\nLine 2"
        test_file.write_text(test_content)
        
        result = file_repo.read_text("test.txt")
        assert result == test_content
    
    def test_read_text_file_not_found(self, file_repo):
        """Test reading non-existent text file."""
        result = file_repo.read_text("nonexistent.txt")
        assert result is None
    
    def test_write_text_success(self, file_repo, temp_dir):
        """Test writing text file successfully."""
        test_content = "Test content\nWith multiple lines"
        file_repo.write_text("output.txt", test_content)
        
        written_file = Path(temp_dir) / "output.txt"
        assert written_file.exists()
        assert written_file.read_text() == test_content
    
    def test_exists_file(self, file_repo, temp_dir):
        """Test checking if file exists."""
        test_file = Path(temp_dir) / "exists.txt"
        test_file.write_text("content")
        
        assert file_repo.exists("exists.txt") is True
        assert file_repo.exists("notexists.txt") is False
    
    def test_exists_directory(self, file_repo, temp_dir):
        """Test checking if directory exists."""
        test_dir = Path(temp_dir) / "subdir"
        test_dir.mkdir()
        
        assert file_repo.exists("subdir") is True
    
    def test_list_files_basic(self, file_repo, temp_dir):
        """Test listing files in directory."""
        # Create test files
        (Path(temp_dir) / "file1.txt").write_text("content")
        (Path(temp_dir) / "file2.txt").write_text("content")
        (Path(temp_dir) / "file3.json").write_text("{}")
        
        result = file_repo.list_files("")
        assert len(result) == 3
        result_str = [str(p) for p in result]
        assert any("file1.txt" in f for f in result_str)
        assert any("file2.txt" in f for f in result_str)
        assert any("file3.json" in f for f in result_str)
    
    def test_list_files_with_pattern(self, file_repo, temp_dir):
        """Test listing files with glob pattern."""
        # Create test files
        (Path(temp_dir) / "test1.txt").write_text("content")
        (Path(temp_dir) / "test2.txt").write_text("content")
        (Path(temp_dir) / "other.json").write_text("{}")
        
        result = file_repo.list_files("", pattern="*.txt")
        assert len(result) == 2
        result_str = [str(p) for p in result]
        assert all(f.endswith(".txt") for f in result_str)
    
    def test_list_files_directory_not_found(self, file_repo):
        """Test listing files in non-existent directory."""
        result = file_repo.list_files("nonexistent_dir")
        assert result == []
    
    def test_create_tar_success(self, file_repo, temp_dir):
        """Test creating tar.gz archive."""
        # Create source directory with files
        source_dir = Path(temp_dir) / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")
        
        tar_path = "archive.tar.gz"
        result = file_repo.create_tar(tar_path, "source")
        
        assert result is True
        tar_file = Path(temp_dir) / tar_path
        assert tar_file.exists()
        
        # Verify archive contents
        with tarfile.open(tar_file, "r:gz") as tar:
            members = tar.getnames()
            # Archive includes directory + 2 files
            assert len(members) == 3
            assert any('file1.txt' in m for m in members)
            assert any('file2.txt' in m for m in members)
    
    def test_create_tar_source_not_found(self, file_repo):
        """Test creating tar from non-existent source."""
        result = file_repo.create_tar("archive.tar.gz", "nonexistent")
        assert result is False
    
    def test_resolve_path_relative(self, file_repo, temp_dir):
        """Test resolving relative path."""
        resolved = file_repo._resolve_path("subdir/file.txt")
        expected = Path(temp_dir) / "subdir" / "file.txt"
        assert resolved == expected
    
    def test_resolve_path_absolute(self, file_repo):
        """Test resolving absolute path."""
        if os.name == 'nt':
            absolute_path = "C:\\absolute\\path\\file.txt"
        else:
            absolute_path = "/absolute/path/file.txt"
        resolved = file_repo._resolve_path(absolute_path)
        assert resolved == Path(absolute_path)
    
    def test_resolve_path_no_base_dir(self):
        """Test resolving path with base directory (should use cwd)."""
        repo = FileRepository()
        resolved = repo._resolve_path("file.txt")
        expected = Path.cwd() / "file.txt"
        assert resolved == expected


class TestCacheEntry:
    """Test cases for CacheEntry dataclass."""
    
    def test_creation(self):
        """Test creating a cache entry."""
        import time
        now = time.time()
        entry = CacheEntry(key="test_key", data={"value": 123}, timestamp=now, ttl=60)
        assert entry.key == "test_key"
        assert entry.data == {"value": 123}
        assert entry.ttl == 60
        assert entry.timestamp == now
    
    def test_is_expired_without_ttl(self):
        """Test that entries without TTL never expire."""
        import time
        entry = CacheEntry(key="test", data="data", timestamp=time.time(), ttl=None)
        assert entry.is_expired() is False
    
    def test_is_expired_not_expired(self):
        """Test entry that has not expired."""
        import time
        entry = CacheEntry(key="test", data="data", timestamp=time.time(), ttl=3600)
        assert entry.is_expired() is False
    
    def test_is_expired_expired(self):
        """Test entry that has expired."""
        import time
        entry = CacheEntry(key="test", data="data", timestamp=time.time(), ttl=0.1)
        time.sleep(0.2)
        assert entry.is_expired() is True


class TestCacheRepository:
    """Test cases for CacheRepository."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def cache_repo(self, temp_cache_dir):
        """Create a CacheRepository instance."""
        return CacheRepository(cache_dir=temp_cache_dir)
    
    def test_initialization(self, temp_cache_dir):
        """Test repository initialization."""
        repo = CacheRepository(cache_dir=temp_cache_dir)
        assert repo.cache_dir == Path(temp_cache_dir)
        assert os.path.exists(temp_cache_dir)
        assert isinstance(repo._memory_cache, dict)
    
    def test_set_and_get_memory_only(self, cache_repo):
        """Test setting and getting from memory cache."""
        cache_repo.set("key1", {"value": "test"}, persist=False)
        result = cache_repo.get("key1")
        assert result == {"value": "test"}
    
    def test_set_and_get_with_persistence(self, cache_repo, temp_cache_dir):
        """Test setting and getting with file persistence."""
        test_data = {"key": "value", "number": 42}
        cache_repo.set("persistent_key", test_data, persist=True)
        
        # Verify in memory
        assert cache_repo.get("persistent_key") == test_data
        
        # Verify file exists
        cache_file = Path(temp_cache_dir) / "persistent_key.json"
        assert cache_file.exists()
    
    def test_get_nonexistent_key(self, cache_repo):
        """Test getting non-existent key."""
        result = cache_repo.get("nonexistent")
        assert result is None
    
    def test_get_with_ttl_not_expired(self, cache_repo):
        """Test getting entry with TTL that hasn't expired."""
        cache_repo.set("ttl_key", "data", ttl=3600)
        result = cache_repo.get("ttl_key")
        assert result == "data"
    
    def test_get_with_ttl_expired(self, cache_repo):
        """Test getting entry with expired TTL."""
        import time
        cache_repo.set("expired_key", "data", ttl=0.1)
        time.sleep(0.2)
        result = cache_repo.get("expired_key")
        assert result is None
    
    def test_delete_memory_only(self, cache_repo):
        """Test deleting from memory cache."""
        cache_repo.set("delete_me", "data", persist=False)
        assert cache_repo.get("delete_me") == "data"
        
        cache_repo.delete("delete_me")
        assert cache_repo.get("delete_me") is None
    
    def test_delete_with_persistence(self, cache_repo, temp_cache_dir):
        """Test deleting from both memory and file cache."""
        cache_repo.set("delete_persistent", "data", persist=True)
        cache_file = Path(temp_cache_dir) / "delete_persistent.json"
        assert cache_file.exists()
        
        cache_repo.delete("delete_persistent")
        assert cache_repo.get("delete_persistent") is None
        assert not cache_file.exists()
    
    def test_clear_all_caches(self, cache_repo, temp_cache_dir):
        """Test clearing all cache entries."""
        # Add multiple entries
        cache_repo.set("key1", "data1", persist=True)
        cache_repo.set("key2", "data2", persist=True)
        cache_repo.set("key3", "data3", persist=False)
        
        cache_repo.clear()
        
        # Verify memory cache is empty
        assert len(cache_repo._memory_cache) == 0
        
        # Verify all cache files are deleted
        cache_files = list(Path(temp_cache_dir).glob("*.json"))
        assert len(cache_files) == 0
    
    def test_cleanup_expired_entries(self, cache_repo):
        """Test cleanup of expired entries."""
        import time
        
        # Add mix of expired and valid entries
        cache_repo.set("valid", "data", ttl=3600)
        cache_repo.set("expired1", "data", ttl=0.1)
        cache_repo.set("expired2", "data", ttl=0.1)
        cache_repo.set("no_ttl", "data", ttl=None)
        
        time.sleep(0.2)
        
        cache_repo.cleanup_expired()
        
        # Valid entries should remain
        assert cache_repo.get("valid") == "data"
        assert cache_repo.get("no_ttl") == "data"
        
        # Expired entries should be removed
        assert cache_repo.get("expired1") is None
        assert cache_repo.get("expired2") is None
    
    def test_read_file_cache_success(self, cache_repo, temp_cache_dir):
        """Test reading from file cache."""
        # Manually create cache file
        cache_file = Path(temp_cache_dir) / "file_key.json"
        test_data = {"from": "file"}
        cache_file.write_text(json.dumps(test_data))
        
        result = cache_repo._read_file_cache("file_key")
        assert result == test_data
    
    def test_read_file_cache_not_found(self, cache_repo):
        """Test reading non-existent file cache."""
        result = cache_repo._read_file_cache("nonexistent")
        assert result is None
    
    def test_write_file_cache_success(self, cache_repo, temp_cache_dir):
        """Test writing to file cache."""
        test_data = {"to": "file"}
        cache_repo._write_file_cache("write_key", test_data)
        
        cache_file = Path(temp_cache_dir) / "write_key.json"
        assert cache_file.exists()
        
        with open(cache_file) as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data
    
    def test_memory_and_file_cache_interaction(self, cache_repo):
        """Test interaction between memory and file cache."""
        # Set with persistence
        cache_repo.set("interaction_key", "value", persist=True)
        
        # Clear memory cache only
        cache_repo._memory_cache.clear()
        
        # Should still be able to get from file cache
        result = cache_repo.get("interaction_key")
        assert result == "value"
        
        # And should now be back in memory
        assert "interaction_key" in cache_repo._memory_cache
