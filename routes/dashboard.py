"""
Dashboard Routes Blueprint
Handles all dashboard-related endpoints for test reports and visualization.
"""

import os
import json
import tarfile
import subprocess
import shutil
import tempfile
from io import BytesIO
from flask import Blueprint, jsonify, request, render_template, send_file, make_response, send_from_directory, current_app
from werkzeug.exceptions import NotFound
import dashboard as dashboard_module
from config.logging_config import get_logger
from utils.validators import validate_platform, validate_date, is_safe_filename, sanitize_path

logger = get_logger(__name__)


# Helper functions copied from app.py
def safe_mkdtemp(prefix='tmp_'):
    """Create a temporary directory safely."""
    return tempfile.mkdtemp(prefix=prefix)


def find_test_archive(target_dir, category, level):
    """Find the appropriate tar archive based on category and level."""
    # Map category/level to archive patterns
    patterns = {
        ('link', 'ev_default'): ['ExitEVT_', 'default'],
        ('link', 'ev_400g'): ['ExitEVT_', '400g'],
        ('link', 'ev_optics_one'): ['ExitEVT_', 'optics_one'],
        ('link', 'ev_optics_two'): ['ExitEVT_', 'optics_two'],
        ('link', 'ev_copper'): ['ExitEVT_', 'copper'],
        ('link_test', 'default'): ['LINKTEST_LOG_'],
        ('sai', 't0'): ['SAI_t0_'],
        ('sai', 't1'): ['SAI_t1_'],
        ('sai', 't2'): ['SAI_t2_'],
        ('agent_hw', 't0'): ['AGENT_HW_t0_'],
        ('agent_hw', 't1'): ['AGENT_HW_t1_'],
        ('agent_hw', 't2'): ['AGENT_HW_t2_'],
        ('link', 't0'): ['LINK_T0_'],
        ('link', 't1'): ['LINK_T1_'],
        ('link', 't2'): ['LINK_T2_'],
    }
    
    files = os.listdir(target_dir)
    pattern_key = (category, level)
    
    if pattern_key in patterns:
        pattern_parts = patterns[pattern_key]
        for filename in files:
            if filename.upper().startswith(pattern_parts[0].upper()) and filename.endswith('.tar.gz'):
                if len(pattern_parts) > 1:
                    topology = pattern_parts[1]
                    if topology.lower() in filename.lower():
                        return os.path.join(target_dir, filename)
                    elif topology == 'default' and not any(t in filename.lower() for t in ['optics', 'copper', '400g']):
                        return os.path.join(target_dir, filename)
                else:
                    return os.path.join(target_dir, filename)
    
    return None


def extract_test_log_from_archive(archive_file, test_name):
    """Extract specific test log content from tar.gz archive.
    Handles nested tar.gz archives - first extracts outer archive, 
    then finds and extracts nested .log.tar.gz file, then uses split_and_report.py logic."""
    import tempfile
    import shutil
    
    START_MARKER = "########## Running test:"
    END_MARKER = "Running all tests took"
    
    temp_dir = None
    nested_dir = None
    
    try:
        # Create temporary directory to extract outer archive
        temp_dir = tempfile.mkdtemp(prefix='test_log_outer_')
        
        # Extract outer tar archive
        print(f"[LOG_DETAIL] Extracting outer archive: {archive_file}")
        logger.info(f"[LOG_DETAIL] Extracting outer archive: {archive_file}")
        with tarfile.open(archive_file, 'r:gz') as tar:
            tar.extractall(temp_dir)
        
        # Find nested .tar.gz or .log.tar.gz files inside
        nested_archives = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.log.tar.gz') or file.endswith('.tar.gz') or file.endswith('.tgz'):
                    nested_path = os.path.join(root, file)
                    nested_size = os.path.getsize(nested_path)
                    nested_archives.append((nested_path, nested_size, file))
        
        # Sort by size to find the main nested archive
        nested_archives.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"[LOG_DETAIL] Found {len(nested_archives)} nested archives")
        for path, size, name in nested_archives[:3]:
            logger.info(f"[LOG_DETAIL]   - {name}: {size:,} bytes")
        
        # If there's a nested archive, extract it
        main_log_content = None
        
        if nested_archives:
            nested_archive_path = nested_archives[0][0]
            logger.info(f"[LOG_DETAIL] Extracting nested archive: {os.path.basename(nested_archive_path)}")
            
            nested_dir = tempfile.mkdtemp(prefix='test_log_nested_')
            with tarfile.open(nested_archive_path, 'r:gz') as tar:
                tar.extractall(nested_dir)
            
            # Find log files in nested archive
            log_files = []
            for root, dirs, files in os.walk(nested_dir):
                for file in files:
                    if file.endswith('.log') or file.endswith('.txt'):
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        log_files.append((file_path, file_size, file))
            
            if log_files:
                # Sort by size (largest first) to get the main log file
                log_files.sort(key=lambda x: x[1], reverse=True)
                main_log_path = log_files[0][0]
                
                logger.info(f"[LOG_DETAIL] Found main log in nested archive: {log_files[0][2]} ({log_files[0][1]:,} bytes)")
                
                # Read the entire log content
                with open(main_log_path, 'r', encoding='utf-8', errors='replace') as f:
                    main_log_content = f.read()
        else:
            # No nested archive, look for log files directly in outer archive
            log_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.log') or file.endswith('.txt'):
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        log_files.append((file_path, file_size))
            
            if not log_files:
                logger.info(f"[LOG_DETAIL] No log files found in archive")
                return None
            
            # Sort by size (largest first) to get the main log file
            log_files.sort(key=lambda x: x[1], reverse=True)
            main_log_path = log_files[0][0]
            
            logger.info(f"[LOG_DETAIL] Found main log file: {os.path.basename(main_log_path)} ({log_files[0][1]:,} bytes)")
            
            # Read the entire log content
            with open(main_log_path, 'r', encoding='utf-8', errors='replace') as f:
                main_log_content = f.read()
        
        if not main_log_content:
            logger.info(f"[LOG_DETAIL] No log content found")
            return None
        
        logger.info(f"[LOG_DETAIL] Total log content: {len(main_log_content):,} chars")
        
        # Use split_and_report.py logic to find the specific test section
        lines = main_log_content.split('\n')
        capturing = False
        test_lines = []
        
        # Strip common prefixes from test name for matching
        test_name_variants = [test_name]
        
        # Try without common prefixes
        for prefix in ['warm_boot.', 'cold_boot.', 'test.', 't0.', 't1.']:
            if test_name.startswith(prefix):
                test_name_variants.append(test_name[len(prefix):])
        
        # Also try with sanitized version
        test_name_sanitized = test_name.replace("/", "_").replace("\\", "_")
        test_name_variants.append(test_name_sanitized)
        
        logger.info(f"[LOG_DETAIL] Search variants: {test_name_variants[:3]}")
        
        for line in lines:
            # Check for end marker
            if END_MARKER in line:
                if capturing:
                    break
            
            # Check for start marker
            if START_MARKER in line:
                parts = line.split(START_MARKER)
                if len(parts) > 1:
                    current_test = parts[1].strip()
                    # Sanitize test name for comparison
                    current_test_sanitized = current_test.replace("/", "_").replace("\\", "_")
                    
                    # Check if current test matches any of our variants
                    matched = False
                    for variant in test_name_variants:
                        variant_sanitized = variant.replace("/", "_").replace("\\", "_")
                        if current_test == variant or current_test_sanitized == variant_sanitized:
                            matched = True
                            break
                    
                    if matched:
                        logger.info(f"[LOG_DETAIL] ✓ Matched target test: {test_name} (found as: {current_test})")
                        capturing = True
                        test_lines = [line]
                    else:
                        # If we were capturing and hit a new test, stop
                        if capturing:
                            break
                        capturing = False
                continue
            
            # Capture lines if we're in the target test
            if capturing:
                test_lines.append(line)
        
        result = '\n'.join(test_lines) if test_lines else None
        
        if result:
            logger.info(f"[LOG_DETAIL] Successfully extracted {len(test_lines)} lines for test: {test_name}")
        else:
            logger.info(f"[LOG_DETAIL] Test not found: {test_name}")
            # Show available tests for debugging
            test_names = []
            for line in lines:
                if START_MARKER in line:
                    parts = line.split(START_MARKER)
                    if len(parts) > 1:
                        test_names.append(parts[1].strip())
            if test_names:
                logger.info(f"[LOG_DETAIL] Available tests in log: {test_names[:10]}")
        
        return result
            
    except Exception as e:
        logger.error(f"[LOG_DETAIL] Error extracting test log: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up temporary directories
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        if nested_dir and os.path.exists(nested_dir):
            try:
                shutil.rmtree(nested_dir)
            except:
                pass


def generate_test_excel_report(test_name, log_content):
    """Generate Excel report from test log content."""
    # This is a simplified placeholder - actual implementation would parse log and create Excel
    # For now, create a text file to demonstrate the concept
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
    temp_file.write(log_content)
    temp_file.close()
    return temp_file.name

# Create blueprint with URL prefix
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


# Helper function to get cached platform (from main app)
def get_cached_platform():
    """Read cached platform from .platform_cache file."""
    cache_file = '.platform_cache'
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return f.read().strip()
        except Exception as e:
            logger.warning(f"Failed to read platform cache: {e}")
    return None


@dashboard_bp.route('/dates/<platform>')
def api_dashboard_dates(platform):
    """Get list of available test dates for a platform."""
    dates = dashboard_module.list_dashboard_dates(platform)
    return jsonify(dates)


@dashboard_bp.route('/current_platform')
def api_dashboard_current_platform():
    """Get the current platform from cache file or detect it."""
    
    # First, try to read from cache file
    cached_platform = get_cached_platform()
    if cached_platform:
        logger.info(f"[API] Using cached platform: {cached_platform}")
        return jsonify({'platform': cached_platform, 'has_data': True, 'source': 'cache_file'})
    
    # If cache doesn't exist, try to infer from working directory
    cwd = os.getcwd()
    inferred_platform = None
    
    if 'MP3N' in cwd or 'MINIPACK3N' in cwd.upper():
        inferred_platform = 'MINIPACK3N'
    elif 'MP3BA' in cwd or 'MINIPACK3BA' in cwd.upper() or 'MONTBLANC' in cwd.upper():
        inferred_platform = 'MINIPACK3BA'
    elif 'WEDGE800BA' in cwd.upper() or 'W800BA' in cwd:
        inferred_platform = 'WEDGE800BACT'
    elif 'WEDGE800CA' in cwd.upper() or 'W800CA' in cwd:
        inferred_platform = 'WEDGE800CACT'
    
    if inferred_platform:
        logger.info(f"[API] Inferred platform from working directory: {inferred_platform}")
        return jsonify({'platform': inferred_platform, 'has_data': True, 'source': 'working_directory'})
    
    # If can't infer from path, find the platform with the most recent test data
    platforms = ['MINIPACK3N', 'MINIPACK3BA', 'WEDGE800BACT', 'WEDGE800CACT']
    latest_platform = None
    latest_date = None
    
    for platform in platforms:
        dates = dashboard_module.list_dashboard_dates(platform)
        if dates:
            # dates are sorted in reverse order (most recent first)
            if latest_date is None or dates[0] > latest_date:
                latest_date = dates[0]
                latest_platform = platform
    
    # If no platform has data, return MINIPACK3N as it's the default in NUI.html
    if latest_platform is None:
        latest_platform = 'MINIPACK3N'
    
    logger.info(f"[API] Selected platform from test data: {latest_platform}")
    return jsonify({'platform': latest_platform, 'has_data': latest_date is not None, 'source': 'test_data'})


@dashboard_bp.route('/summary/<platform>/<date>')
def api_dashboard_summary(platform, date):
    """Get summarized test results for a specific platform and date."""
    summary = dashboard_module.get_dashboard_summary(platform, date)
    if summary:
        return jsonify(summary)
    return jsonify({'error': 'Report not found'}), 404


@dashboard_bp.route('/trend/<platform>')
@dashboard_bp.route('/trend/<platform>/<end_date>')
@dashboard_bp.route('/trend/<platform>/<end_date>/<category>/<level>')
def api_dashboard_trend(platform, end_date=None, category=None, level=None):
    """Get test trend data for a platform or specific test case."""
    range_type = request.args.get('range', 'week')  # week, month, or year
    trend_data = dashboard_module.get_7day_trend(platform, end_date, category, level, range_type)
    return jsonify(trend_data)


@dashboard_bp.route('/diff/<platform>/<date_curr>/<date_prev>')
def api_dashboard_diff(platform, date_curr, date_prev):
    """Get diff of test results between two dates."""
    diff = dashboard_module.get_diff_summary(platform, date_curr, date_prev)
    return jsonify(diff)


@dashboard_bp.route('/download_log/<platform>/<date>/<category>/<level>')
def api_dashboard_download_log(platform, date, category, level):
    """Download log file for a specific test category and level."""
    target_dir = os.path.join(dashboard_module.TEST_REPORT_BASE, platform, f"all_test_{date}")
    
    if not os.path.isdir(target_dir):
        return jsonify({'error': 'Test report directory not found'}), 404
    
    # Special case: "all/all" means download all logs as a combined archive
    if category == 'all' and level == 'all':
        # Create a tar.gz with all test archives
        memory_file = BytesIO()
        
        try:
            with tarfile.open(fileobj=memory_file, mode='w:gz') as tar:
                # Add all tar.gz files in the directory
                for filename in os.listdir(target_dir):
                    if filename.endswith('.tar.gz') or filename.endswith('.tgz'):
                        file_path = os.path.join(target_dir, filename)
                        tar.add(file_path, arcname=filename)
            
            memory_file.seek(0)
            
            return send_file(
                memory_file,
                mimetype='application/gzip',
                as_attachment=True,
                download_name=f'All_Test_Logs_{platform}_{date}.tar.gz'
            )
        except Exception as e:
            logger.error(f"Error creating combined archive: {e}")
            return jsonify({'error': 'Failed to create combined archive'}), 500
    
    # Use find_test_archive to locate the correct archive
    archive_file = find_test_archive(target_dir, category, level)
    
    if archive_file and os.path.exists(archive_file):
        return send_from_directory(target_dir, os.path.basename(archive_file), as_attachment=True)
    
    return jsonify({'error': f'Log file not found for {category}/{level}'}), 404


@dashboard_bp.route('/download_all/<platform>/<date>')
def api_dashboard_download_all(platform, date):
    """Download entire test report directory as tar.gz."""
    target_dir = os.path.join(dashboard_module.TEST_REPORT_BASE, platform, f"all_test_{date}")
    
    if not os.path.isdir(target_dir):
        return jsonify({'error': 'Test report directory not found'}), 404
    
    # Create tar.gz in memory
    memory_file = BytesIO()
    
    with tarfile.open(fileobj=memory_file, mode='w:gz') as tar:
        # Add all files in the directory
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, target_dir)
                tar.add(file_path, arcname=arcname)
    
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/gzip',
        as_attachment=True,
        download_name=f'all_test_{platform}_{date}.tar.gz'
    )


@dashboard_bp.route('/download_organized/<platform>/<date>')
def api_dashboard_download_organized(platform, date):
    """Generate organized test report using organize_test_reports.py and download as tar.gz."""
    # Validate inputs
    if not validate_platform(platform):
        logger.warning(f"[API] Invalid platform in download request: {platform}")
        return jsonify({'error': 'Invalid platform'}), 400
    
    if not validate_date(date):
        logger.warning(f"[API] Invalid date in download request: {date}")
        return jsonify({'error': 'Invalid date format'}), 400
    
    target_dir = os.path.join(dashboard_module.TEST_REPORT_BASE, platform, f"all_test_{date}")
    
    if not os.path.isdir(target_dir):
        return jsonify({'error': 'Test report directory not found'}), 404
    
    try:
        # Create a temporary directory for organized output
        temp_output_dir = safe_mkdtemp(prefix='organized_report_')
        
        try:
            # Run organize_test_reports.py - it will create the directory structure
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'organize_test_reports.py')
            
            logger.info(f'[ORGANIZE] Source: {target_dir}')
            logger.info(f'[ORGANIZE] Output: {temp_output_dir}')
            
            # Check if source directory has .tar.gz files
            tar_gz_files = [f for f in os.listdir(target_dir) if f.endswith('.tar.gz')]
            logger.info(f'[ORGANIZE] Found {len(tar_gz_files)} .tar.gz files in source')
            if tar_gz_files:
                logger.info(f'[ORGANIZE] Files: {tar_gz_files[:5]}')  # Show first 5
            
            result = subprocess.run(
                ['python3', script_path, target_dir, temp_output_dir],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            logger.info(f'[ORGANIZE] Script stdout:\n{result.stdout}')
            if result.stderr:
                logger.warning(f'[ORGANIZE] Script stderr:\n{result.stderr}')
            
            if result.returncode != 0:
                # Check if error message indicates files are being written
                error_msg = result.stderr + result.stdout
                if 'being written' in error_msg or 'modified recently' in error_msg:
                    return jsonify({
                        'error': 'Some test archives are still being created. Please wait until tests complete, then try again.',
                        'details': result.stderr,
                        'is_test_running': True
                    }), 409  # 409 Conflict
                else:
                    return jsonify({
                        'error': 'Failed to organize reports',
                        'details': result.stderr,
                        'stdout': result.stdout
                    }), 500
            
            # Verify files were created - use list to force evaluation
            all_files = []
            for root, dirs, files in os.walk(temp_output_dir):
                for f in files:
                    all_files.append(os.path.join(root, f))
            
            file_count = len(all_files)
            logger.info(f'[ORGANIZE] Generated {file_count} files in output')
            if file_count > 0:
                logger.info(f'[ORGANIZE] Sample files: {all_files[:5]}')
            
            if file_count == 0:
                # Debug: check if directory exists and what's in it
                logger.warning(f'[ORGANIZE] Checking temp_output_dir: {temp_output_dir}')
                logger.warning(f'[ORGANIZE] Directory exists: {os.path.exists(temp_output_dir)}')
                if os.path.exists(temp_output_dir):
                    try:
                        all_items = os.listdir(temp_output_dir)
                        logger.warning(f'[ORGANIZE] Items in directory: {all_items}')
                    except Exception as e:
                        logger.error(f'[ORGANIZE] Error listing directory: {e}')
                
                # Get list of source files for debugging
                source_files = os.listdir(target_dir) if os.path.isdir(target_dir) else []
                return jsonify({
                    'error': 'No files were generated in organized report',
                    'source_files': source_files[:10],  # First 10 files
                    'source_dir': target_dir,
                    'script_output': result.stdout
                }), 500
            
            # Create tar.gz in memory
            memory_file = BytesIO()
            
            with tarfile.open(fileobj=memory_file, mode='w:gz') as tar:
                # Add all files in the temp directory (with organized structure)
                for root, dirs, files in os.walk(temp_output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_output_dir)
                        tar.add(file_path, arcname=arcname)
            
            memory_file.seek(0)
            
            return send_file(
                memory_file,
                mimetype='application/gzip',
                as_attachment=True,
                download_name=f'Organized_Report_{platform}_{date}.tar.gz'
            )
        
        finally:
            # Clean up temp directory
            if os.path.exists(temp_output_dir):
                shutil.rmtree(temp_output_dir, ignore_errors=True)
    
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Report organization timed out'}), 500
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in download_organized: {error_details}")
        return jsonify({
            'error': f'Failed to generate organized report: {str(e)}',
            'details': error_details
        }), 500


@dashboard_bp.route('/test_log_detail/<platform>/<date>/<category>/<level>/<path:test_name>')
def api_dashboard_test_log_detail(platform, date, category, level, test_name):
    """Generate detailed Excel report for a specific test using split_and_report.py logic."""
    print(f"[LOG_DETAIL] Request: platform={platform}, date={date}, category={category}, level={level}, test={test_name}")
    logger.info(f"[LOG_DETAIL] Request: platform={platform}, date={date}, category={category}, level={level}, test={test_name}")
    
    # Check if full content mode or preview mode is requested
    full_mode = request.args.get('full') == 'true'
    preview_mode = request.args.get('preview') == 'true'
    
    target_dir = os.path.join(dashboard_module.TEST_REPORT_BASE, platform, f"all_test_{date}")
    
    if not os.path.isdir(target_dir):
        logger.info(f"[LOG_DETAIL] Directory not found: {target_dir}")
        return jsonify({'error': 'Test report directory not found'}), 404
    
    try:
        # Find the appropriate tar archive based on category and level
        archive_file = find_test_archive(target_dir, category, level)
        if not archive_file:
            logger.info(f"[LOG_DETAIL] Archive not found for category={category}, level={level}")
            return jsonify({'error': f'Test archive not found for {category}/{level}'}), 404
        
        logger.info(f"[LOG_DETAIL] Found archive: {archive_file}")
        
        # Extract the specific test log from the archive
        test_log_content = extract_test_log_from_archive(archive_file, test_name)
        
        # If not found, try other archives (test might be miscategorized in dashboard)
        if not test_log_content:
            logger.info(f"[LOG_DETAIL] Test not found in {category}/{level}, trying other archives...")
            # Try common alternative categories
            alternatives = []
            if category == 'sai':
                alternatives = [('link', level), ('agent_hw', level)]
            elif category == 'link':
                alternatives = [('sai', level), ('agent_hw', level)]
            elif category == 'agent_hw':
                alternatives = [('sai', level), ('link', level)]
            
            for alt_cat, alt_level in alternatives:
                alt_archive = find_test_archive(target_dir, alt_cat, alt_level)
                if alt_archive:
                    logger.info(f"[LOG_DETAIL] Trying alternative archive: {alt_cat}/{alt_level}")
                    test_log_content = extract_test_log_from_archive(alt_archive, test_name)
                    if test_log_content:
                        logger.info(f"[LOG_DETAIL] Found test in {alt_cat}/{alt_level} instead!")
                        break
        
        if not test_log_content:
            logger.info(f"[LOG_DETAIL] Test log content not found for: {test_name}")
            return jsonify({'error': f'Test log not found: {test_name}'}), 404
        
        logger.info(f"[LOG_DETAIL] Extracted log content ({len(test_log_content)} chars)")
        
        # Determine test status based on actual test result markers
        status = "UNKNOWN"
        if ("[ FAILED ]" in test_log_content or 
            "[  FAILED  ]" in test_log_content or 
            "FAILED TEST" in test_log_content or
            "Test FAILED" in test_log_content or
            "TESTS FAILED" in test_log_content):
            status = "FAIL"
        elif ("[ PASSED ]" in test_log_content or
              "[  PASSED  ]" in test_log_content or
              "Test PASSED" in test_log_content or 
              "ALL TESTS PASSED" in test_log_content):
            status = "PASS"
        
        # If full mode, return JSON with complete log content (no Excel download)
        if full_mode:
            logger.info(f"[LOG_DETAIL] Returning full log content ({len(test_log_content)} chars)")
            return jsonify({
                'status': status,
                'log_content': test_log_content,
                'log_size': len(test_log_content)
            })
        
        # If preview mode, return JSON with log content
        if preview_mode:
            # Get preview (first 5000 chars)
            log_preview = test_log_content[:5000]
            if len(test_log_content) > 5000:
                log_preview += "\n\n... (truncated, full content in Excel file)"
            
            # Generate download URL (same endpoint without preview flag)
            safe_test_name = test_name.replace("/", "_").replace("\\", "_")
            download_url = f"/api/dashboard/test_log_detail/{platform}/{date}/{category}/{level}/{test_name}"
            
            return jsonify({
                'status': status,
                'log_preview': log_preview,
                'log_size': len(test_log_content),
                'download_url': download_url,
                'filename': f'{safe_test_name}_report.xlsx'
            })
        
        # Generate Excel report using split_and_report.py logic
        excel_file = generate_test_excel_report(test_name, test_log_content)
        
        logger.info(f"[LOG_DETAIL] Generated Excel report: {excel_file}")
        
        # Sanitize test name for download filename
        safe_test_name = test_name.replace("/", "_").replace("\\", "_")
        
        # Send the Excel file (or text file for now)
        return send_file(
            excel_file,
            as_attachment=True,
            download_name=f'{safe_test_name}_report.txt'
        )
    
    except Exception as e:
        logger.error(f"[LOG_DETAIL] Error generating test log detail: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/notes/<platform>/<date>', methods=['GET'])
def api_dashboard_get_notes(platform, date):
    """Get all notes from _dashboard_notes.json in test report directory"""
    notes_file = os.path.join(dashboard_module.TEST_REPORT_BASE, platform, f'all_test_{date}', '_dashboard_notes.json')
    
    if os.path.exists(notes_file):
        try:
            with open(notes_file, 'r', encoding='utf-8') as f:
                notes = json.load(f)
                return jsonify(notes)
        except Exception as e:
            logger.error(f"Error reading notes from {notes_file}: {e}")
            return jsonify({})
    
    return jsonify({})


@dashboard_bp.route('/notes/<platform>/<date>', methods=['POST'])
def api_dashboard_save_notes(platform, date):
    """Save a note to _dashboard_notes.json in test report directory"""
    notes_file = os.path.join(dashboard_module.TEST_REPORT_BASE, platform, f'all_test_{date}', '_dashboard_notes.json')
    
    try:
        note_data = request.get_json()
        note_key = note_data.get('key')
        note_value = note_data.get('value')
        
        if not note_key:
            return jsonify({'error': 'Note key is required'}), 400
        
        # Check if directory exists
        notes_dir = os.path.dirname(notes_file)
        if not os.path.exists(notes_dir):
            return jsonify({'error': f'Test report directory not found: {notes_dir}'}), 404
        
        # Load existing notes
        notes = {}
        if os.path.exists(notes_file):
            try:
                with open(notes_file, 'r', encoding='utf-8') as f:
                    notes = json.load(f)
            except Exception as e:
                logger.error(f"Error reading existing notes: {e}")
                notes = {}
        
        # Update note
        notes[note_key] = note_value
        
        # Save back to file
        with open(notes_file, 'w', encoding='utf-8') as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)
        
        return jsonify({'status': 'success', 'message': 'Note saved'})
    
    except Exception as e:
        logger.error(f"Error saving note: {e}")
        return jsonify({'error': str(e)}), 500
