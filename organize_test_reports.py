#!/usr/bin/env python3
"""
Organize test reports from tar.gz archives into structured GDrive folders.

This script processes daily test archives and organizes them by:
- Test level (T0, T1, T2)
- Test category (SAI_Test, Agent_HW_test, Link_Test)
- Topology (optic_one, optic_two, copper)
- Date

Usage:
    python organize_test_reports.py <source_dir> <output_dir>
    
Example:
    python organize_test_reports.py test_report/ALL_DB/Bringup_Lab/WEDGE800BACT/AP29047231/all_test_2026-10-21 GDrive
"""

import os
import sys
import tarfile
import shutil
import re
import time
from pathlib import Path
from datetime import datetime


def is_file_being_written(file_path, wait_seconds=2):
    """
    Check if a file is currently being written to.
    Returns True if file is stable (not being written), False otherwise.
    
    This helps avoid processing incomplete tar.gz files when tests are running.
    """
    try:
        # Get initial file size and modification time
        stat1 = os.stat(file_path)
        size1 = stat1.st_size
        mtime1 = stat1.st_mtime
        
        # Wait a bit
        time.sleep(wait_seconds)
        
        # Check again
        stat2 = os.stat(file_path)
        size2 = stat2.st_size
        mtime2 = stat2.st_mtime
        
        # If size or mtime changed, file is being written
        if size1 != size2 or mtime1 != mtime2:
            return False  # File is being written
        
        return True  # File is stable
        
    except (OSError, FileNotFoundError):
        return False  # Can't access file


def is_archive_valid(archive_path):
    """
    Verify that a tar.gz archive is valid and complete.
    Returns True if valid, False otherwise.
    """
    try:
        with tarfile.open(archive_path, 'r:gz') as tar:
            # Try to list members - this will fail if archive is corrupted
            members = tar.getmembers()
            return len(members) > 0
    except (tarfile.TarError, EOFError, OSError) as e:
        return False


def split_log_tar_file(log_tar_path, output_log_dir):
    """
    Split a .log.tar.gz file into individual test log files.
    Extracts the tar, then splits the main log file into separate test logs.
    
    Args:
        log_tar_path: Path to the .log.tar.gz file
        output_log_dir: Directory where individual .log files will be placed
    """
    import tempfile
    
    # Define markers for splitting
    START_MARKER = "########## Running test:"
    END_MARKER = "Running all tests took"
    
    # Create a temporary directory for extraction
    temp_extract_dir = tempfile.mkdtemp(prefix='log_extract_')
    
    try:
        # First, extract the .log.tar.gz to get the .log file
        with tarfile.open(log_tar_path, 'r:gz') as tar:
            tar.extractall(path=temp_extract_dir)
        
        # Find the .log file (should be the main one without .tar.gz)
        log_files = []
        for root, dirs, files in os.walk(temp_extract_dir):
            for file in files:
                if file.endswith('.log') and not file.endswith('.tar.gz'):
                    log_files.append(os.path.join(root, file))
        
        if not log_files:
            print(f"      ⚠️  No .log file found inside {os.path.basename(log_tar_path)}")
            return 0
            return 0
        
        # Process the main log file (usually the first/largest one)
        source_log = log_files[0]
        
        current_file = None
        file_count = 0
        
        with open(source_log, 'r', encoding='utf-8', errors='replace') as infile:
            for line in infile:
                # Check for end marker
                if END_MARKER in line:
                    break
                
                # Check for start marker
                if START_MARKER in line:
                    if current_file:
                        current_file.close()
                    
                    parts = line.split(START_MARKER)
                    if len(parts) > 1:
                        test_name = parts[1].strip()
                        # Sanitize filename to prevent path issues
                        safe_filename = test_name.replace("/", "_").replace("\\", "_")
                        
                        output_path = os.path.join(output_log_dir, f"{safe_filename}.log")
                        current_file = open(output_path, 'w', encoding='utf-8')
                        file_count += 1
                
                # Write content
                if current_file:
                    current_file.write(line)
        
        if current_file:
            current_file.close()
        
        return file_count
        
    except Exception as e:
        print(f"      ❌ Error splitting log: {e}")
        return 0
    finally:
        # Clean up temp directory
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir, ignore_errors=True)


def parse_archive_info(filename):
    """
    Parse archive filename to extract category, level, and topology.
    
    Returns: dict with 'category', 'level', 'topology', 'date'
    """
    filename_upper = filename.upper()
    info = {
        'category': None,
        'level': None,
        'topology': None,
        'date': None,
        'original': filename
    }
    
    # Extract date from filename (YYYY-MM-DD format)
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if date_match:
        info['date'] = date_match.group(1)
    
    # Determine category and level
    if filename_upper.startswith('SAI_T0'):
        info['category'] = 'SAI_Test'
        info['level'] = 'T0'
    elif filename_upper.startswith('SAI_T1'):
        info['category'] = 'SAI_Test'
        info['level'] = 'T1'
    elif filename_upper.startswith('SAI_T2'):
        info['category'] = 'SAI_Test'
        info['level'] = 'T2'
    elif filename_upper.startswith('AGENT_HW_T0'):
        info['category'] = 'Agent_HW_test'
        info['level'] = 'T0'
    elif filename_upper.startswith('AGENT_HW_T1'):
        info['category'] = 'Agent_HW_test'
        info['level'] = 'T1'
    elif filename_upper.startswith('AGENT_HW_T2'):
        info['category'] = 'Agent_HW_test'
        info['level'] = 'T2'
    elif filename_upper.startswith('LINK_T0') or filename.lower().startswith('link_test'):
        info['category'] = 'Link_Test'
        info['level'] = 'T0'
        # Extract topology from LINK_T0 filename
        filename_lower = filename.lower()
        if 'optic_one' in filename_lower or 'optics_one' in filename_lower:
            info['topology'] = 'optic_one'
        elif 'optic_two' in filename_lower or 'optics_two' in filename_lower:
            info['topology'] = 'optic_two'
        elif 'copper' in filename_lower:
            info['topology'] = 'copper'
        elif 'basic' in filename_lower:
            info['topology'] = 'basic'
    elif filename_upper.startswith('LINK_T1'):
        info['category'] = 'Link_Test'
        info['level'] = 'T1'
        # Extract topology from LINK_T1 filename
        filename_lower = filename.lower()
        if 'optic_one' in filename_lower or 'optics_one' in filename_lower:
            info['topology'] = 'optic_one'
        elif 'optic_two' in filename_lower or 'optics_two' in filename_lower:
            info['topology'] = 'optic_two'
        elif 'copper' in filename_lower:
            info['topology'] = 'copper'
        elif 'basic' in filename_lower:
            info['topology'] = 'basic'
    elif filename_upper.startswith('LINK_T2'):
        info['category'] = 'Link_Test'
        info['level'] = 'T2'
        # Extract topology from LINK_T2 filename
        filename_lower = filename.lower()
        if 'optic_one' in filename_lower or 'optics_one' in filename_lower:
            info['topology'] = 'optic_one'
        elif 'optic_two' in filename_lower or 'optics_two' in filename_lower:
            info['topology'] = 'optic_two'
        elif 'copper' in filename_lower:
            info['topology'] = 'copper'
        elif 'basic' in filename_lower:
            info['topology'] = 'basic'
    elif filename_upper.startswith('EXITEVT'):
        info['category'] = 'ExitEVT'
        info['level'] = 'full_EVT+'
        # Extract topology from ExitEVT filename
        filename_lower = filename.lower()
        if 'optic_one' in filename_lower or 'optics_one' in filename_lower:
            info['topology'] = 'optic_one'
        elif 'optic_two' in filename_lower or 'optics_two' in filename_lower:
            info['topology'] = 'optic_two'
        elif 'copper' in filename_lower:
            info['topology'] = 'copper'
        elif '400g' in filename_lower:
            info['topology'] = '400g'
    
    return info


def get_file_category(filename):
    """Determine if file is config, log, or version info."""
    filename_lower = filename.lower()
    
    if filename == 'Version_Info.txt':
        return 'version'
    elif filename_lower.startswith('fruid') and filename_lower.endswith('.json'):
        return 'config'
    elif 'platform_mapping.json' in filename_lower:
        return 'config'
    elif 'materialized_json' in filename_lower or filename_lower.endswith('.materialized_json'):
        return 'config'
    elif filename_lower.endswith('.log.tar.gz') or filename_lower.endswith('.log'):
        return 'log'
    elif filename_lower.endswith('.csv'):
        return 'csv'
    elif filename_lower.endswith('.xlsx'):
        return 'xlsx'
    elif filename_lower.startswith('fboss2_show') and filename_lower.endswith('.txt'):
        return 'log'
    else:
        return None


def extract_and_organize_archive(archive_path, output_base_dir):
    """
    Extract archive and organize files into proper directory structure.
    Returns True if successful, False otherwise.
    """
    archive_name = os.path.basename(archive_path)
    
    # Check if file is being written or is invalid
    if not is_file_being_written(archive_path, wait_seconds=1):
        print(f"⚠️  Skipping {archive_name} - file is being written or modified recently")
        return False
    
    if not is_archive_valid(archive_path):
        print(f"⚠️  Skipping {archive_name} - archive is invalid or corrupted")
        return False
    
    info = parse_archive_info(archive_name)
    
    if not info['category']:
        print(f"⚠️  Skipping unknown archive type: {archive_name}")
        return False
    
    print(f"\n📦 Processing: {archive_name}")
    print(f"   Category: {info['category']}, Level: {info['level']}, Topology: {info['topology']}")
    
    # Determine target directory structure
    if info['level'] == 'full_EVT+':
        # ExitEVT structure
        base_dir = os.path.join(output_base_dir, 'full_EVT+')
        if info['date']:
            date_dir = os.path.join(base_dir, info['date'].replace('-', ''))
        else:
            date_dir = base_dir
        
        if info['topology']:
            topology_dir = os.path.join(date_dir, info['topology'])
        else:
            topology_dir = date_dir
            
        config_dir = os.path.join(topology_dir, 'Configs')
        log_dir = os.path.join(topology_dir, 'Logs')
        qsfp_config_dir = os.path.join(config_dir, 'qsfp_test_configs')
        
    else:
        # T0/T1/T2 structure
        level_dir = os.path.join(output_base_dir, info['level'])
        
        if info['date']:
            date_dir = os.path.join(level_dir, info['date'].replace('-', ''))
        else:
            date_dir = level_dir
        
        if info['category'] == 'Link_Test':
            category_dir = os.path.join(date_dir, 'Link_Test')
            if info['topology']:
                topology_dir = os.path.join(category_dir, info['topology'])
            else:
                topology_dir = category_dir
            config_dir = os.path.join(topology_dir, 'Configs')
            log_dir = os.path.join(topology_dir, 'Logs')
            qsfp_config_dir = os.path.join(config_dir, 'qsfp_test_configs')
        else:
            category_dir = os.path.join(date_dir, info['category'])
            config_dir = os.path.join(category_dir, 'Configs')
            log_dir = os.path.join(category_dir, 'Logs')
            qsfp_config_dir = None
    
    # Create directories
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    if qsfp_config_dir:
        os.makedirs(qsfp_config_dir, exist_ok=True)
    
    print(f"   📂 Directories:")
    print(f"      Config: {config_dir}")
    print(f"      Logs: {log_dir}")
    
    # Extract and organize files
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix='organize_extract_')
    
    try:
        with tarfile.open(archive_path, 'r:gz') as tar:
            members = tar.getmembers()
            
            files_copied = {'version': 0, 'config': 0, 'log': 0, 'qsfp': 0, 'csv': 0, 'xlsx': 0}
            log_tar_files = []  # Track .log.tar.gz files for splitting
            
            for member in members:
                if member.isfile():
                    filename = os.path.basename(member.name)
                    file_cat = get_file_category(filename)
                    
                    if file_cat == 'version':
                        # Version_Info.txt goes to date directory
                        target = os.path.join(date_dir if info['level'] != 'full_EVT+' else date_dir, filename)
                        # Extract to temp dir and copy
                        tar.extract(member, path=temp_dir)
                        extracted_path = os.path.join(temp_dir, member.name)
                        shutil.copy2(extracted_path, target)
                        files_copied['version'] += 1
                        print(f"   ✓ Version: {filename}")
                        
                    elif file_cat == 'config':
                        # Check if it's a qsfp_test_configs file
                        if 'qsfp_test_configs' in member.name and qsfp_config_dir:
                            target = os.path.join(qsfp_config_dir, filename)
                            files_copied['qsfp'] += 1
                        else:
                            target = os.path.join(config_dir, filename)
                            files_copied['config'] += 1
                        
                        tar.extract(member, path=temp_dir)
                        extracted_path = os.path.join(temp_dir, member.name)
                        shutil.copy2(extracted_path, target)
                        
                    elif file_cat == 'log':
                        target = os.path.join(log_dir, filename)
                        tar.extract(member, path=temp_dir)
                        extracted_path = os.path.join(temp_dir, member.name)
                        shutil.copy2(extracted_path, target)
                        files_copied['log'] += 1
                        
                        # Track .log.tar.gz files for splitting
                        if filename.endswith('.log.tar.gz'):
                            log_tar_files.append(target)
                        
                    elif file_cat == 'csv' or file_cat == 'xlsx':
                        # CSV and XLSX files go to parent directory of Logs (topology_dir or category_dir)
                        if info['category'] == 'Link_Test' or info['level'] == 'full_EVT+':
                            # For Link_Test and ExitEVT, place in topology directory
                            target = os.path.join(topology_dir, filename)
                        else:
                            # For SAI/Agent_HW, place in category directory
                            target = os.path.join(category_dir, filename)
                        
                        tar.extract(member, path=temp_dir)
                        extracted_path = os.path.join(temp_dir, member.name)
                        shutil.copy2(extracted_path, target)
                        files_copied[file_cat] += 1
            
            print(f"   ✅ Copied: {files_copied['version']} version, {files_copied['config']} configs, "
                  f"{files_copied['log']} logs, {files_copied['csv']} csv, {files_copied['xlsx']} xlsx, "
                  f"{files_copied['qsfp']} qsfp configs")
            
            # Verify files were actually created
            total_files = sum(files_copied.values())
            print(f"   📊 Total files copied: {total_files}")
            
            # Split log tar files into individual test logs
            if log_tar_files:
                print(f"   🔧 Splitting {len(log_tar_files)} log file(s) into individual test logs...")
                total_split_logs = 0
                for log_tar in log_tar_files:
                    split_count = split_log_tar_file(log_tar, log_dir)
                    if split_count > 0:
                        total_split_logs += split_count
                        print(f"      ✓ {os.path.basename(log_tar)}: {split_count} test logs extracted")
                
                if total_split_logs > 0:
                    print(f"   ✅ Total {total_split_logs} individual test log files created")
            
            return True  # Successfully processed
                
    except Exception as e:
        print(f"   ❌ Error processing archive: {e}")
        import traceback
        traceback.print_exc()
        return False  # Failed to process
    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def organize_test_reports(source_dir, output_dir):
    """
    Main function to organize all test reports from source directory.
    """
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return 1
    
    print(f"🔍 Scanning: {source_dir}")
    print(f"📁 Output: {output_dir}")
    print("=" * 80)
    
    # Find all .tar.gz files
    archives = list(source_path.glob('*.tar.gz'))
    
    if not archives:
        print("⚠️  No .tar.gz files found in source directory")
        # List what files are present for debugging
        all_files = list(source_path.glob('*'))
        if all_files:
            print(f"ℹ️  Found {len(all_files)} other files:")
            for f in all_files[:10]:  # Show first 10
                print(f"    - {f.name}")
            if len(all_files) > 10:
                print(f"    ... and {len(all_files) - 10} more")
        else:
            print("ℹ️  Source directory is empty")
        return 0  # Exit cleanly but with no files processed
    
    print(f"Found {len(archives)} archive(s)")
    
    processed_count = 0
    # Process each archive
    for archive in sorted(archives):
        result = extract_and_organize_archive(str(archive), output_dir)
        if result:  # If successfully processed
            processed_count += 1
    
    print("\n" + "=" * 80)
    if processed_count > 0:
        print(f"✅ Organization complete! Processed {processed_count} archive(s)")
        print(f"📁 Output directory: {os.path.abspath(output_dir)}")
        
        # Count and list generated files
        total_files = 0
        total_dirs = 0
        for root, dirs, files in os.walk(output_dir):
            total_dirs += len(dirs)
            total_files += len(files)
        
        print(f"📊 Generated: {total_files} files in {total_dirs} directories")
        
        if total_files == 0:
            print("⚠️  Warning: No files were generated in output directory!")
            print("   This might indicate an issue with file copying.")
            return 1  # Exit with error code if no files generated
    else:
        print("⚠️  No archives were successfully processed")
        return 1

    return 0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\n❌ Error: Missing required arguments")
        print("\nUsage:")
        print("  python organize_test_reports.py <source_dir> <output_dir>")
        print("\nExample:")
        print("  python organize_test_reports.py test_report/ALL_DB/Bringup_Lab/WEDGE800BACT/AP29047231/all_test_2026-10-21 GDrive")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    exit_code = organize_test_reports(source_dir, output_dir)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
