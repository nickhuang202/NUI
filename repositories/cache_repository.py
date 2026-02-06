"""
Cache Repository

Handles caching operations for the application.
Provides in-memory and file-based caching with TTL support.
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, asdict
from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with data and metadata"""
    key: str
    data: Any
    timestamp: float
    ttl: Optional[int] = None  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl


class CacheRepository:
    """Repository for caching operations"""
    
    def __init__(self, cache_dir: Optional[Union[str, Path]] = None):
        """
        Initialize cache repository.
        
        Args:
            cache_dir: Directory for file-based cache. Defaults to .cache/
        """
        if cache_dir is None:
            self.cache_dir = Path('.cache')
        elif isinstance(cache_dir, str):
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = cache_dir
            
        self.cache_dir.mkdir(exist_ok=True)
        
        # In-memory cache
        self._memory_cache: Dict[str, CacheEntry] = {}
        
        logger.info(f"CacheRepository initialized with cache_dir: {self.cache_dir}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value, or None if not found or expired
        """
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            
            if entry.is_expired():
                logger.debug(f"Cache expired: {key}")
                del self._memory_cache[key]
                return None
            
            logger.debug(f"Cache hit (memory): {key}")
            return entry.data
        
        # Check file cache
        file_data = self._read_file_cache(key)
        if file_data is not None:
            logger.debug(f"Cache hit (file): {key}")
            # Populate memory cache
            self._memory_cache[key] = CacheEntry(
                key=key,
                data=file_data,
                timestamp=time.time()
            )
            return file_data
        
        logger.debug(f"Cache miss: {key}")
        return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None, 
            persist: bool = False) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (None = no expiration)
            persist: Whether to write to file cache
            
        Returns:
            True if successful
        """
        try:
            entry = CacheEntry(
                key=key,
                data=data,
                timestamp=time.time(),
                ttl=ttl
            )
            
            # Store in memory
            self._memory_cache[key] = entry
            
            # Optionally persist to file
            if persist:
                self._write_file_cache(key, data)
            
            logger.debug(f"Cache set: {key} (ttl={ttl}, persist={persist})")
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache for {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        deleted = False
        
        # Delete from memory
        if key in self._memory_cache:
            del self._memory_cache[key]
            deleted = True
        
        # Delete from file
        cache_file = self._get_cache_file(key)
        if cache_file.exists():
            cache_file.unlink()
            deleted = True
        
        if deleted:
            logger.debug(f"Cache deleted: {key}")
        
        return deleted
    
    def clear(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        # Clear memory cache
        count = len(self._memory_cache)
        self._memory_cache.clear()
        
        # Clear file cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except Exception as e:
                logger.error(f"Error deleting cache file {cache_file}: {e}")
        
        logger.info(f"Cache cleared: {count} entries removed")
        return count
    
    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            self.delete(key)
        
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        return len(expired_keys)
    
    def _get_cache_file(self, key: str) -> Path:
        """Get path to cache file for a key"""
        # Use safe filename
        safe_key = key.replace('/', '_').replace('\\', '_')
        return self.cache_dir / f"{safe_key}.json"
    
    def _read_file_cache(self, key: str) -> Optional[Any]:
        """Read cache entry from file"""
        try:
            cache_file = self._get_cache_file(key)
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            logger.error(f"Error reading cache file for {key}: {e}")
            return None
    
    def _write_file_cache(self, key: str, data: Any) -> bool:
        """Write cache entry to file"""
        try:
            cache_file = self._get_cache_file(key)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Error writing cache file for {key}: {e}")
            return False
