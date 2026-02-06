"""
File Repository

Handles all file system operations for the application.
Provides safe, validated file access with proper error handling.
"""

import os
import json
import tarfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from config.logging_config import get_logger
from utils.validators import sanitize_path, is_safe_filename

logger = get_logger(__name__)


class FileRepository:
    """Repository for file system operations"""
    
    def __init__(self, base_dir: Optional[Union[str, Path]] = None):
        """
        Initialize file repository.
        
        Args:
            base_dir: Base directory for file operations. Defaults to current directory.
        """
        if base_dir is None:
            self.base_dir = Path.cwd()
        elif isinstance(base_dir, str):
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = base_dir
        logger.info(f"FileRepository initialized with base_dir: {self.base_dir}")
    
    def read_json(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Read and parse a JSON file.
        
        Args:
            file_path: Path to JSON file (relative to base_dir or absolute)
            
        Returns:
            Parsed JSON data, or None if file not found or invalid
        """
        try:
            full_path = self._resolve_path(file_path)
            
            if not full_path.exists():
                logger.warning(f"JSON file not found: {full_path}")
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"Read JSON file: {full_path}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading JSON file {file_path}: {e}")
            return None
    
    def write_json(self, file_path: Union[str, Path], data: Dict[str, Any], 
                   indent: int = 2) -> bool:
        """
        Write data to a JSON file.
        
        Args:
            file_path: Path to JSON file
            data: Data to write
            indent: JSON indentation (default 2)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = self._resolve_path(file_path)
            
            # Create directory if it doesn't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            
            logger.debug(f"Wrote JSON file: {full_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing JSON file {file_path}: {e}")
            return False
    
    def read_text(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        Read a text file.
        
        Args:
            file_path: Path to text file
            
        Returns:
            File contents, or None if error
        """
        try:
            full_path = self._resolve_path(file_path)
            
            if not full_path.exists():
                logger.warning(f"Text file not found: {full_path}")
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.debug(f"Read text file: {full_path} ({len(content)} bytes)")
            return content
            
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            return None
    
    def write_text(self, file_path: Union[str, Path], content: str) -> bool:
        """
        Write content to a text file.
        
        Args:
            file_path: Path to text file
            content: Content to write
            
        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = self._resolve_path(file_path)
            
            # Create directory if it doesn't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug(f"Wrote text file: {full_path} ({len(content)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Error writing text file {file_path}: {e}")
            return False
    
    def exists(self, file_path: Union[str, Path]) -> bool:
        """
        Check if a file or directory exists.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if exists, False otherwise
        """
        try:
            full_path = self._resolve_path(file_path)
            return full_path.exists()
        except Exception:
            return False
    
    def list_files(self, directory: Union[str, Path], 
                   pattern: str = "*") -> List[Path]:
        """
        List files in a directory matching a pattern.
        
        Args:
            directory: Directory to list
            pattern: Glob pattern (default "*")
            
        Returns:
            List of matching file paths
        """
        try:
            full_path = self._resolve_path(directory)
            
            if not full_path.is_dir():
                logger.warning(f"Not a directory: {full_path}")
                return []
            
            files = sorted(full_path.glob(pattern))
            logger.debug(f"Found {len(files)} files in {directory} matching {pattern}")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {e}")
            return []
    
    def create_tar(self, tar_path: Union[str, Path], 
                   source_dir: Union[str, Path]) -> bool:
        """
        Create a tar.gz archive.
        
        Args:
            tar_path: Path for the tar.gz file
            source_dir: Directory to archive
            
        Returns:
            True if successful, False otherwise
        """
        try:
            full_tar_path = self._resolve_path(tar_path)
            full_source_dir = self._resolve_path(source_dir)
            
            if not full_source_dir.is_dir():
                logger.error(f"Source directory not found: {full_source_dir}")
                return False
            
            with tarfile.open(full_tar_path, "w:gz") as tar:
                tar.add(full_source_dir, arcname=full_source_dir.name)
            
            logger.info(f"Created tar archive: {full_tar_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating tar archive: {e}")
            return False
    
    def _resolve_path(self, file_path: Union[str, Path]) -> Path:
        """
        Resolve a file path relative to base_dir or as absolute.
        
        Args:
            file_path: File path to resolve
            
        Returns:
            Resolved Path object
        """
        path = Path(file_path)
        
        if path.is_absolute():
            return path
        else:
            return self.base_dir / path
