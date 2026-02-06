"""
Topology Routes Blueprint
Handles topology configuration, file management, and application endpoints.
"""

import os
import json
import subprocess
import sys
from datetime import datetime
from flask import Blueprint, jsonify, request, abort
from config.logging_config import get_logger
from utils.validators import validate_platform, is_safe_filename

logger = get_logger(__name__)

# Create blueprint (no /api/topology prefix - routes need flexibility)
topology_bp = Blueprint('topology', __name__, url_prefix='/api')


def ensure_switch_config_thrift():
    """Ensure switch_config.thrift exists (from app.py)"""
    thrift_path = os.path.join(os.getcwd(), 'fboss_src', 'switch_config.thrift')
    if not os.path.exists(thrift_path):
        raise FileNotFoundError(f"switch_config.thrift not found at {thrift_path}")


def ensure_topology_file(platform):
    """Find topology file for platform (from app.py)"""
    platform_up = platform.upper()
    base_dir = os.path.join(os.getcwd(), 'Topology', platform_up)
    
    if not os.path.isdir(base_dir):
        raise FileNotFoundError(f"Topology directory not found for platform: {platform_up}")
    
    # Look for materialized_JSON file
    for filename in os.listdir(base_dir):
        if filename.lower().endswith('materialized_json') or filename.lower().endswith('.json'):
            return os.path.join(base_dir, filename)
    
    raise FileNotFoundError(f"No topology file found for platform: {platform_up}")


def parse_materialized_json(file_path):
    """Parse materialized JSON topology file (from app.py)"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    connections = []
    
    # Parse pimInfo structure
    for pim in data.get('pimInfo', []):
        interfaces = pim.get('interfaces', {})
        processed = set()
        
        for port1, info in interfaces.items():
            neighbor = info.get('neighbor')
            if not neighbor or port1 in processed or neighbor in processed:
                continue
            
            # Create bidirectional connection
            profile1 = info.get('profileID', 'PROFILE_DEFAULT')
            profile2 = interfaces.get(neighbor, {}).get('profileID', 'PROFILE_DEFAULT')
            
            connections.append({
                'port1': port1,
                'port2': neighbor,
                'profile1': profile1,
                'profile2': profile2
            })
            
            processed.add(port1)
            processed.add(neighbor)
    
    return connections


def calculate_profile_stats(connections):
    """Calculate profile statistics from connections (from app.py)"""
    stats = {}
    for conn in connections:
        profile1 = conn.get('profile1', 'PROFILE_DEFAULT')
        profile2 = conn.get('profile2', 'PROFILE_DEFAULT')
        
        stats[profile1] = stats.get(profile1, 0) + 1
        if profile1 != profile2:
            stats[profile2] = stats.get(profile2, 0) + 1
    
    return stats


@topology_bp.route('/topology_files/<platform>')
def api_topology_files(platform):
    """List available topology JSON files for a platform."""
    try:
        platform_up = platform.upper()
        base_dir = os.path.join(os.getcwd(), 'Topology', platform_up)
        if not os.path.isdir(base_dir):
            return jsonify({'platform': platform, 'files': []})
        
        files = []
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isfile(item_path):
                ext = os.path.splitext(item)[1].lower()
                # Include .json files and files ending with _JSON (like materialized_JSON)
                if ext == '.json' or item.lower().endswith('_json'):
                    files.append(item)
        
        files.sort()
        return jsonify({'platform': platform, 'files': files})
    except Exception as e:
        logger.error(f"Error listing topology files: {e}")
        return jsonify({'platform': platform, 'files': [], 'error': str(e)})


@topology_bp.route('/topology/<platform>')
def api_topology(platform):
    """Get topology configuration for a platform."""
    # Validate platform
    if not validate_platform(platform):
        logger.warning(f"[API] Invalid platform in topology request: {platform}")
        return jsonify({'error': 'Invalid platform'}), 400
    
    try:
        # Ensure switch_config.thrift is available
        ensure_switch_config_thrift()
        
        # Allow specifying a particular file under the platform directory via ?file=filename
        req_file = request.args.get('file')
        if req_file:
            # Validate filename
            if not is_safe_filename(req_file):
                logger.warning(f"[API] Invalid topology filename: {req_file}")
                return jsonify({'error': 'Invalid filename'}), 400
            
            platform_up = platform.upper()
            base_dir = os.path.join(os.getcwd(), 'Topology', platform_up)
            file_path = os.path.join(base_dir, req_file)
            if not os.path.isfile(file_path):
                abort(404, f'Requested topology file not found: {req_file} for platform {platform_up}')
        else:
            file_path = ensure_topology_file(platform)
    except FileNotFoundError as e:
        abort(404, str(e))

    try:
        conns = parse_materialized_json(file_path)
        stats = calculate_profile_stats(conns)
        
        return jsonify({
            'platform': platform, 
            'file': os.path.basename(file_path), 
            'connections': conns,
            'profile_stats': stats
        })
    except Exception as e:
        logger.error(f"Error parsing topology: {e}")
        abort(500, f'Error parsing topology: {e}')


@topology_bp.route('/save_topology', methods=['POST'])
def api_save_topology():
    """Save current topology to a materialized_JSON file."""
    try:
        data = request.get_json()
        platform = data.get('platform', '').upper()
        filename = data.get('filename', '')
        connections = data.get('connections', [])
        
        # Validate platform
        if not platform or not validate_platform(platform):
            logger.warning(f"[API] Invalid platform in save topology: {platform}")
            return jsonify({'error': 'Invalid platform'}), 400
        
        if not filename:
            return jsonify({'error': 'Filename is required'}), 400
        
        # Validate filename
        if not is_safe_filename(filename):
            logger.warning(f"[API] Invalid filename in save topology: {filename}")
            return jsonify({'error': 'Invalid filename'}), 400
        
        if not connections:
            return jsonify({'error': 'No connections to save'}), 400
        
        # Create Topology directory if it doesn't exist
        base_dir = os.path.join(os.getcwd(), 'Topology', platform)
        os.makedirs(base_dir, exist_ok=True)
        
        # Ensure filename has proper extension
        if not (filename.endswith('.json') or filename.endswith('_JSON')):
            filename += '.materialized_JSON'
        
        file_path = os.path.join(base_dir, filename)
        
        # Build materialized_JSON structure matching the original format
        interfaces = {}
        
        for conn in connections:
            port1 = conn.get('port1')
            port2 = conn.get('port2')
            profile1 = conn.get('profile1')
            profile2 = conn.get('profile2')
            
            if not port1 or not port2:
                continue
            
            # Add bidirectional connections with neighbor as string (not object)
            if port1 not in interfaces:
                interfaces[port1] = {
                    'neighbor': port2,
                    'profileID': profile1,
                    'hasTransceiver': True
                }
            
            if port2 not in interfaces:
                interfaces[port2] = {
                    'neighbor': port1,
                    'profileID': profile2,
                    'hasTransceiver': True
                }
        
        # Create the materialized JSON structure matching original format
        topology_data = {
            'platform': platform.lower(),
            'pimInfo': [
                {
                    'slot': 1,
                    'pimName': '',
                    'interfaces': interfaces
                }
            ],
            'metadata': {
                'saved_by': 'NUI',
                'timestamp': datetime.now().isoformat(),
                'connection_count': len(connections)
            }
        }
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(topology_data, f, indent=2)
        
        logger.info(f"[API] Saved topology: {filename} ({len(connections)} connections)")
        return jsonify({
            'success': True,
            'file': filename,
            'path': file_path,
            'connections': len(connections)
        })
        
    except Exception as e:
        logger.error(f"Error saving topology: {e}")
        return jsonify({'error': str(e)}), 500


@topology_bp.route('/apply_topology', methods=['POST'])
def api_apply_topology():
    """Execute reconvert.py to apply the current topology configuration."""
    try:
        data = request.get_json()
        platform = data.get('platform', '').upper()
        config_filename = data.get('config_filename', None)  # Optional custom config filename
        
        # Validate platform
        if not platform or not validate_platform(platform):
            logger.warning(f"[API] Invalid platform in apply topology: {platform}")
            return jsonify({'error': 'Invalid platform'}), 400
        
        # Validate config filename if provided
        if config_filename and not is_safe_filename(config_filename):
            logger.warning(f"[API] Invalid config filename in apply topology: {config_filename}")
            return jsonify({'error': 'Invalid config filename'}), 400
        
        logger.info(f"[DEBUG] Applying topology for platform: {platform}, config: {config_filename}")
        
        # Find reconvert.py in the current directory
        convert_script = os.path.join(os.getcwd(), 'reconvert.py')
        
        if not os.path.isfile(convert_script):
            return jsonify({'error': 'reconvert.py not found'}), 404
        
        # Default topology files mapping (same as in app.py)
        DEFAULT_TOPOLOGY_FILES = {
            'MINIPACK3N': 'minipack3n.materialized_JSON',
            'MINIPACK3BA': 'montblanc.materialized_JSON',
            'WEDGE800BACT': 'wedge800bact.materialized_JSON',
            'WEDGE800CACT': 'wedge800bact.materialized_JSON'
        }

        # Check if config_filename is actually a Topology file in Topology/ directory
        topology_handled = False
        if config_filename:
            topo_dir = os.path.join(os.getcwd(), 'Topology', platform)
            possible_topo_path = os.path.join(topo_dir, config_filename)
            
            if os.path.exists(possible_topo_path):
                # User provided a TOPOLOGY file, not a config file
                # The UI procedure overwrites the default topology file
                default_filename = DEFAULT_TOPOLOGY_FILES.get(platform)
                
                if default_filename:
                    target_path = os.path.join(topo_dir, default_filename)
                    if possible_topo_path != target_path:
                        import shutil
                        try:
                            shutil.copy2(possible_topo_path, target_path)
                            logger.info(f"[API] Copied custom topology '{config_filename}' to default '{default_filename}'")
                        except Exception as e:
                            logger.error(f"[API] Failed to copy topology file: {e}")
                    
                    # Do NOT pass config_filename to reconvert.py
                    # We want reconvert.py to use the updated DEFAULT topology and DEFAULT config
                    topology_handled = True
                    logger.info(f"[API] Treating '{config_filename}' as Topology file (updated default)")

        # Build command arguments
        cmd_args = [sys.executable, convert_script, platform.lower()]
        
        # Add config filename if provided AND not handled as a topology update
        if config_filename and not topology_handled:
            cmd_args.append(config_filename)
        
        # Execute reconvert.py
        try:
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.getcwd()
            )
            
            output = result.stdout
            error = result.stderr
            
            if result.returncode == 0:
                logger.info(f"[API] Topology applied successfully: {platform}")
                return jsonify({
                    'success': True,
                    'message': f'reconvert.py executed successfully (platform: {platform}, config: {config_filename or "default"})',
                    'output': output,
                    'returncode': result.returncode
                })
            else:
                logger.warning(f"[API] Topology apply failed: {platform}, code={result.returncode}")
                return jsonify({
                    'success': False,
                    'error': f'reconvert.py failed with return code {result.returncode}',
                    'output': output,
                    'stderr': error,
                    'returncode': result.returncode
                }), 500
                
        except subprocess.TimeoutExpired:
            logger.error(f"[API] Topology apply timeout: {platform}")
            return jsonify({'error': 'reconvert.py execution timed out (60s)'}), 504
        except Exception as e:
            logger.error(f"[API] Topology apply exception: {e}")
            return jsonify({'error': f'Failed to execute reconvert.py: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error in apply_topology: {e}")
        return jsonify({'error': str(e)}), 500
