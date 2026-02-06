"""
Test Routes Blueprint
Handles test execution, monitoring, and procedure management endpoints.
"""

import os
import json
import subprocess
import re
from flask import Blueprint, jsonify, request, current_app
from config.logging_config import get_logger
from utils.validators import is_safe_filename, sanitize_command_arg, validate_test_items, validate_platform

logger = get_logger(__name__)

# Create blueprint with URL prefix
test_bp = Blueprint('test', __name__, url_prefix='/api/test')

# Test procedures directory
TEST_PROCEDURES_DIR = os.path.join(os.getcwd(), 'test_procedures')
if not os.path.exists(TEST_PROCEDURES_DIR):
    os.makedirs(TEST_PROCEDURES_DIR)

# Global test execution tracking (shared with main app)
# This will be set by app.py to the TestExecutionManager instance
test_execution = None


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


def get_platform_name():
    """Get platform name from FRUID or default."""
    # Simplified version - actual implementation in app.py
    return 'MINIPACK3N'


@test_bp.route('/scripts')
def api_test_scripts():
    """List available test scripts"""
    test_script_dir = 'test_script'
    
    if not os.path.isdir(test_script_dir):
        return jsonify({'scripts': []})
    
    try:
        scripts = [
            f for f in os.listdir(test_script_dir)
            if f.endswith('.sh') and os.path.isfile(os.path.join(test_script_dir, f))
        ]
        return jsonify({'scripts': sorted(scripts)})
    except Exception as e:
        logger.error(f"Error listing test scripts: {e}")
        return jsonify({'error': str(e)}), 500


@test_bp.route('/bins')
def api_test_bins():
    """List all .zst files from /home/"""
    try:
        bin_dir = '/home'
        
        if not os.path.exists(bin_dir):
            return jsonify({'error': f'Bin directory not found: {bin_dir}', 'bins': []})
        
        # List all .zst files
        bins = []
        for filename in os.listdir(bin_dir):
            if filename.endswith('.zst'):
                filepath = os.path.join(bin_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    bins.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })
        
        # Sort by modification time, newest first
        bins.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({'bins': bins, 'bin_dir': bin_dir})
    except Exception as e:
        logger.error(f"Error listing bins: {e}")
        return jsonify({'error': str(e), 'bins': []})


@test_bp.route('/topology-types')
def api_test_topology_types():
    """Get list of topology types (link test configs)"""
    topology_types = ['default', '400g', 'optics_one', 'optics_two', 'copper']
    return jsonify({'types': topology_types})


@test_bp.route('/topology-files/<platform>')
def api_test_topology_files(platform):
    """Get list of topology JSON files for a platform"""
    if not validate_platform(platform):
        return jsonify({'error': 'Invalid platform'}), 400
    
    try:
        platform_upper = platform.upper()
        # Use absolute path from the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level from routes/ to get to app root
        app_root = os.path.dirname(script_dir)
        topology_dir = os.path.join(app_root, 'Topology', platform_upper)
        
        if not os.path.exists(topology_dir):
            logger.warning(f"Topology directory not found: {topology_dir}")
            return jsonify({'error': f'Topology directory not found for platform: {platform}', 'files': []})
        
        # List all JSON files (including _JSON and .materialized_JSON)
        files = []
        for filename in os.listdir(topology_dir):
            if filename.endswith('.json') or filename.endswith('_JSON') or filename.endswith('.materialized_JSON'):
                filepath = os.path.join(topology_dir, filename)
                if os.path.isfile(filepath):
                    files.append(filename)
        
        # Sort alphabetically
        files.sort()
        
        return jsonify({'files': files, 'platform': platform_upper, 'topology_dir': topology_dir})
    except Exception as e:
        logger.error(f"Error listing topology files: {e}")
        return jsonify({'error': str(e), 'files': []})


@test_bp.route('/upload-bin', methods=['POST'])
def api_test_upload_bin():
    """Upload a custom .zst file to /home/"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    filename = file.filename
    if not is_safe_filename(filename):
        logger.warning(f"[API] Invalid bin filename rejected: {filename}")
        return jsonify({'success': False, 'error': 'Invalid filename'}), 400
    
    if not filename.endswith('.zst'):
        return jsonify({'success': False, 'error': 'Only .zst files are allowed'}), 400
    
    try:
        bin_dir = '/home'
        filepath = os.path.join(bin_dir, filename)
        
        file.save(filepath)
        
        logger.info(f"[API] Binary file uploaded: {filename} to {filepath}")
        return jsonify({
            'success': True,
            'filename': filename,
            'path': filepath,
            'message': f'File uploaded successfully: {filename}'
        })
    except Exception as e:
        logger.error(f"Error uploading binary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@test_bp.route('/procedures')
def api_test_procedures():
    """List saved test procedures"""
    procedures_dir = 'test_procedures'
    
    if not os.path.isdir(procedures_dir):
        return jsonify({'procedures': []})
    
    try:
        procedures = [
            f.replace('.json', '') for f in os.listdir(procedures_dir)
            if f.endswith('.json') and os.path.isfile(os.path.join(procedures_dir, f))
        ]
        return jsonify({'procedures': sorted(procedures)})
    except Exception as e:
        logger.error(f"Error listing procedures: {e}")
        return jsonify({'error': str(e)}), 500


@test_bp.route('/kill-processes', methods=['POST'])
def api_test_kill_processes():
    """Kill running test processes"""
    try:
        test_processes = [
            'run_all_test.sh',
            'Agent_HW_TX_test.sh',
            'ExitEVT.sh',
            'Link_T0_test.sh',
            'Prbs_test.sh',
            'SAI_TX_test.sh'
        ]
        
        killed = []
        for process_name in test_processes:
            try:
                result = subprocess.run(
                    ['pkill', '-9', '-f', process_name],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    killed.append(process_name)
                    logger.info(f"[API] Killed process: {process_name}")
            except Exception as e:
                logger.warning(f"Error killing {process_name}: {e}")
        
        # Reset test execution state
        global test_execution
        if test_execution:
            test_execution.stop_test()
        
        return jsonify({
            'success': True,
            'killed': killed,
            'message': f'Killed {len(killed)} processes'
        })
    except Exception as e:
        logger.error(f"Error killing test processes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# NOTE: /start endpoint is handled in app.py due to complexity and global state dependencies
# The blueprint registration with prefix '/api/test' would create '/api/test/start'
# but app.py has '@app.route('/api/test/start')' which should take precedence if we don't define it here


@test_bp.route('/status')
def api_test_status():
    """Check if any test is currently running"""
    global test_execution
    
    try:
        # Check if we have a tracked test
        if test_execution and test_execution.is_running() and test_execution.get_pid():
            # Verify process is still running
            try:
                result = subprocess.run(
                    ['ps', '-p', str(test_execution.get_pid())],
                    capture_output=True,
                    timeout=2
                )
                
                if result.returncode == 0:
                    return jsonify({
                        'running': True,
                        'script': test_execution.get_script(),
                        'bin': test_execution.get_bin(),
                        'topology': test_execution.get_topology(),
                        'pid': test_execution.get_pid(),
                        'start_time': test_execution.get_start_time()
                    })
                else:
                    test_execution.stop_test()
            except (ProcessLookupError, OSError):
                test_execution.stop_test()
        
        # Fallback: Check for any test-related processes
        test_processes = [
            'run_all_test.sh',
            'Agent_HW_TX_test.sh',
            'ExitEVT.sh',
            'Link_T0_test.sh',
            'Prbs_test.sh',
            'SAI_TX_test.sh'
        ]
        
        for process_name in test_processes:
            try:
                result = subprocess.run(
                    ['pgrep', '-f', process_name],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    return jsonify({
                        'running': True,
                        'script': process_name,
                        'pid': int(result.stdout.strip().split('\n')[0])
                    })
            except (subprocess.SubprocessError, subprocess.TimeoutExpired, ValueError, IndexError):
                pass
        
        return jsonify({'running': False})
        
    except Exception as e:
        logger.error(f"Error checking test status: {e}")
        return jsonify({'running': False, 'error': str(e)})


@test_bp.route('/procedures', methods=['GET'])
def api_test_get_procedures():
    """Get list of saved test procedures"""
    try:
        procedures = []
        for filename in os.listdir(TEST_PROCEDURES_DIR):
            if filename.endswith('.json'):
                procedures.append(filename[:-5])  # Remove .json extension
        return jsonify(sorted(procedures))
    except Exception as e:
        logger.error(f"Error listing procedures: {e}")
        return jsonify({'error': str(e)}), 500


@test_bp.route('/procedures/<procedure_name>', methods=['GET'])
def api_test_get_procedure(procedure_name):
    """Get a specific test procedure"""
    if not is_safe_filename(procedure_name):
        return jsonify({'error': 'Invalid procedure name'}), 400
    
    filepath = os.path.join(TEST_PROCEDURES_DIR, f'{procedure_name}.json')
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Procedure not found'}), 404
    
    try:
        with open(filepath, 'r') as f:
            procedure = json.load(f)

        # Backward compatibility: unwrap nested payloads that were saved as
        # {"name": ..., "config": {...}}
        if isinstance(procedure, dict) and 'config' in procedure and 'name' in procedure:
            logger.info(f"[API] Unwrapping nested procedure config for {procedure_name}")
            procedure = procedure.get('config', {})

        # Return in format expected by frontend
        return jsonify({
            'success': True,
            'name': procedure_name,
            'config': procedure
        })
    except Exception as e:
        logger.error(f"Error loading procedure {procedure_name}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@test_bp.route('/procedures', methods=['POST'])
def api_test_save_procedure():
    """Save a test procedure"""
    try:
        data = request.get_json()
        name = data.get('name')
        config = data.get('config')
        
        if not name:
            return jsonify({'success': False, 'error': 'Procedure name is required'}), 400
        
        if not is_safe_filename(name):
            return jsonify({'success': False, 'error': 'Invalid procedure name'}), 400

        if not config or not isinstance(config, dict):
            return jsonify({'success': False, 'error': 'Invalid procedure config'}), 400
        
        filepath = os.path.join(TEST_PROCEDURES_DIR, f'{name}.json')
        
        # Save only the inner config to keep file format stable
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"[API] Saved test procedure: {name}")
        return jsonify({'success': True, 'message': f'Procedure "{name}" saved'})
    except Exception as e:
        logger.error(f"Error saving procedure: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@test_bp.route('/procedures/<procedure_name>', methods=['DELETE'])
def api_test_delete_procedure(procedure_name):
    """Delete a test procedure"""
    if not is_safe_filename(procedure_name):
        return jsonify({'error': 'Invalid procedure name'}), 400
    
    filepath = os.path.join(TEST_PROCEDURES_DIR, f'{procedure_name}.json')
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Procedure not found'}), 404
    
    try:
        os.remove(filepath)
        logger.info(f"[API] Deleted test procedure: {procedure_name}")
        return jsonify({'success': True, 'message': f'Procedure "{procedure_name}" deleted'})
    except Exception as e:
        logger.error(f"Error deleting procedure {procedure_name}: {e}")
        return jsonify({'error': str(e)}), 500
