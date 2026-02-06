import os
import tarfile
import re
import csv
import io
import json
from datetime import datetime

TEST_REPORT_BASE = os.path.join(os.getcwd(), "test_report")
CACHE_FILENAME = "_dashboard_cache.json"

def _get_cache_file_path(target_dir):
    """Get cache file path for a test report directory."""
    return os.path.join(target_dir, CACHE_FILENAME)

def _is_cache_valid(target_dir, cache_file):
    """Check if cache file is valid (newer than all tar.gz files and test directories)."""
    if not os.path.exists(cache_file):
        return False
    
    cache_mtime = os.path.getmtime(cache_file)
    
    # Check if any tar.gz files or test directories are newer than cache
    for filename in os.listdir(target_dir):
        if filename == CACHE_FILENAME:
            continue
            
        item_path = os.path.join(target_dir, filename)
        
        # Check tar archives
        if filename.endswith('.tar.gz') or filename.endswith('.tgz'):
            if os.path.getmtime(item_path) > cache_mtime:
                return False
        
        # Check test directories (exclude cache file)
        elif os.path.isdir(item_path):
            if os.path.getmtime(item_path) > cache_mtime:
                return False
    
    return True

def _load_from_cache(cache_file):
    """Load summary from cache file."""
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[CACHE] Loaded from cache: {cache_file}")
        # Ensure notes field exists
        if 'notes' not in data:
            data['notes'] = {}
        return data
    except Exception as e:
        print(f"[CACHE] Error loading cache (corrupt), removing file: {e}")
        try:
            os.remove(cache_file)
        except OSError:
            pass
        return None

def _save_to_cache(cache_file, summary):
    """Save summary to cache file, preserving existing notes."""
    try:
        # Load existing notes if cache file exists
        existing_notes = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    existing_notes = existing_data.get('notes', {})
            except (IOError, OSError, json.JSONDecodeError):
                pass  # Cache file corrupted or unreadable, start fresh
        
        # Cache including debug_logs so they persist
        cache_data = summary.copy()
        
        # Merge existing notes with new data (existing notes take precedence)
        cache_data['notes'] = existing_notes
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"[CACHE] Saved to cache: {cache_file} (with {len(existing_notes)} notes)")
        return True
    except Exception as e:
        print(f"[CACHE] Error saving cache: {e}")
        return False

def list_dashboard_dates(platform):
    """List available date folders for a platform."""
    platform_dir = os.path.join(TEST_REPORT_BASE, platform)
    if not os.path.exists(platform_dir):
        return []
    
    dates = []
    for item in os.listdir(platform_dir):
        if item.startswith("all_test_") and os.path.isdir(os.path.join(platform_dir, item)):
            # Extract date part: all_test_YYYY-MM-DD
            date_str = item.replace("all_test_", "")
            # Normalize date format to ensure leading zeros (YYYY-MM-DD)
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                normalized_date = parsed_date.strftime("%Y-%m-%d")
                dates.append(normalized_date)
            except ValueError:
                # If date parsing fails, keep original format
                dates.append(date_str)
    
    # Sort dates properly (most recent first)
    dates.sort(key=lambda d: datetime.strptime(d, "%Y-%m-%d") if d.count('-') == 2 else d, reverse=True)
    return dates

def get_dashboard_summary(platform, date_str):
    """Generate summary data for the dashboard with caching."""
    target_dir = os.path.join(TEST_REPORT_BASE, platform, f"all_test_{date_str}")
    if not os.path.isdir(target_dir):
        return None
    
    # Check if cache exists and is valid
    cache_file = _get_cache_file_path(target_dir)
    if _is_cache_valid(target_dir, cache_file):
        cached_data = _load_from_cache(cache_file)
        if cached_data:
            return cached_data
    
    # No valid cache, parse from tar files
    print(f"[CACHE] Parsing tar files for {platform}/{date_str}")

    summary = {
        "platform": platform,
        "date": date_str,
        "version_info": {},
        "tests": {
            "sai": {
                "t0": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None}, 
                "t1": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None},
                "t2": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None}
            },
            "agent_hw": {
                "t0": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None}, 
                "t1": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None},
                "t2": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None}
            },
            "link": {
                "t0": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "topology": None, "timestamp": None}, 
                "t1": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "topology": None, "timestamp": None},
                "t2": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "topology": None, "timestamp": None},
                "ev": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None},
                "ev_default": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None},
                "ev_400g": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None},
                "ev_optics_one": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None},
                "ev_optics_two": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None},
                "ev_copper": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None}
            },
            "link_test": {
                "default": {"passed": 0, "failed": 0, "total": 0, "items": [], "start_time": None, "end_time": None, "duration": None, "timestamp": None}
            }
        },
        "all_tests": {"passed": 0, "failed": 0, "total": 0},
        "test_times": {"start": None, "end": None, "duration": None},
        "debug_logs": []
    }

    def log(msg):
        summary["debug_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    log(f"Scanning directory: {target_dir}")

    # Iterate through archives and directories
    files = os.listdir(target_dir)
    log(f"Found {len(files)} items: {files}")

    for filename in files:
        # Skip cache file
        if filename == CACHE_FILENAME:
            continue
            
        filepath = os.path.join(target_dir, filename)
        
        # Check if it's a tar archive or directory
        is_tar = filename.endswith(".tar.gz") or filename.endswith(".tgz")
        is_dir = os.path.isdir(filepath)
        
        if not is_tar and not is_dir:
            log(f"Skipping non-tar/non-directory item: {filename}")
            continue

        log(f"Processing {'archive' if is_tar else 'directory'}: {filename}")
        
        # Determine category and level from filename early for TEST_STATUS parsing
        category = None
        level = None
        filename_upper = filename.upper()
        
        if filename_upper.startswith("AGENT_HW_T0"):
            category = "agent_hw"
            level = "t0"
        elif filename_upper.startswith("AGENT_HW_T1"):
            category = "agent_hw"
            level = "t1"
        elif filename_upper.startswith("AGENT_HW_T2"):
            category = "agent_hw"
            level = "t2"
        elif filename_upper.startswith("EXITEVT"):
            category = "link"
            # Extract topology from filename
            # Format: ExitEVT_{PLATFORM}_{VERSION}_{TOPOLOGY}_{DATE}.tar.gz
            filename_lower = filename.lower()
            topology = "default"
            
            # Check for topology patterns in the filename
            if "_optic_one_" in filename_lower or filename_lower.endswith("_optic_one.tar.gz"):
                topology = "optics_one"
            elif "_optic_two_" in filename_lower or filename_lower.endswith("_optic_two.tar.gz"):
                topology = "optics_two"
            elif "_optics_one_" in filename_lower or filename_lower.endswith("_optics_one.tar.gz"):
                topology = "optics_one"
            elif "_optics_two_" in filename_lower or filename_lower.endswith("_optics_two.tar.gz"):
                topology = "optics_two"
            elif "_copper_" in filename_lower or filename_lower.endswith("_copper.tar.gz"):
                topology = "copper"
            elif "_400g_" in filename_lower or filename_lower.endswith("_400g.tar.gz"):
                topology = "400g"
            elif "_default_" in filename_lower or filename_lower.endswith("_default.tar.gz"):
                topology = "default"
            
            level = f"ev_{topology}"
        elif filename_upper.startswith("LINK_T0"):
            category = "link"
            level = "t0"
            # Extract topology from LINK_T0 filename
            # Format examples: LINK_T0_*.zst_optic_one_*, LINK_T0_*_copper_*, LINK_T0_*_400g_*
            topology = "default"  # default topology
            filename_lower = filename.lower()
            if "_optic_one" in filename_lower or "optic_one_" in filename_lower:
                topology = "optic_one"
            elif "_optic_two" in filename_lower or "optic_two_" in filename_lower:
                topology = "optic_two"
            elif "_copper" in filename_lower or "copper_" in filename_lower:
                topology = "copper"
            elif "_400g" in filename_lower or "400g_" in filename_lower:
                topology = "400g"
            # Store topology info in the summary
            if summary["tests"]["link"]["t0"]["topology"] is None:
                summary["tests"]["link"]["t0"]["topology"] = topology
                log(f"LINK_T0 test detected with topology: {topology}")
        elif filename_upper.startswith("LINK_T1"):
            category = "link"
            level = "t1"
            # Extract topology from LINK_T1 filename
            # Format examples: LINK_T1_*.zst_optics_two_*, LINK_T1_*_copper_*, LINK_T1_*_400g_*
            topology = "default"  # default topology
            filename_lower = filename.lower()
            if "_optic_one" in filename_lower or "optic_one_" in filename_lower:
                topology = "optic_one"
            elif "_optic_two" in filename_lower or "optic_two_" in filename_lower:
                topology = "optic_two"
            elif "_optics_one" in filename_lower or "optics_one_" in filename_lower:
                topology = "optics_one"
            elif "_optics_two" in filename_lower or "optics_two_" in filename_lower:
                topology = "optics_two"
            elif "_copper" in filename_lower or "copper_" in filename_lower:
                topology = "copper"
            elif "_400g" in filename_lower or "400g_" in filename_lower:
                topology = "400g"
            # Store topology info in the summary
            if summary["tests"]["link"]["t1"]["topology"] is None:
                summary["tests"]["link"]["t1"]["topology"] = topology
                log(f"LINK_T1 test detected with topology: {topology}")
        elif filename_upper.startswith("LINK_T2"):
            category = "link"
            level = "t2"
            # Extract topology from LINK_T2 filename
            topology = "default"  # default topology
            filename_lower = filename.lower()
            if "_optic_one" in filename_lower or "optic_one_" in filename_lower:
                topology = "optic_one"
            elif "_optic_two" in filename_lower or "optic_two_" in filename_lower:
                topology = "optic_two"
            elif "_optics_one" in filename_lower or "optics_one_" in filename_lower:
                topology = "optics_one"
            elif "_optics_two" in filename_lower or "optics_two_" in filename_lower:
                topology = "optics_two"
            elif "_copper" in filename_lower or "copper_" in filename_lower:
                topology = "copper"
            elif "_400g" in filename_lower or "400g_" in filename_lower:
                topology = "400g"
            # Store topology info in the summary
            if summary["tests"]["link"]["t2"]["topology"] is None:
                summary["tests"]["link"]["t2"]["topology"] = topology
                log(f"LINK_T2 test detected with topology: {topology}")
        elif filename_upper.startswith("SAI_T0"):
            category = "sai"
            level = "t0"
        elif filename_upper.startswith("SAI_T1"):
            category = "sai"
            level = "t1"
        elif filename_upper.startswith("SAI_T2"):
            category = "sai"
            level = "t2"
        elif filename_upper.startswith("LINKTEST_LOG_"):
            category = "link_test"
            level = "default"
        
        try:
            if is_tar:
                # Process tar archive (existing logic)
                with tarfile.open(filepath, "r:gz") as tar:
                    # 1. Extract Version Info (only need once)
                    if not summary["version_info"]:
                        version_file = None
                        # Try both path variants
                        for vpath in ["./Version_Info.txt", "Version_Info.txt"]:
                            try:
                                version_file = tar.extractfile(vpath)
                                if version_file:
                                    log(f"Found Version_Info at {vpath}")
                                    break
                            except KeyError:
                                continue
                                
                        if version_file:
                            try:
                                content = version_file.read().decode('utf-8')
                                summary["version_info"] = parse_version_info(content)
                                log("Parsed Version_Info successfully")
                            except Exception as e:
                                log(f"Error parse version info in {filename}: {e}")

                    # 1b. Extract Extended Version Info for MP3N (LINKTEST_LOG)
                    if filename_upper.startswith("LINKTEST_LOG_"):
                        log(f"Detected LINKTEST_LOG: {filename}")
                        
                        # Parse version info from filename
                        # Format: LINKTEST_LOG_YYYYMMDD-HHMM_<binary>_<sdk>_<sai>.tar.tgz
                        try:
                            # Remove extension and split by underscore
                            name_parts = filename.replace(".tar.gz", "").replace(".tgz", "").split("_")
                            
                            # Extract binary info (fboss_bins_nv_YYYYMMDD_HH_MM_SS_HASH)
                            binary_parts = []
                            sdk_version = None
                            sai_build = None
                            
                            i = 0
                            while i < len(name_parts):
                                part = name_parts[i]
                                
                                # Look for SDK version
                                if part.upper().startswith("SWITCH") and i + 1 < len(name_parts) and name_parts[i+1].upper().startswith("SDK"):
                                    # Switch_SDK_v4_8_2108
                                    sdk_parts = []
                                    while i < len(name_parts) and not name_parts[i].upper().startswith("SAIBUILD"):
                                        sdk_parts.append(name_parts[i])
                                        i += 1
                                    sdk_version = "_".join(sdk_parts)
                                    continue
                                
                                # Look for SAI Build
                                if part.upper().startswith("SAIBUILD"):
                                    # SAIBuild2505_34_0_13
                                    sai_parts = []
                                    while i < len(name_parts):
                                        sai_parts.append(name_parts[i])
                                        i += 1
                                    sai_build = "_".join(sai_parts)
                                    break
                                
                                # Collect binary parts (skip LINKTEST, LOG, date-time)
                                if not part.startswith("LINKTEST") and not part.startswith("LOG") and not re.match(r'\d{8}-\d{4}', part):
                                    binary_parts.append(part)
                                
                                i += 1
                            
                            if binary_parts:
                                binary_name = "_".join(binary_parts)
                                summary["version_info"]["FBOSS_BINARY"] = binary_name
                                log(f"Extracted Binary from filename: {binary_name}")
                            
                            if sdk_version:
                                summary["version_info"]["SDK_VERSION"] = sdk_version
                                log(f"Extracted SDK Version from filename: {sdk_version}")
                            
                            if sai_build:
                                summary["version_info"]["SAI_BUILD"] = sai_build
                                log(f"Extracted SAI Build from filename: {sai_build}")
                        
                        except Exception as e:
                            log(f"Error parsing version from filename: {e}")
                        
                        # Try to parse HW_info.txt
                        try:
                            hw_info_file = None
                            for hpath in ["./HW_info.txt", "HW_info.txt"]:
                                try:
                                    hw_info_file = tar.extractfile(hpath)
                                    if hw_info_file:
                                        break
                                except KeyError:
                                    continue
                            
                            if hw_info_file:
                                content = hw_info_file.read().decode('utf-8', errors='ignore')
                                summary["version_info"].update(parse_hw_info(content, log))
                                log("Parsed HW_info.txt successfully")
                        except Exception as e:
                            log(f"Error parsing HW_info.txt in {filename}: {e}")

                        # Try to parse mp3n_sdk_ver_fw_ver.txt
                        try:
                            fw_info_file = None
                            for fpath in ["./mp3n_sdk_ver_fw_ver.txt", "mp3n_sdk_ver_fw_ver.txt"]:
                                try:
                                    fw_info_file = tar.extractfile(fpath)
                                    if fw_info_file:
                                        break
                                except KeyError:
                                    continue
                            
                            if fw_info_file:
                                content = fw_info_file.read().decode('utf-8', errors='ignore')
                                summary["version_info"].update(parse_fw_info(content, log))
                                log("Parsed mp3n_sdk_ver_fw_ver.txt successfully")
                        except Exception as e:
                            log(f"Error parsing mp3n_sdk_ver_fw_ver.txt in {filename}: {e}")

                        # Try to parse fboss_commit_url.txt
                        try:
                            commit_file = None
                            for cpath in ["./fboss_commit_url.txt", "fboss_commit_url.txt"]:
                                try:
                                    commit_file = tar.extractfile(cpath)
                                    if commit_file:
                                        break
                                except KeyError:
                                    continue
                            
                            if commit_file:
                                content = commit_file.read().decode('utf-8', errors='ignore').strip()
                                if content:
                                    summary["version_info"]["FBOSS_COMMIT_URL"] = content
                                    # Extract commit ID from URL
                                    if "/commit/" in content:
                                        commit_id = content.split("/commit/")[-1]
                                        summary["version_info"]["FBOSS_COMMIT_ID"] = commit_id
                                        log(f"Found FBOSS Commit URL: {content}")
                                        log(f"Found FBOSS Commit ID: {commit_id}")
                        except Exception as e:
                            log(f"Error parsing fboss_commit_url.txt in {filename}: {e}")

                    # 1c. Extract commit hash from filename if not found in commit file
                    # Format: *_20260115_13_18_02_94239f9ce8_*
                    if not summary["version_info"].get("FBOSS_COMMIT_ID"):
                        import re
                        # Look for pattern: timestamp_hash where hash is 10 hex chars
                        match = re.search(r'_(\d{8}_\d{2}_\d{2}_\d{2})_([a-f0-9]{10})_', filename.lower())
                        if match:
                            commit_hash = match.group(2)
                            summary["version_info"]["FBOSS_COMMIT_ID"] = commit_hash
                            log(f"Extracted commit hash from filename: {commit_hash}")

                    # 2. Extract TEST_STATUS for timing info
                    status_file = None
                    for spath in ["./TEST_STATUS", "TEST_STATUS"]:
                        try:
                            status_file = tar.extractfile(spath)
                            if status_file:
                                log(f"Found TEST_STATUS at {spath}")
                                break
                        except KeyError:
                            continue
                    
                    if status_file:
                        try:
                            content = status_file.read().decode('utf-8')
                            parse_test_times(summary, content, filename, category, level, log)
                        except Exception as e:
                            log(f"Error parsing TEST_STATUS in {filename}: {e}")

                    # 3. Extract Test Results (CSV) with validation from log file
                    # Look for CSV files in the archive
                    members = tar.getmembers()
                    log(f"Archive contains {len(members)} members")
                    
                    # First, extract available test names from the log file
                    available_tests = set()
                    for member in members:
                        if member.name.endswith(".log"):
                            log(f"Found log file: {member.name} for validation")
                            try:
                                f = tar.extractfile(member)
                                if f:
                                    log_content = f.read().decode('utf-8', errors='ignore')
                                    # Extract test names from "########## Running test:" markers
                                    import re
                                    test_matches = re.findall(r'#{10,}\s+Running test:\s+(\S+)', log_content)
                                    available_tests.update(test_matches)
                                    log(f"Found {len(available_tests)} unique tests in log file")
                            except Exception as e:
                                log(f"Error reading log file {member.name}: {e}")
                    
                    csv_found = False
                    for member in members:
                        if member.name.endswith(".csv"):
                            log(f"Found CSV: {member.name}")
                            f = tar.extractfile(member)
                            if f:
                                content = f.read().decode('utf-8')
                                update_test_stats(summary, filename, content, log, available_tests)
                                csv_found = True
                    
                    if not csv_found:
                        log(f"No CSV files found in {filename}")
            
            else:  # is_dir
                # Process extracted directory
                log(f"Processing directory: {filepath}")
                
                # 1. Extract Version Info (only need once)
                if not summary["version_info"]:
                    version_path = os.path.join(filepath, "Version_Info.txt")
                    if os.path.exists(version_path):
                        try:
                            with open(version_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                summary["version_info"] = parse_version_info(content)
                                log("Parsed Version_Info successfully from directory")
                        except Exception as e:
                            log(f"Error parsing Version_Info in directory {filename}: {e}")
                
                # 2. Look for TEST_STATUS (may not exist in extracted dirs)
                status_path = os.path.join(filepath, "TEST_STATUS")
                if os.path.exists(status_path):
                    try:
                        with open(status_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            parse_test_times(summary, content, filename, category, level, log)
                    except Exception as e:
                        log(f"Error parsing TEST_STATUS in directory {filename}: {e}")
                
                # 3. Look for CSV files with validation from log files
                # First extract available tests from log files
                available_tests = set()
                for root, dirs, dir_files in os.walk(filepath):
                    for file in dir_files:
                        if file.endswith(".log"):
                            log_path = os.path.join(root, file)
                            log(f"Found log file: {log_path} for validation")
                            try:
                                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    log_content = f.read()
                                    import re
                                    test_matches = re.findall(r'#{10,}\s+Running test:\s+(\S+)', log_content)
                                    available_tests.update(test_matches)
                                    log(f"Found {len(available_tests)} unique tests in log file")
                            except Exception as e:
                                log(f"Error reading log file {log_path}: {e}")
                
                csv_found = False
                for root, dirs, dir_files in os.walk(filepath):
                    for file in dir_files:
                        if file.endswith(".csv"):
                            csv_path = os.path.join(root, file)
                            log(f"Found CSV in directory: {csv_path}")
                            try:
                                with open(csv_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    update_test_stats(summary, filename, content, log, available_tests if available_tests else None)
                                    csv_found = True
                            except Exception as e:
                                log(f"Error reading CSV {csv_path}: {e}")
                
                if not csv_found:
                    log(f"No CSV files found in directory {filename}")

        except Exception as e:
            log(f"Error processing {filename}: {e}")
            print(f"Error processing {filename}: {e}")

    # Convert datetime objects to strings for JSON serialization
    if isinstance(summary["test_times"]["start"], datetime):
        summary["test_times"]["start"] = summary["test_times"]["start"].strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(summary["test_times"]["end"], datetime):
        summary["test_times"]["end"] = summary["test_times"]["end"].strftime("%Y-%m-%d %H:%M:%S")

    # Initialize notes field if not exists
    if 'notes' not in summary:
        summary['notes'] = {}
    
    if summary["tests"]["link"]["ev"]["total"] == 0 and summary["tests"]["link"]["ev_default"]["total"] > 0:
        summary["tests"]["link"]["ev"] = summary["tests"]["link"]["ev_default"]

    # Save to cache before returning
    cache_file = _get_cache_file_path(target_dir)
    _save_to_cache(cache_file, summary)
    
    return summary

def parse_test_times(summary, content, filename, category, level, log_func=None):
    """Parse TEST_STATUS to extract start and end times."""
    def log(msg):
        if log_func: log_func(msg)
    
    # First, extract timestamp from filename
    # Format: *_2026-01-28-AM10-50.tar.gz
    import re
    timestamp_match = re.search(r'_(\d{4}-\d{2}-\d{2}-[AP]M\d{2}-\d{2})', filename)
    if timestamp_match and category and level:
        timestamp = timestamp_match.group(1)
        summary["tests"][category][level]["timestamp"] = timestamp
        log(f"Extracted timestamp from filename: {timestamp}")
    
    start_time = None
    end_time = None
    
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("Sart Time:"):
            start_time = line.split(":", 1)[1].strip()
        elif line.startswith("End Time:"):
            end_time = line.split(":", 1)[1].strip()
    
    if start_time and end_time:
        try:
            # Parse dates: format is YYYY-MM-DD-AMPM-HH-MM
            start_dt = datetime.strptime(start_time, "%Y-%m-%d-%p%I-%M")
            end_dt = datetime.strptime(end_time, "%Y-%m-%d-%p%I-%M")
            duration = end_dt - start_dt
            
            # Calculate duration in hours and minutes
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            
            # Store individual test times
            if category and level:
                summary["tests"][category][level]["start_time"] = start_time
                summary["tests"][category][level]["end_time"] = end_time
                summary["tests"][category][level]["duration"] = duration_str
            
            # Update global earliest start and latest end
            if summary["test_times"]["start"] is None:
                summary["test_times"]["start"] = start_dt
            else:
                summary["test_times"]["start"] = min(summary["test_times"]["start"], start_dt)
            
            if summary["test_times"]["end"] is None:
                summary["test_times"]["end"] = end_dt
            else:
                summary["test_times"]["end"] = max(summary["test_times"]["end"], end_dt)
            
            # Calculate total duration
            total_duration = summary["test_times"]["end"] - summary["test_times"]["start"]
            total_hours = int(total_duration.total_seconds() // 3600)
            total_minutes = int((total_duration.total_seconds() % 3600) // 60)
            summary["test_times"]["duration"] = f"{total_hours}h {total_minutes}m" if total_hours > 0 else f"{total_minutes}m"
            
            log(f"Parsed times for {filename}: {start_time} -> {end_time}, Duration: {duration_str}")
        except Exception as e:
            log(f"Error parsing time format: {e}")

def parse_version_info(content):
    """Parse Version_Info.txt content."""
    info = {
        "FBOSS_COMMIT_URL": "",
        "FBOSS_COMMIT_DESC": "",
        "FBOSS_BINARY": "",
        "BCM_SAI_VERSION": "",
        "OCP_SAI_VERSION": "",
        "BCM_HSDK_VERSION": ""
    }
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
            
        if "FBOSS_COMMIT_URL" in line and ":" in line:
            info["FBOSS_COMMIT_URL"] = line.split(":", 1)[1].strip()
        elif "FBOSS_COMMIT_DESC" in line and ":" in line:
            info["FBOSS_COMMIT_DESC"] = line.split(":", 1)[1].strip()
        elif "FBOSS_BINARY" in line and ":" in line:
            info["FBOSS_BINARY"] = line.split(":", 1)[1].strip()
        elif "BCM SAI_VERSION" in line and ":" in line:
            info["BCM_SAI_VERSION"] = line.split(":", 1)[1].strip()
        elif "OCP SAI_VERSION" in line and ":" in line:
            info["OCP_SAI_VERSION"] = line.split(":", 1)[1].strip()
        elif "BCM HSDK_VERSION" in line and ":" in line:
            info["BCM_HSDK_VERSION"] = line.split(":", 1)[1].strip()
            
    return info
    
def parse_hw_info(content, log_func=None):
    """Parse HW_info.txt content."""
    def log(msg):
        if log_func: log_func(msg)

    info = {}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
            
        if "Product Name:" in line:
            val = line.split(":", 1)[1].strip()
            info["PRODUCT_NAME"] = val
            log(f"Found Product Name: {val}")
        elif "Production State:" in line:
            val = line.split(":", 1)[1].strip()
            info["PRODUCTION_STATE"] = val
            log(f"Found Production State: {val}")
        elif "ASIC:" in line:
            val = line.split(":", 1)[1].strip()
            info["ASIC"] = val
            log(f"Found ASIC: {val}")
        elif "PCB Manufacturer:" in line:
            val = line.split(":", 1)[1].strip()
            info["PCB_MANUFACTURER"] = val
            log(f"Found PCB Manufacturer: {val}")
        elif "Product Serial Number:" in line:
            val = line.split(":", 1)[1].strip()
            info["PRODUCT_SERIAL_NUMBER"] = val
            log(f"Found Serial Number: {val}")
            
    return info

def parse_fw_info(content, log_func=None):
    """Parse mp3n_sdk_ver_fw_ver.txt content."""
    def log(msg):
        if log_func: log_func(msg)

    info = {}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
            
        if "Image type:" in line:
            val = line.split(":", 1)[1].strip()
            info["FW_IMAGE_TYPE"] = val
            log(f"Found Image Type: {val}")
        elif "FW Version:" in line:
            val = line.split(":", 1)[1].strip()
            info["FW_VERSION"] = val
            log(f"Found FW Version: {val}")
        elif "FW Release Date:" in line:
            val = line.split(":", 1)[1].strip()
            info["FW_RELEASE_DATE"] = val
            log(f"Found FW Release Date: {val}")
        elif "Product Version:" in line:
            val = line.split(":", 1)[1].strip()
            info["PRODUCT_VERSION"] = val
            log(f"Found Product Version: {val}")
        elif "PSID:" in line:
            val = line.split(":", 1)[1].strip()
            info["FW_PSID"] = val
            log(f"Found PSID: {val}")
            
    return info

def update_test_stats(summary, filename, csv_content, log_func=None, available_tests=None):
    """Update summary stats based on CSV content and filename.
    
    Args:
        summary: Summary dict to update
        filename: Archive filename to determine category/level
        csv_content: CSV file content
        log_func: Logging function
        available_tests: Set of test names that actually exist in the log file (for validation)
    """
    def log(msg):
        if log_func: log_func(msg)

    # Determine test category from filename
    category = None
    level = None
    
    filename_upper = filename.upper()
    log(f"Categorizing filename: {filename_upper}")
    
    if filename_upper.startswith("AGENT_HW_T0"):
        category = "agent_hw"
        level = "t0"
    elif filename_upper.startswith("AGENT_HW_T1"):
        category = "agent_hw"
        level = "t1"
    elif filename_upper.startswith("AGENT_HW_T2"):
        category = "agent_hw"
        level = "t2"
    elif filename_upper.startswith("EXITEVT"):
        category = "link"
        # Extract topology from filename
        # Format: ExitEVT_{PLATFORM}_{VERSION}_{TOPOLOGY}_{DATE}.tar.gz
        filename_lower = filename.lower()
        topology = "default"
        
        # Check for topology patterns in the filename
        if "_optic_one_" in filename_lower or filename_lower.endswith("_optic_one.tar.gz"):
            topology = "optics_one"
        elif "_optic_two_" in filename_lower or filename_lower.endswith("_optic_two.tar.gz"):
            topology = "optics_two"
        elif "_optics_one_" in filename_lower or filename_lower.endswith("_optics_one.tar.gz"):
            topology = "optics_one"
        elif "_optics_two_" in filename_lower or filename_lower.endswith("_optics_two.tar.gz"):
            topology = "optics_two"
        elif "_copper_" in filename_lower or filename_lower.endswith("_copper.tar.gz"):
            topology = "copper"
        elif "_400g_" in filename_lower or filename_lower.endswith("_400g.tar.gz"):
            topology = "400g"
        elif "_default_" in filename_lower or filename_lower.endswith("_default.tar.gz"):
            topology = "default"
        
        level = f"ev_{topology}"
        log(f"EVT test detected with topology: {topology}")
    elif filename_upper.startswith("LINK_T0"):
        category = "link"
        level = "t0"
        # Extract topology from LINK_T0 filename
        topology = "default"
        filename_lower = filename.lower()
        if "_optic_one" in filename_lower or "optic_one_" in filename_lower:
            topology = "optic_one"
        elif "_optic_two" in filename_lower or "optic_two_" in filename_lower:
            topology = "optic_two"
        elif "_copper" in filename_lower or "copper_" in filename_lower:
            topology = "copper"
        elif "_400g" in filename_lower or "400g_" in filename_lower:
            topology = "400g"
        # Store topology info
        if summary["tests"]["link"]["t0"]["topology"] is None:
            summary["tests"]["link"]["t0"]["topology"] = topology
            log(f"LINK_T0 test detected with topology: {topology}")
    elif filename_upper.startswith("LINK_T1"):
        category = "link"
        level = "t1"
        # Extract topology from LINK_T1 filename
        topology = "default"
        filename_lower = filename.lower()
        if "_optic_one" in filename_lower or "optic_one_" in filename_lower:
            topology = "optic_one"
        elif "_optic_two" in filename_lower or "optic_two_" in filename_lower:
            topology = "optic_two"
        elif "_optics_one" in filename_lower or "optics_one_" in filename_lower:
            topology = "optics_one"
        elif "_optics_two" in filename_lower or "optics_two_" in filename_lower:
            topology = "optics_two"
        elif "_copper" in filename_lower or "copper_" in filename_lower:
            topology = "copper"
        elif "_400g" in filename_lower or "400g_" in filename_lower:
            topology = "400g"
        # Store topology info
        if summary["tests"]["link"]["t1"]["topology"] is None:
            summary["tests"]["link"]["t1"]["topology"] = topology
            log(f"LINK_T1 test detected with topology: {topology}")
    elif filename_upper.startswith("LINK_T2"):
        category = "link"
        level = "t2"
        # Extract topology from LINK_T2 filename
        topology = "default"
        filename_lower = filename.lower()
        if "_optic_one" in filename_lower or "optic_one_" in filename_lower:
            topology = "optic_one"
        elif "_optic_two" in filename_lower or "optic_two_" in filename_lower:
            topology = "optic_two"
        elif "_optics_one" in filename_lower or "optics_one_" in filename_lower:
            topology = "optics_one"
        elif "_optics_two" in filename_lower or "optics_two_" in filename_lower:
            topology = "optics_two"
        elif "_copper" in filename_lower or "copper_" in filename_lower:
            topology = "copper"
        elif "_400g" in filename_lower or "400g_" in filename_lower:
            topology = "400g"
        # Store topology info
        if summary["tests"]["link"]["t2"]["topology"] is None:
            summary["tests"]["link"]["t2"]["topology"] = topology
            log(f"LINK_T2 test detected with topology: {topology}")
    elif filename_upper.startswith("SAI_T0"):
        category = "sai"
        level = "t0"
    elif filename_upper.startswith("SAI_T1"):
        category = "sai"
        level = "t1"
    elif filename_upper.startswith("SAI_T2"):
        category = "sai"
        level = "t2"
    elif filename_upper.startswith("LINKTEST_LOG_"):
        category = "link_test"
        level = "default"

    if not category or not level:
        log(f"Skipping unknown category/level for {filename}")
        return

    log(f"Matched Category: {category}, Level: {level}")

    # Parse CSV to count Pass/Fail
    reader = csv.reader(io.StringIO(csv_content))
    passed = 0
    failed = 0
    skipped = 0
    
    rows = list(reader)
    if not rows:
        log("CSV is empty")
        return
    
    # Check if first row is a header (contains "Test Name" or "Result")
    header_row = 0
    if len(rows) > 0 and any(h.strip().lower() in ['test name', 'result', 'test case'] for h in rows[0]):
        header_row = 1
        log(f"Detected header row: {rows[0]}")
    
    # Find the Result column index
    result_col_idx = -1
    if header_row == 1:
        for idx, col in enumerate(rows[0]):
            if col.strip().lower() == 'result':
                result_col_idx = idx
                break
    
    # If no header or Result column not found, assume column 1 (second column) is the result
    if result_col_idx == -1:
        result_col_idx = 1
        log(f"No Result column found in header, assuming column index 1")
    else:
        log(f"Result column found at index {result_col_idx}")
    
    # Parse each data row
    for i, row in enumerate(rows[header_row:], start=header_row):
        if len(row) <= result_col_idx:
            log(f"Row {i} has insufficient columns: {row}")
            continue
        
        result = row[result_col_idx].strip().upper()
        test_name = row[0].strip() if len(row) > 0 else f"Test_{i}"
        
        # Validate test exists in log file if available_tests is provided  
        if available_tests is not None and len(available_tests) > 0:
            # Check if test name (with or without warm_boot./cold_boot. prefix) exists in log
            test_name_variants = [test_name, test_name.replace("warm_boot.", ""), test_name.replace("cold_boot.", "")]
            if not any(variant in available_tests for variant in test_name_variants):
                log(f"Skipping test '{test_name}' - not found in log file")
                continue
        
        # Count based on result value
        if result in ['OK', 'PASS', 'PASSED']:
            passed += 1
            summary["tests"][category][level]["items"].append({
                "name": test_name,
                "result": "PASS"
            })
        elif result in ['FAIL', 'FAILED', 'ERROR']:
            failed += 1
            summary["tests"][category][level]["items"].append({
                "name": test_name,
                "result": "FAIL"
            })
        elif result in ['SKIPPED', 'SKIP', 'IGNORED']:
            skipped += 1
            # Don't add skipped items to the list
        else:
            # Unknown result, log it
            log(f"Row {i}: Unknown result '{result}' in: {row}")

    log(f"Parsed CSV stats: passed={passed}, failed={failed}, skipped={skipped}, total={passed+failed}")

    summary["tests"][category][level]["passed"] += passed
    summary["tests"][category][level]["failed"] += failed
    summary["tests"][category][level]["total"] += (passed + failed)
    
    # Update global stats
    summary["all_tests"]["passed"] += passed
    summary["all_tests"]["failed"] += failed
    summary["all_tests"]["total"] += (passed + failed)

def get_7day_trend(platform, end_date_str=None, category=None, level=None, range_type='week'):
    """Get test trend data for a platform or specific test case.
    
    Args:
        platform: Platform name
        end_date_str: End date in YYYY-MM-DD format
        category: Test category (e.g., 'sai', 'agent_hw', 'link')
        level: Test level (e.g., 't0', 't1', 'ev_default')
        range_type: Time range - 'week' (7 days), 'month' (30 days), 'year' (365 days)
    """
    from datetime import datetime, timedelta
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError:
            end_date = datetime.now()  # Invalid date format, use current date
    else:
        end_date = datetime.now()
    
    # Determine number of days based on range_type
    if range_type == 'week':
        days = 7
    elif range_type == 'month':
        days = 30
    elif range_type == 'year':
        days = 365
    else:
        days = 7  # default to week
    
    trend_data = []
    
    # Get data for the specified range
    for i in range(days - 1, -1, -1):
        date = end_date - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        summary = get_dashboard_summary(platform, date_str)
        
        if summary:
            if category and level:
                # Get specific test case data
                test_data = summary["tests"].get(category, {}).get(level, {})
                trend_data.append({
                    "date": date_str,
                    "passed": test_data.get("passed", 0),
                    "failed": test_data.get("failed", 0),
                    "total": test_data.get("total", 0),
                    "items": test_data.get("items", []),
                    "version_info": summary.get("version_info", {}),
                    "duration": test_data.get("duration", None)
                })
            else:
                # Get all tests data
                trend_data.append({
                    "date": date_str,
                    "all_tests": {
                        "passed": summary["all_tests"]["passed"],
                        "failed": summary["all_tests"]["failed"],
                        "total": summary["all_tests"]["total"]
                    },
                    "version_info": summary.get("version_info", {}),
                    "tests": summary["tests"]
                })
        else:
            # No data for this date
            if category and level:
                trend_data.append({
                    "date": date_str,
                    "passed": 0,
                    "failed": 0,
                    "total": 0,
                    "items": [],
                    "version_info": {},
                    "duration": None
                })
            else:
                trend_data.append({
                    "date": date_str,
                    "all_tests": {"passed": 0, "failed": 0, "total": 0},
                    "version_info": {},
                    "tests": {}
                })
    
    return trend_data
def pregenerate_all_caches():
    """Pre-generate cache files for all platforms and dates to improve dashboard performance."""
    print("[CACHE PREGENERATION] Starting cache pre-generation for all platforms...")
    
    if not os.path.exists(TEST_REPORT_BASE):
        print(f"[CACHE PREGENERATION] Test report base directory not found: {TEST_REPORT_BASE}")
        return
    
    # Get all platform directories
    platforms = []
    for item in os.listdir(TEST_REPORT_BASE):
        item_path = os.path.join(TEST_REPORT_BASE, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            platforms.append(item)
    
    print(f"[CACHE PREGENERATION] Found {len(platforms)} platforms: {platforms}")
    
    total_generated = 0
    total_cached = 0
    
    for platform in platforms:
        dates = list_dashboard_dates(platform)
        print(f"[CACHE PREGENERATION] Platform {platform}: {len(dates)} dates")
        
        for date_str in dates:
            target_dir = os.path.join(TEST_REPORT_BASE, platform, f"all_test_{date_str}")
            cache_file = _get_cache_file_path(target_dir)
            
            # Check if cache already exists and is valid
            if _is_cache_valid(target_dir, cache_file):
                print(f"[CACHE PREGENERATION] {platform}/{date_str}: Cache already valid, skipping")
                total_cached += 1
            else:
                print(f"[CACHE PREGENERATION] {platform}/{date_str}: Generating cache...")
                try:
                    get_dashboard_summary(platform, date_str)
                    total_generated += 1
                    print(f"[CACHE PREGENERATION] {platform}/{date_str}: ✓ Cache generated")
                except Exception as e:
                    print(f"[CACHE PREGENERATION] {platform}/{date_str}: ✗ Error: {e}")
    
    print(f"[CACHE PREGENERATION] Complete! Generated: {total_generated}, Already cached: {total_cached}, Total: {total_generated + total_cached}")
    return total_generated, total_cached

def get_diff_summary(platform, date_curr_str, date_prev_str):
    """Compare test results between two dates and return diff.
    
    Args:
        platform: Platform name
        date_curr_str: Current date (YYYY-MM-DD)
        date_prev_str: Previous date (YYYY-MM-DD)
        
    Returns:
        dict: Diff summary containing 'new_failures' and 'fixed' lists.
    """
    summary_curr = get_dashboard_summary(platform, date_curr_str)
    summary_prev = get_dashboard_summary(platform, date_prev_str)
    
    diff = {
        "new_failures": [],
        "fixed": [],
        "added_tests": [],
        "removed_tests": [],
        "stats": {
            "new_failures_count": 0,
            "fixed_count": 0,
            "added_count": 0,
            "removed_count": 0
        }
    }
    
    if not summary_curr or not summary_prev:
        return diff
        
    # Helper to flatten test items
    def get_all_items(summary):
        items = {}
        if not summary.get("tests"):
            return items
            
        for category, cat_data in summary["tests"].items():
            for level, level_data in cat_data.items():
                if "items" in level_data:
                    for item in level_data["items"]:
                        # Use Name+Category+Level as unique key
                        key = f"{category}|{level}|{item['name']}"
                        items[key] = {
                            "name": item["name"],
                            "result": item["result"],
                            "category": category,
                            "level": level,
                            "note": get_report_note(f"note_{summary['dut_name']}_{summary['date']}_{category}_{level}_{item['name']}") if 'dut_name' in summary else ""
                            # Note: dut_name might not be in summary if it's a platform summary.
                            # dashboard.py summary has dut_name? No, get_dashboard_summary returns a summary structure. 
                            # Let's check get_dashboard_summary output structure again.
                            # It returns summary dict. It doesn't seem to have dut_name at top level in platform summary?
                            # Actually get_dashboard_summary scans a directory. 
                            # If it's lab_monitor context, we might need dut_name. 
                            # But dashboard.py is generic. 
                            # Let's just use item name for now.
                        }
        return items

    items_curr = get_all_items(summary_curr)
    items_prev = get_all_items(summary_prev)
    
    # Check for New Failures (Failed in Curr, but Passed or Missing in Prev)
    for key, curr_item in items_curr.items():
        if curr_item["result"] == "FAIL":
            prev_item = items_prev.get(key)
            if not prev_item or prev_item["result"] == "PASS":
                diff["new_failures"].append({
                    "name": curr_item["name"],
                    "category": curr_item["category"],
                    "level": curr_item["level"],
                    "curr_result": "FAIL",
                    "prev_result": prev_item["result"] if prev_item else "N/A"
                })

    # Check for Fixed (Passed in Curr, but Failed in Prev)
    for key, curr_item in items_curr.items():
        if curr_item["result"] == "PASS":
             prev_item = items_prev.get(key)
             if prev_item and prev_item["result"] == "FAIL":
                 diff["fixed"].append({
                    "name": curr_item["name"],
                    "category": curr_item["category"],
                    "level": curr_item["level"],
                    "curr_result": "PASS",
                    "prev_result": "FAIL"
                 })

    # Check for Added Tests (In Curr, Not in Prev)
    for key, curr_item in items_curr.items():
        if key not in items_prev:
            diff["added_tests"].append({
                "name": curr_item["name"],
                "category": curr_item["category"],
                "level": curr_item["level"],
                "curr_result": curr_item["result"],
                "prev_result": "N/A"
            })

    # Check for Removed Tests (In Prev, Not in Curr)
    for key, prev_item in items_prev.items():
        if key not in items_curr:
            diff["removed_tests"].append({
                "name": prev_item["name"],
                "category": prev_item["category"],
                "level": prev_item["level"],
                "curr_result": "N/A",
                "prev_result": prev_item["result"]
            })

    diff["stats"]["new_failures_count"] = len(diff["new_failures"])
    diff["stats"]["fixed_count"] = len(diff["fixed"])
    diff["stats"]["added_count"] = len(diff["added_tests"])
    diff["stats"]["removed_count"] = len(diff["removed_tests"])
    
    return diff
