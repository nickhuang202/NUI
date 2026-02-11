#!/usr/bin/env python3
"""
NUI Project Release Archive Creator
Creates a versioned tar.gz archive of the NUI project
Cross-platform Python version
"""

import os
import sys
import tarfile
import shutil
from datetime import datetime
from pathlib import Path
import platform

# Version number (update this for each release)
VERSION = "v0.0.1.7"
PROJECT_NAME = "NUI"

# Files and directories to exclude
EXCLUDE_PATTERNS = [
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '.git',
    '.gitignore',
    '.vscode',
    '.idea',
    '*.log',
    '*.tmp',
    '*.swp',
    '*~',
    '.DS_Store',
    'venv',
    '.venv',
    'env',
    '.env',
    'test_report/',  # Exclude entire test_report directory
]

def should_exclude(path):
    """Check if a path should be excluded based on patterns"""
    path_str = str(path).replace('\\', '/')
    name = os.path.basename(path_str)
    
    for pattern in EXCLUDE_PATTERNS:
        # Handle path patterns with ** (e.g., test_report/**/*.tar.gz)
        if '**' in pattern:
            pattern_parts = pattern.split('**')
            if len(pattern_parts) == 2:
                prefix = pattern_parts[0].rstrip('/')
                suffix = pattern_parts[1].lstrip('/')
                
                # Check if path contains the prefix and ends with matching suffix
                if prefix in path_str:
                    # Extract the part after prefix
                    if suffix.startswith('*'):
                        # Wildcard suffix like *.tar.gz
                        ext = suffix[1:]
                        if path_str.endswith(ext):
                            return True
        elif pattern.startswith('*'):
            # Wildcard pattern
            if name.endswith(pattern[1:]):
                return True
        elif pattern.endswith('*'):
            # Wildcard pattern
            if name.startswith(pattern[:-1]):
                return True
        elif pattern.endswith('/'):
            # Directory pattern - check if path contains this directory
            dir_pattern = pattern.rstrip('/')
            path_parts = path_str.split('/')
            if dir_pattern in path_parts:
                return True
        else:
            # Exact match - only match exact filename
            if name == pattern:
                return True
    return False

def get_dir_size(path):
    """Calculate directory size"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size

def format_size(size_bytes):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def create_release_info(output_dir):
    """Create RELEASE_INFO.txt file"""
    info_file = output_dir / "RELEASE_INFO.txt"
    
    content = f"""NUI Project Release Information
================================

Version: {VERSION}

0. 0.0.1.0 [2026-2-03] Refactored project structure for better modularity. 
1. 0.0.1.1 [2026-2-04] Add profile 54 , 24 UI support 
2. 0.0.1.2 [2026-2-05] Enhance lab_monitor feature 
3. 0.0.1.3 [2026-2-05] Add REST API 
4. 0.0.1.4 [2026-2-05] Add offline viewer of topology  
5. 0.0.1.5 [2026-2-06] Enhance trand showing content 
6. 0.0.1.6 [2026-2-07] Refactor cict test script
7. 0.0.1.7 [2026-2-11] Enhance ExitEvt.sh

Release Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Created By: {os.getenv('USER', os.getenv('USERNAME', 'unknown'))}@{platform.node()}
Platform: {platform.system()} {platform.release()}

Package Contents:
- Flask Web Application (app.py)
- Configuration Converters (convert.py, reconvert.py)
- Port Pair Checker (check_port_pairs.py)
- HTML Frontend (NUI.html)
- Documentation (docs/)
- Topology Files (Topology/)
- Link Test Configs (link_test_configs/)
- FBOSS Source (fboss_src/)
- Requirements (requirements.txt, requirements.lock)
- UV project metadata (pyproject.toml)

Installation (uv recommended):
1. Extract archive: tar -xzf {PROJECT_NAME}.tar.gz
2. Navigate to directory: cd {PROJECT_NAME}
3. Install uv and create venv: uv venv
4. Sync deps: uv pip sync requirements.lock
5. Run application: uv run python app.py

Alternative (pip):
1. Install dependencies: pip install -r requirements.txt
2. Run application: python app.py

For detailed documentation, see docs/SPEC.md and docs/README.md

================================
"""
    
    with open(info_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return info_file

def create_version_file(output_dir):
    """Create VERSION file"""
    version_file = output_dir / "VERSION"
    with open(version_file, 'w', encoding='utf-8') as f:
        f.write(f"{VERSION}\n")
    return version_file

def create_archive():
    """Main function to create the release archive"""
    
    # Get paths
    script_dir = Path(__file__).parent.absolute()
    parent_dir = script_dir.parent
    archive_name = f"{PROJECT_NAME}_{VERSION}.tar.gz"
    output_path = parent_dir / archive_name
    
    print("=" * 50)
    print("NUI Project Release Archive Creator")
    print("=" * 50)
    print(f"Version: {VERSION}")
    print(f"Source: {script_dir}")
    print(f"Output: {output_path}")
    print("=" * 50)
    print()
    
    # Create VERSION file in source directory
    print("Creating VERSION file...")
    version_file = create_version_file(script_dir)
    print(f"✓ Created: {version_file.name}")
    
    # Create RELEASE_INFO.txt in source directory
    print("Creating RELEASE_INFO.txt...")
    info_file = create_release_info(script_dir)
    print(f"✓ Created: {info_file.name}")
    print()
    
    # Create tar.gz archive
    print("Creating tar.gz archive...")
    print("Scanning and compressing files...")
    
    file_count = 0
    total_size = 0
    
    try:
        with tarfile.open(output_path, 'w:gz') as tar:
            for root, dirs, files in os.walk(script_dir):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d)]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    # Skip excluded files
                    if should_exclude(file_path):
                        continue
                    
                    # Calculate relative path
                    rel_path = file_path.relative_to(script_dir.parent)
                    arcname = f"{PROJECT_NAME}" / rel_path.relative_to(script_dir.name)
                    
                    # Add to archive
                    tar.add(file_path, arcname=arcname)
                    file_count += 1
                    
                    # Show progress every 10 files
                    if file_count % 10 == 0:
                        print(f"  Added {file_count} files...", end='\r')
        
        print(f"  Added {file_count} files... Done!     ")
        print()
        
        # Get archive size
        archive_size = os.path.getsize(output_path)
        
        print("=" * 50)
        print("✓ Archive created successfully!")
        print("=" * 50)
        print(f"File: {output_path}")
        print(f"Size: {format_size(archive_size)}")
        print(f"Files: {file_count}")
        print("=" * 50)
        print()
        
        # List first 20 files in archive
        print("Archive contents (first 20 files):")
        with tarfile.open(output_path, 'r:gz') as tar:
            members = tar.getmembers()[:20]
            for member in members:
                print(f"  {member.name}")
            if len(tar.getmembers()) > 20:
                print(f"  ... ({len(tar.getmembers())} total files)")
        
        print()
        print("Release archive ready for distribution!")
        return 0
        
    except Exception as e:
        print("=" * 50)
        print("✗ Error creating archive")
        print("=" * 50)
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(create_archive())
