"""
Lab Monitor Module
Handles lab configuration, DUT monitoring, and status updates.
"""
import json
import os
import subprocess
import platform
import threading
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional

LAB_CONFIG_FILE = 'lab_config.json'
LAB_STATUS_FILE = 'lab_status.json'

# Default configuration structure
DEFAULT_LAB_CONFIG = {
    "labs": [],
    "version": "1.0"
}

def get_lab_config_path():
    """Get the full path to the lab configuration file."""
    return os.path.join(os.getcwd(), LAB_CONFIG_FILE)

def get_lab_status_path():
    """Get the full path to the lab status file."""
    return os.path.join(os.getcwd(), LAB_STATUS_FILE)

def load_lab_config():
    """Load lab configuration from file."""
    config_path = get_lab_config_path()
    
    if not os.path.exists(config_path):
        # Create default config
        save_lab_config(DEFAULT_LAB_CONFIG)
        return DEFAULT_LAB_CONFIG.copy()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Ensure version field exists
            if 'version' not in config:
                config['version'] = '1.0'
            if 'labs' not in config:
                config['labs'] = []
            return config
    except Exception as e:
        print(f"[LAB_MONITOR] Error loading config: {e}")
        return DEFAULT_LAB_CONFIG.copy()

def save_lab_config(config):
    """Save lab configuration to file."""
    config_path = get_lab_config_path()
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[LAB_MONITOR] Error saving config: {e}")
        return False

def load_lab_status():
    """Load lab status from file."""
    status_path = get_lab_status_path()
    
    if not os.path.exists(status_path):
        return {}
    
    try:
        with open(status_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[LAB_MONITOR] Error loading status: {e}")
        return {}

def save_lab_status(status):
    """Save lab status to file."""
    status_path = get_lab_status_path()
    
    try:
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[LAB_MONITOR] Error saving status: {e}")
        return False

def generate_id(prefix='item'):
    """Generate a unique ID based on timestamp."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    return f"{prefix}_{timestamp}"

def add_lab(lab_name: str, description: str = "") -> Dict:
    """Add a new lab group."""
    config = load_lab_config()
    
    lab_id = generate_id('lab')
    new_lab = {
        "id": lab_id,
        "name": lab_name,
        "description": description,
        "platforms": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    config['labs'].append(new_lab)
    
    if save_lab_config(config):
        return {"success": True, "lab": new_lab}
    else:
        return {"success": False, "error": "Failed to save configuration"}

def update_lab(lab_id: str, lab_name: str = None, description: str = None) -> Dict:
    """Update an existing lab group."""
    config = load_lab_config()
    
    for lab in config['labs']:
        if lab['id'] == lab_id:
            if lab_name is not None:
                lab['name'] = lab_name
            if description is not None:
                lab['description'] = description
            lab['updated_at'] = datetime.now().isoformat()
            
            if save_lab_config(config):
                return {"success": True, "lab": lab}
            else:
                return {"success": False, "error": "Failed to save configuration"}
    
    return {"success": False, "error": "Lab not found"}

def delete_lab(lab_id: str) -> Dict:
    """Delete a lab group."""
    config = load_lab_config()
    
    config['labs'] = [lab for lab in config['labs'] if lab['id'] != lab_id]
    
    if save_lab_config(config):
        return {"success": True}
    else:
        return {"success": False, "error": "Failed to save configuration"}

def add_platform(lab_id: str, platform_name: str, description: str = "") -> Dict:
    """Add a platform to a lab."""
    config = load_lab_config()
    
    for lab in config['labs']:
        if lab['id'] == lab_id:
            platform_id = generate_id('platform')
            new_platform = {
                "id": platform_id,
                "name": platform_name,
                "description": description,
                "duts": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            lab['platforms'].append(new_platform)
            lab['updated_at'] = datetime.now().isoformat()
            
            if save_lab_config(config):
                return {"success": True, "platform": new_platform}
            else:
                return {"success": False, "error": "Failed to save configuration"}
    
    return {"success": False, "error": "Lab not found"}

def update_platform(lab_id: str, platform_id: str, platform_name: str = None, description: str = None) -> Dict:
    """Update an existing platform."""
    config = load_lab_config()
    
    for lab in config['labs']:
        if lab['id'] == lab_id:
            for platform in lab['platforms']:
                if platform['id'] == platform_id:
                    if platform_name is not None:
                        platform['name'] = platform_name
                    if description is not None:
                        platform['description'] = description
                    platform['updated_at'] = datetime.now().isoformat()
                    lab['updated_at'] = datetime.now().isoformat()
                    
                    if save_lab_config(config):
                        return {"success": True, "platform": platform}
                    else:
                        return {"success": False, "error": "Failed to save configuration"}
    
    return {"success": False, "error": "Platform not found"}

def delete_platform(lab_id: str, platform_id: str) -> Dict:
    """Delete a platform from a lab."""
    config = load_lab_config()
    
    for lab in config['labs']:
        if lab['id'] == lab_id:
            lab['platforms'] = [p for p in lab['platforms'] if p['id'] != platform_id]
            lab['updated_at'] = datetime.now().isoformat()
            
            if save_lab_config(config):
                return {"success": True}
            else:
                return {"success": False, "error": "Failed to save configuration"}
    
    return {"success": False, "error": "Lab not found"}

def add_dut(lab_id: str, platform_id: str, dut_name: str, ip_address: str = "", 
            config_type: str = "Config A", description: str = "", password: str = "") -> Dict:
    """Add a DUT to a platform."""
    config = load_lab_config()
    
    # Ensure all fields are strings, not objects
    dut_name = str(dut_name) if dut_name and not isinstance(dut_name, dict) else "Unnamed DUT"
    ip_address = str(ip_address) if ip_address and not isinstance(ip_address, dict) else ""
    password = str(password) if password and not isinstance(password, dict) else ""
    config_type = str(config_type) if config_type and not isinstance(config_type, dict) else "Config A"
    description = str(description) if description and not isinstance(description, dict) else ""
    
    for lab in config['labs']:
        if lab['id'] == lab_id:
            for platform in lab['platforms']:
                if platform['id'] == platform_id:
                    dut_id = generate_id('dut')
                    new_dut = {
                        "id": dut_id,
                        "name": dut_name,
                        "ip_address": ip_address,
                        "password": password,
                        "config_type": config_type,
                        "description": description,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    platform['duts'].append(new_dut)
                    platform['updated_at'] = datetime.now().isoformat()
                    lab['updated_at'] = datetime.now().isoformat()
                    
                    if save_lab_config(config):
                        return {"success": True, "dut": new_dut}
                    else:
                        return {"success": False, "error": "Failed to save configuration"}
    
    return {"success": False, "error": "Platform not found"}

def update_dut(lab_id: str, platform_id: str, dut_id: str, 
               dut_name: str = None, ip_address: str = None, 
               config_type: str = None, description: str = None, password: str = None) -> Dict:
    """Update an existing DUT."""
    config = load_lab_config()
    
    for lab in config['labs']:
        if lab['id'] == lab_id:
            for platform in lab['platforms']:
                if platform['id'] == platform_id:
                    for dut in platform['duts']:
                        if dut['id'] == dut_id:
                            # Ensure all fields are strings, not objects
                            if dut_name is not None:
                                dut['name'] = str(dut_name) if not isinstance(dut_name, dict) else "Unnamed DUT"
                            if ip_address is not None:
                                dut['ip_address'] = str(ip_address) if not isinstance(ip_address, dict) else ""
                            if password is not None:
                                dut['password'] = str(password) if not isinstance(password, dict) else ""
                            if config_type is not None:
                                dut['config_type'] = str(config_type) if not isinstance(config_type, dict) else "Config A"
                            if description is not None:
                                dut['description'] = str(description) if not isinstance(description, dict) else ""
                            dut['updated_at'] = datetime.now().isoformat()
                            platform['updated_at'] = datetime.now().isoformat()
                            lab['updated_at'] = datetime.now().isoformat()
                            
                            if save_lab_config(config):
                                return {"success": True, "dut": dut}
                            else:
                                return {"success": False, "error": "Failed to save configuration"}
    
    return {"success": False, "error": "DUT not found"}

def delete_dut(lab_id: str, platform_id: str, dut_id: str) -> Dict:
    """Delete a DUT from a platform."""
    config = load_lab_config()
    
    for lab in config['labs']:
        if lab['id'] == lab_id:
            for platform in lab['platforms']:
                if platform['id'] == platform_id:
                    platform['duts'] = [d for d in platform['duts'] if d['id'] != dut_id]
                    platform['updated_at'] = datetime.now().isoformat()
                    lab['updated_at'] = datetime.now().isoformat()
                    
                    if save_lab_config(config):
                        return {"success": True}
                    else:
                        return {"success": False, "error": "Failed to save configuration"}
    
    return {"success": False, "error": "Platform not found"}

def move_platform(source_lab_id: str, target_lab_id: str, platform_id: str) -> Dict:
    """Move a platform from one lab to another."""
    config = load_lab_config()
    
    # Find and remove platform from source lab
    platform_data = None
    for lab in config['labs']:
        if lab['id'] == source_lab_id:
            for i, platform in enumerate(lab['platforms']):
                if platform['id'] == platform_id:
                    platform_data = lab['platforms'].pop(i)
                    lab['updated_at'] = datetime.now().isoformat()
                    break
            break
    
    if not platform_data:
        return {"success": False, "error": "Platform not found in source lab"}
    
    # Add platform to target lab
    for lab in config['labs']:
        if lab['id'] == target_lab_id:
            platform_data['updated_at'] = datetime.now().isoformat()
            lab['platforms'].append(platform_data)
            lab['updated_at'] = datetime.now().isoformat()
            
            if save_lab_config(config):
                return {"success": True, "platform": platform_data}
            else:
                return {"success": False, "error": "Failed to save configuration"}
    
    return {"success": False, "error": "Target lab not found"}

def move_dut(source_platform_id: str, target_platform_id: str, dut_id: str) -> Dict:
    """Move a DUT from one platform to another."""
    config = load_lab_config()
    
    # Find and remove DUT from source platform
    dut_data = None
    source_lab = None
    for lab in config['labs']:
        for platform in lab['platforms']:
            if platform['id'] == source_platform_id:
                for i, dut in enumerate(platform['duts']):
                    if dut['id'] == dut_id:
                        dut_data = platform['duts'].pop(i)
                        platform['updated_at'] = datetime.now().isoformat()
                        source_lab = lab
                        break
                break
        if dut_data:
            break
    
    if not dut_data:
        return {"success": False, "error": "DUT not found in source platform"}
    
    # Add DUT to target platform
    for lab in config['labs']:
        for platform in lab['platforms']:
            if platform['id'] == target_platform_id:
                dut_data['updated_at'] = datetime.now().isoformat()
                platform['duts'].append(dut_data)
                platform['updated_at'] = datetime.now().isoformat()
                lab['updated_at'] = datetime.now().isoformat()
                
                if source_lab:
                    source_lab['updated_at'] = datetime.now().isoformat()
                
                if save_lab_config(config):
                    return {"success": True, "dut": dut_data}
                else:
                    return {"success": False, "error": "Failed to save configuration"}
    
    return {"success": False, "error": "Target platform not found"}

def update_dut_status(dut_id: str, status: str, last_seen: str = None) -> Dict:
    """Update DUT status (online/offline/testing)."""
    status_data = load_lab_status()
    
    if dut_id not in status_data:
        status_data[dut_id] = {}
    
    status_data[dut_id]['status'] = status
    status_data[dut_id]['last_seen'] = last_seen or datetime.now().isoformat()
    status_data[dut_id]['updated_at'] = datetime.now().isoformat()
    
    if save_lab_status(status_data):
        return {"success": True, "status": status_data[dut_id]}
    else:
        return {"success": False, "error": "Failed to save status"}

def get_dut_status(dut_id: str) -> Dict:
    """Get DUT status."""
    status_data = load_lab_status()
    
    if dut_id in status_data:
        return status_data[dut_id]
    else:
        return {
            "status": "unknown",
            "last_seen": None,
            "updated_at": None
        }

def get_all_dut_statuses() -> Dict:
    """Get all DUT statuses."""
    return load_lab_status()

def copy_platform(source_lab_id: str, target_lab_id: str, platform_id: str) -> Dict:
    """Copy a platform from one lab to another."""
    import copy
    config = load_lab_config()
    
    # Find platform in source lab
    platform_data = None
    for lab in config['labs']:
        if lab['id'] == source_lab_id:
            for platform in lab['platforms']:
                if platform['id'] == platform_id:
                    # Deep copy the platform
                    platform_data = copy.deepcopy(platform)
                    break
            break
    
    if not platform_data:
        return {"success": False, "error": "Platform not found in source lab"}
    
    # Generate new IDs for the copied platform and all its DUTs
    platform_data['id'] = generate_id('platform')
    platform_data['name'] = platform_data['name'] + ' (Copy)'
    platform_data['created_at'] = datetime.now().isoformat()
    platform_data['updated_at'] = datetime.now().isoformat()
    
    # Generate new IDs for all DUTs
    for dut in platform_data.get('duts', []):
        dut['id'] = generate_id('dut')
        dut['name'] = dut['name'] + ' (Copy)'
        dut['created_at'] = datetime.now().isoformat()
        dut['updated_at'] = datetime.now().isoformat()
    
    # Add platform to target lab
    for lab in config['labs']:
        if lab['id'] == target_lab_id:
            lab['platforms'].append(platform_data)
            lab['updated_at'] = datetime.now().isoformat()
            
            if save_lab_config(config):
                return {"success": True, "platform": platform_data}
            else:
                return {"success": False, "error": "Failed to save configuration"}
    
    return {"success": False, "error": "Target lab not found"}

def copy_dut(source_platform_id: str, target_platform_id: str, dut_id: str) -> Dict:
    """Copy a DUT from one platform to another."""
    import copy
    config = load_lab_config()
    
    # Find DUT in source platform
    dut_data = None
    for lab in config['labs']:
        for platform in lab['platforms']:
            if platform['id'] == source_platform_id:
                for dut in platform['duts']:
                    if dut['id'] == dut_id:
                        # Deep copy the DUT
                        dut_data = copy.deepcopy(dut)
                        break
                break
        if dut_data:
            break
    
    if not dut_data:
        return {"success": False, "error": "DUT not found in source platform"}
    
    # Generate new ID and update name
    dut_data['id'] = generate_id('dut')
    dut_data['name'] = dut_data['name'] + ' (Copy)'
    dut_data['created_at'] = datetime.now().isoformat()
    dut_data['updated_at'] = datetime.now().isoformat()
    
    # Add DUT to target platform
    for lab in config['labs']:
        for platform in lab['platforms']:
            if platform['id'] == target_platform_id:
                platform['duts'].append(dut_data)
                platform['updated_at'] = datetime.now().isoformat()
                lab['updated_at'] = datetime.now().isoformat()
                
                if save_lab_config(config):
                    return {"success": True, "dut": dut_data}
                else:
                    return {"success": False, "error": "Failed to save configuration"}
    
    return {"success": False, "error": "Target platform not found"}


def ping_host(ip_address: str, timeout: int = 2) -> bool:
    """
    Ping a host to check if it's online.
    Returns True if host responds, False otherwise.
    """
    if not ip_address or ip_address.strip() == '':
        return False
    
    try:
        # Determine the ping command based on the operating system
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
        
        # Build the ping command
        command = ['ping', param, '1', timeout_param, str(timeout), ip_address]
        
        # Execute ping command
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 1
        )
        
        # Check if ping was successful
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        print(f"[LAB_MONITOR] Error pinging {ip_address}: {e}")
        return False


def check_dut_status(dut_id: str, ip_address: str) -> str:
    """
    Check a single DUT's online status by pinging its IP address.
    Also checks if a test is currently running on the DUT.
    Returns 'testing', 'online', 'offline', or 'unknown'.
    """
    if not ip_address or ip_address.strip() == '':
        return 'unknown'
    
    is_online = ping_host(ip_address)
    
    if not is_online:
        return 'offline'
    
    # If online, check if test is running via API
    try:
        url = f'http://{ip_address}:5000/api/test/status'
        response = requests.get(url, timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('running', False):
                return 'testing'
    except (requests.RequestException, requests.Timeout, ValueError):
        # If we can't check test status, just return online
        pass  # Network error or invalid response
    
    return 'online'


def get_dut_version(ip_address: str, timeout: int = 5) -> Dict:
    """
    Get NUI version from a DUT via HTTP API.
    Returns dict with 'success', 'version', and optional 'error'.
    """
    if not ip_address or ip_address.strip() == '':
        return {'success': False, 'error': 'No IP address provided', 'version': 'unknown'}
    
    try:
        # Try to get version from DUT's /api/version endpoint
        url = f'http://{ip_address}:5000/api/version'
        response = requests.get(url, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            version = data.get('version', 'unknown')
            return {'success': True, 'version': version}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}', 'version': 'unknown'}
            
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Timeout', 'version': 'unknown'}
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'Connection refused', 'version': 'unknown'}
    except Exception as e:
        return {'success': False, 'error': str(e), 'version': 'unknown'}


def update_dut_version(dut_id: str, ip_address: str) -> Dict:
    """
    Query and update a single DUT's version information.
    Returns dict with 'success', 'version', 'dut_id', and optional 'error'.
    """
    result = get_dut_version(ip_address)
    
    if result['success']:
        # Update status file with version info
        status_data = load_lab_status()
        
        if dut_id not in status_data:
            status_data[dut_id] = {}
        
        status_data[dut_id]['version'] = result['version']
        status_data[dut_id]['version_updated_at'] = datetime.now().isoformat()
        
        if save_lab_status(status_data):
            return {
                'success': True,
                'dut_id': dut_id,
                'version': result['version']
            }
        else:
            return {
                'success': False,
                'dut_id': dut_id,
                'version': result['version'],
                'error': 'Failed to save version to status file'
            }
    else:
        return {
            'success': False,
            'dut_id': dut_id,
            'version': 'unknown',
            'error': result.get('error', 'Failed to get version')
        }


def get_all_dut_versions() -> Dict:
    """
    Query and update versions for all DUTs with IP addresses.
    Returns summary of the operation.
    """
    config = load_lab_config()
    status_data = load_lab_status()
    
    checked_count = 0
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    results = []
    
    # Iterate through all DUTs
    for lab in config.get('labs', []):
        for platform in lab.get('platforms', []):
            for dut in platform.get('duts', []):
                dut_id = dut.get('id')
                ip_address = dut.get('ip_address', '').strip()
                
                if not ip_address:
                    skipped_count += 1
                    continue
                
                checked_count += 1
                result = update_dut_version(dut_id, ip_address)
                
                if result['success']:
                    success_count += 1
                else:
                    failed_count += 1
                
                results.append(result)
    
    print(f"[LAB_MONITOR] Version check: {success_count} success, {failed_count} failed, {skipped_count} skipped")
    
    return {
        'success': True,
        'checked_count': checked_count,
        'success_count': success_count,
        'failed_count': failed_count,
        'skipped_count': skipped_count,
        'results': results
    }


def update_all_dut_statuses() -> Dict:
    """
    Check and update the status of all DUTs with IP addresses.
    Returns a summary of the update operation.
    """
    config = load_lab_config()
    status_data = load_lab_status()
    
    checked_count = 0
    online_count = 0
    offline_count = 0
    skipped_count = 0
    
    # Iterate through all DUTs
    for lab in config.get('labs', []):
        for platform in lab.get('platforms', []):
            for dut in platform.get('duts', []):
                dut_id = dut.get('id')
                ip_address = dut.get('ip_address', '').strip()
                
                if not ip_address:
                    skipped_count += 1
                    continue
                
                # Check status
                status = check_dut_status(dut_id, ip_address)
                checked_count += 1
                
                if status == 'online':
                    online_count += 1
                elif status == 'offline':
                    offline_count += 1
                
                # Update status data
                if dut_id not in status_data:
                    status_data[dut_id] = {}
                
                status_data[dut_id]['status'] = status
                status_data[dut_id]['last_checked'] = datetime.now().isoformat()
                
                if status == 'online':
                    status_data[dut_id]['last_seen'] = datetime.now().isoformat()
                
                status_data[dut_id]['updated_at'] = datetime.now().isoformat()
    
    # Save updated status
    save_lab_status(status_data)
    
    return {
        "success": True,
        "summary": {
            "checked": checked_count,
            "online": online_count,
            "offline": offline_count,
            "skipped": skipped_count,
            "timestamp": datetime.now().isoformat()
        }
    }


def check_single_dut(dut_id: str) -> Dict:
    """
    Check and update the status of a single DUT.
    Returns the updated status.
    """
    config = load_lab_config()
    
    # Find the DUT
    dut_found = None
    for lab in config.get('labs', []):
        for platform in lab.get('platforms', []):
            for dut in platform.get('duts', []):
                if dut.get('id') == dut_id:
                    dut_found = dut
                    break
            if dut_found:
                break
        if dut_found:
            break
    
    if not dut_found:
        return {"success": False, "error": "DUT not found"}
    
    ip_address = dut_found.get('ip_address', '').strip()
    
    if not ip_address:
        return {"success": False, "error": "DUT has no IP address"}
    
    # Check status
    status = check_dut_status(dut_id, ip_address)
    
    # Update status data
    status_data = load_lab_status()
    
    if dut_id not in status_data:
        status_data[dut_id] = {}
    
    status_data[dut_id]['status'] = status
    status_data[dut_id]['last_checked'] = datetime.now().isoformat()
    
    if status == 'online':
        status_data[dut_id]['last_seen'] = datetime.now().isoformat()
    
    status_data[dut_id]['updated_at'] = datetime.now().isoformat()
    
    # Save updated status
    if save_lab_status(status_data):
        return {"success": True, "status": status_data[dut_id]}
    else:
        return {"success": False, "error": "Failed to save status"}


# Background status checker
_status_checker_thread = None
_status_checker_running = False
_status_check_interval = 30  # seconds
_status_checker_last_check = None  # timestamp of last check


def start_background_status_checker(interval: int = 30):
    """
    Start a background thread that periodically checks all DUT statuses and versions.
    """
    global _status_checker_thread, _status_checker_running, _status_check_interval
    
    if _status_checker_running:
        print("[LAB_MONITOR] Background status checker already running")
        return
    
    _status_check_interval = interval
    _status_checker_running = True
    
    def checker_loop():
        global _status_checker_running, _status_checker_last_check
        print(f"[LAB_MONITOR] Background status checker started (interval: {interval}s)")
        
        check_count = 0  # Counter to trigger version check every 10 cycles
        
        while _status_checker_running:
            try:
                _status_checker_last_check = time.time()
                
                # Always check status
                result = update_all_dut_statuses()
                summary = result.get('summary', {})
                print(f"[LAB_MONITOR] Status check: {summary.get('online', 0)} online, "
                      f"{summary.get('offline', 0)} offline, {summary.get('skipped', 0)} skipped")
                
                # Check versions every 10 cycles (e.g., every 5 minutes if interval is 30s)
                check_count += 1
                if check_count >= 10:
                    check_count = 0
                    try:
                        version_result = get_all_dut_versions()
                        print(f"[LAB_MONITOR] Version check: {version_result.get('success_count', 0)} success, "
                              f"{version_result.get('failed_count', 0)} failed, {version_result.get('skipped_count', 0)} skipped")
                    except Exception as ve:
                        print(f"[LAB_MONITOR] Error in version checker: {ve}")
                
            except Exception as e:
                print(f"[LAB_MONITOR] Error in status checker: {e}")
            
            # Wait for the next interval
            time.sleep(_status_check_interval)
    
    _status_checker_thread = threading.Thread(target=checker_loop, daemon=True)
    _status_checker_thread.start()


def stop_background_status_checker():
    """
    Stop the background status checker thread.
    """
    global _status_checker_running
    
    if _status_checker_running:
        print("[LAB_MONITOR] Stopping background status checker")
        _status_checker_running = False
        if _status_checker_thread:
            _status_checker_thread.join(timeout=5)


def get_status_checker_info() -> Dict:
    """
    Get information about the background status checker.
    """
    global _status_checker_last_check
    
    next_check_in = 0
    if _status_checker_running and _status_checker_last_check:
        elapsed = time.time() - _status_checker_last_check
        next_check_in = max(0, int(_status_check_interval - elapsed))
    
    return {
        "running": _status_checker_running,
        "interval": _status_check_interval,
        "next_check_in": next_check_in
    }


def update_status_checker_interval(new_interval: int) -> Dict:
    """
    Update the status checker interval dynamically.
    """
    global _status_check_interval
    
    if new_interval < 5:
        return {'success': False, 'error': 'Interval must be at least 5 seconds'}
    
    old_interval = _status_check_interval
    _status_check_interval = new_interval
    
    return {
        'success': True,
        'old_interval': old_interval,
        'new_interval': new_interval,
        'message': f'Status checker interval updated from {old_interval}s to {new_interval}s'
    }


# =============================================================================
# Report Sync Functions
# =============================================================================

def get_remote_reports(dut_ip: str, platform: str, password: str = "", timeout: int = 10) -> Dict:
    """
    Check what report files exist on a remote DUT using DUT's local API.
    Returns dict with 'success', 'reports' (list of dates), and optional 'error'.
    """
    if not dut_ip or dut_ip.strip() == '':
        return {'success': False, 'error': 'No IP address provided', 'reports': []}
    
    try:
        # Call DUT's local API to list reports
        dut_api_url = f"http://{dut_ip}:5000/api/dut/reports/{platform}"
        
        response = requests.get(dut_api_url, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                # Convert API response format to expected format
                reports = []
                for report in data.get('reports', []):
                    reports.append({
                        'date': report['date'],
                        'is_tarball': report['is_tarball']
                    })
                
                return {
                    'success': True,
                    'reports': reports
                }
            else:
                return {
                    'success': False,
                    'error': data.get('error', 'Unknown error from DUT API'),
                    'reports': []
                }
        else:
            return {
                'success': False,
                'error': f'DUT API returned status {response.status_code}',
                'reports': []
            }
            
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': 'DUT API timeout',
            'reports': []
        }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'error': 'Cannot connect to DUT API',
            'reports': []
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error calling DUT API: {str(e)}',
            'reports': []
        }


def get_local_reports(lab_name: str, platform: str, dut_name: str) -> List[str]:
    """
    Get list of report dates that exist locally for a DUT.
    """
    local_base = f'/home/NUI/test_report/ALL_DB/{lab_name}/{platform}/{dut_name}'
    
    if not os.path.exists(local_base):
        return []
    
    reports = []
    try:
        for item in os.listdir(local_base):
            item_path = os.path.join(local_base, item)
            if os.path.isdir(item_path) and item.startswith('all_test_'):
                # Extract date from folder name: all_test_2026-01-21
                date_str = item.replace('all_test_', '')
                reports.append(date_str)
    except Exception as e:
        print(f"[LAB_MONITOR] Error listing local reports: {e}")
    
    return reports


def get_dut_dashboard_dates(dut_id: str) -> Dict:
    """
    Get available test dates for a DUT's dashboard.
    Returns dict with 'success', 'dates' (list of date strings sorted newest first).
    """
    try:
        # Find DUT information from lab_monitor config
        config = load_lab_config()
        dut_info = None
        lab_name = None
        platform_name = None
        
        for lab in config.get('labs', []):
            for platform in lab.get('platforms', []):
                for dut in platform.get('duts', []):
                    if dut.get('id') == dut_id:
                        dut_info = dut
                        lab_name = lab.get('name', '')
                        platform_name = platform.get('name', '')
                        break
                if dut_info:
                    break
            if dut_info:
                break
        
        if not dut_info or not lab_name or not platform_name:
            return {'success': False, 'error': 'DUT not found', 'dates': []}
        
        # Get dates from ALL_DB directory structure
        dut_name = dut_info.get('name', '')
        dates = get_local_reports(lab_name, platform_name, dut_name)
        dates.sort(reverse=True)  # Most recent first
        
        return {'success': True, 'dates': dates}
    except Exception as e:
        print(f"[LAB_MONITOR] Error getting dashboard dates: {e}")
        return {'success': False, 'error': str(e), 'dates': []}


def get_dut_dashboard_summary(dut_id: str, date: str) -> Dict:
    """
    Get test summary for a DUT on a specific date.
    Returns dict with test results from that date.
    """
    try:
        # Find DUT information
        config = load_lab_config()
        dut_info = None
        lab_name = None
        platform_name = None
        
        for lab in config.get('labs', []):
            for platform in lab.get('platforms', []):
                for dut in platform.get('duts', []):
                    if dut.get('id') == dut_id:
                        dut_info = dut
                        lab_name = lab.get('name', '')
                        platform_name = platform.get('name', '')
                        break
                if dut_info:
                    break
            if dut_info:
                break
        
        if not dut_info or not lab_name or not platform_name:
            return {'success': False, 'error': 'DUT not found'}
        
        # Build path to test report
        dut_name = dut_info.get('name', '')
        report_path = f'/home/NUI/test_report/ALL_DB/{lab_name}/{platform_name}/{dut_name}/all_test_{date}'
        
        if not os.path.exists(report_path):
            return {'success': False, 'error': 'Report not found'}
        
        # Use dashboard module to get summary
        import dashboard as dashboard_module
        original_base = dashboard_module.TEST_REPORT_BASE
        try:
            # Temporarily set TEST_REPORT_BASE to DUT's directory
            dashboard_module.TEST_REPORT_BASE = f'/home/NUI/test_report/ALL_DB/{lab_name}/{platform_name}/{dut_name}'
            
            # Get summary using dashboard module (empty platform since path already includes it)
            summary = dashboard_module.get_dashboard_summary('', date)
            
            if summary:
                summary['lab_name'] = lab_name
                summary['platform_name'] = platform_name
                summary['dut_name'] = dut_name
                return {'success': True, 'summary': summary}
            else:
                return {'success': False, 'error': 'Failed to generate summary'}
        finally:
            dashboard_module.TEST_REPORT_BASE = original_base
            
    except Exception as e:
        print(f"[LAB_MONITOR] Error getting dashboard summary: {e}")
        return {'success': False, 'error': str(e)}


def check_dut_reports(dut_id: str, dut_ip: str, platform: str, lab_name: str, dut_name: str, password: str = "") -> Dict:
    """
    Check if a DUT has new reports that are not synced locally.
    Returns dict with 'has_new_reports', 'new_reports' (list), 'total_remote', 'total_local'.
    """
    if not dut_ip or dut_ip.strip() == '':
        return {
            'success': True,
            'has_new_reports': False,
            'new_reports': [],
            'total_remote': 0,
            'total_local': 0
        }
    
    # Get remote reports
    remote_result = get_remote_reports(dut_ip, platform, password)
    
    if not remote_result['success']:
        return {
            'success': False,
            'error': remote_result.get('error', 'Failed to get remote reports'),
            'has_new_reports': False,
            'new_reports': [],
            'total_remote': 0,
            'total_local': 0
        }
    
    remote_reports = remote_result['reports']
    remote_dates = {r['date'] for r in remote_reports}
    
    # Get local reports
    local_dates = set(get_local_reports(lab_name, platform, dut_name))
    
    # Find new reports
    new_dates = remote_dates - local_dates
    new_reports = [r for r in remote_reports if r['date'] in new_dates]
    
    # Update status file
    status_data = load_lab_status()
    if dut_id not in status_data:
        status_data[dut_id] = {}
    
    status_data[dut_id]['has_new_reports'] = len(new_reports) > 0
    status_data[dut_id]['new_reports_count'] = len(new_reports)
    status_data[dut_id]['reports_checked_at'] = datetime.now().isoformat()
    
    save_lab_status(status_data)
    
    return {
        'success': True,
        'has_new_reports': len(new_reports) > 0,
        'new_reports': new_reports,
        'total_remote': len(remote_reports),
        'total_local': len(local_dates)
    }


def sync_dut_report(dut_ip: str, platform: str, date: str, lab_name: str, dut_name: str, password: str = "", is_tarball: bool = True) -> Dict:
    """
    Sync a specific report from remote DUT to local storage using scp.
    Supports both tar.gz files and directories.
    """
    if not dut_ip or dut_ip.strip() == '':
        return {'success': False, 'error': 'No IP address provided'}
    
    try:
        local_base_dir = f'/home/NUI/test_report/ALL_DB/{lab_name}/{platform}/{dut_name}'
        local_dir = f'{local_base_dir}/all_test_{date}'
        
        # Create local directory
        os.makedirs(local_dir, exist_ok=True)
        
        if is_tarball:
            # Sync tar.gz file
            remote_file = f'/home/NUI/test_report/{platform}/all_test_{date}.tar.gz'
            local_tarball = os.path.join(local_dir, f'all_test_{date}.tar.gz')
            
            if password:
                env = os.environ.copy()
                env['SSHPASS'] = password
                scp_command = [
                    'sshpass', '-e',
                    'scp', '-r',
                    '-o', 'ConnectTimeout=10',
                    '-o', 'StrictHostKeyChecking=no',
                    f'root@{dut_ip}:{remote_file}',
                    local_tarball
                ]
            else:
                scp_command = [
                    'scp', '-r',
                    '-o', 'ConnectTimeout=10',
                    '-o', 'StrictHostKeyChecking=no',
                    f'root@{dut_ip}:{remote_file}',
                    local_tarball
                ]
            
            print(f"[LAB_MONITOR] Syncing tar.gz from {dut_ip}: {date}")
        else:
            # Sync entire directory
            remote_dir = f'/home/NUI/test_report/{platform}/all_test_{date}/'
            
            if password:
                env = os.environ.copy()
                env['SSHPASS'] = password
                scp_command = [
                    'sshpass', '-e',
                    'scp', '-r',
                    '-o', 'ConnectTimeout=10',
                    '-o', 'StrictHostKeyChecking=no',
                    f'root@{dut_ip}:{remote_dir}',
                    local_base_dir
                ]
            else:
                scp_command = [
                    'scp', '-r',
                    '-o', 'ConnectTimeout=10',
                    '-o', 'StrictHostKeyChecking=no',
                    f'root@{dut_ip}:{remote_dir}',
                    local_base_dir
                ]
                env = None
            
            print(f"[LAB_MONITOR] Syncing directory from {dut_ip}: {date}")
        
        result = subprocess.run(
            scp_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,  # 5 minutes timeout
            text=True,
            env=env if password else None
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or 'SCP failed'
            return {'success': False, 'error': error_msg}
        
        # Download completed successfully
        print(f"[LAB_MONITOR] Report synced successfully: {date}")
        return {'success': True, 'date': date, 'local_path': local_dir}
            
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Operation timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def check_all_dut_reports() -> Dict:
    """
    Check all DUTs for new reports.
    Only checks DUTs that are currently online.
    Returns summary of the operation.
    """
    config = load_lab_config()
    dut_statuses = get_all_dut_statuses()  # Get all DUT statuses
    
    checked_count = 0
    has_new_count = 0
    failed_count = 0
    skipped_count = 0
    
    results = []
    logs = []  # Detailed logs for debug window
    
    logs.append({'message': 'Starting report check across all labs (online DUTs only)...', 'type': 'info'})
    
    for lab in config.get('labs', []):
        lab_name = lab.get('name', '')
        logs.append({'message': f'Checking lab: {lab_name}', 'type': 'info'})
        
        for platform in lab.get('platforms', []):
            platform_name = platform.get('name', '')
            logs.append({'message': f'  Platform: {platform_name}', 'type': 'info'})
            
            for dut in platform.get('duts', []):
                dut_id = dut.get('id')
                dut_name = dut.get('name', '')
                ip_address = dut.get('ip_address', '').strip()
                password = dut.get('password', '')
                
                if not ip_address:
                    skipped_count += 1
                    logs.append({'message': f'    ⊘ {dut_name}: No IP address, skipped', 'type': 'warning'})
                    continue
                
                # Check if DUT is online
                dut_status_info = dut_statuses.get(dut_id, {})
                dut_status = dut_status_info.get('status', 'unknown')
                
                if dut_status != 'online':
                    skipped_count += 1
                    logs.append({'message': f'    ⊘ {dut_name}: Status is {dut_status}, skipped', 'type': 'warning'})
                    continue
                
                checked_count += 1
                logs.append({'message': f'    → Checking {dut_name} ({ip_address})...', 'type': 'info'})
                
                result = check_dut_reports(dut_id, ip_address, platform_name, lab_name, dut_name, password)
                
                if result.get('success'):
                    if result.get('has_new_reports'):
                        has_new_count += 1
                        new_count = len(result.get('new_reports', []))
                        logs.append({'message': f'    ✓ {dut_name}: Found {new_count} new report(s)', 'type': 'success'})
                    else:
                        logs.append({'message': f'    ✓ {dut_name}: No new reports', 'type': 'info'})
                else:
                    failed_count += 1
                    error = result.get('error', 'Unknown error')
                    logs.append({'message': f'    ✗ {dut_name}: {error}', 'type': 'error'})
                
                results.append({
                    'dut_id': dut_id,
                    'dut_name': dut_name,
                    **result
                })
    
    summary_msg = f'Check complete: {checked_count} checked, {has_new_count} with new reports, {failed_count} failed, {skipped_count} skipped'
    logs.append({'message': summary_msg, 'type': 'success'})
    print(f"[LAB_MONITOR] {summary_msg}")
    
    return {
        'success': True,
        'checked_count': checked_count,
        'has_new_count': has_new_count,
        'failed_count': failed_count,
        'skipped_count': skipped_count,
        'results': results,
        'logs': logs  # Include detailed logs for debug window
    }


# Background report checker
_report_checker_thread = None
_report_checker_running = False
_report_check_interval = 86400  # 24 hours
_report_checker_last_check = None


def start_background_report_checker(interval: int = 86400):
    """
    Start a background thread that periodically checks all DUTs for new reports.
    Default interval is 24 hours (86400 seconds).
    """
    global _report_checker_thread, _report_checker_running, _report_check_interval
    
    if _report_checker_running:
        print("[LAB_MONITOR] Background report checker already running")
        return
    
    _report_check_interval = interval
    _report_checker_running = True
    
    def checker_loop():
        global _report_checker_running, _report_checker_last_check
        print(f"[LAB_MONITOR] Background report checker started (interval: {interval}s)")
        
        while _report_checker_running:
            try:
                _report_checker_last_check = time.time()
                result = check_all_dut_reports()
                print(f"[LAB_MONITOR] Report check: {result.get('has_new_count', 0)} DUTs with new reports")
            except Exception as e:
                print(f"[LAB_MONITOR] Error in report checker: {e}")
            
            # Wait for the next interval
            time.sleep(_report_check_interval)
    
    _report_checker_thread = threading.Thread(target=checker_loop, daemon=True)
    _report_checker_thread.start()


def stop_background_report_checker():
    """
    Stop the background report checker thread.
    """
    global _report_checker_running
    
    if _report_checker_running:
        print("[LAB_MONITOR] Stopping background report checker")
        _report_checker_running = False


def get_report_checker_info() -> Dict:
    """
    Get information about the background report checker.
    """
    global _report_checker_last_check
    
    next_check_in = 0
    if _report_checker_running and _report_checker_last_check:
        elapsed = time.time() - _report_checker_last_check
        next_check_in = max(0, int(_report_check_interval - elapsed))
    
    return {
        "running": _report_checker_running,
        "interval": _report_check_interval,
        "next_check_in": next_check_in
    }


def update_report_checker_interval(new_interval: int) -> Dict:
    """
    Update the report checker interval dynamically.
    """
    global _report_check_interval
    
    if new_interval < 60:
        return {'success': False, 'error': 'Interval must be at least 60 seconds'}
    
    old_interval = _report_check_interval
    _report_check_interval = new_interval
    
    return {
        'success': True,
        'old_interval': old_interval,
        'new_interval': new_interval,
        'message': f'Report checker interval updated from {old_interval}s to {new_interval}s'
    }

# =============================================================================
# Sync Task Management with Progress Tracking
# =============================================================================

_sync_tasks = {}  # task_id -> task_info
_sync_task_counter = 0


def start_sync_task(dut_id: str, dut_ip: str, platform: str, date: str, lab_name: str, dut_name: str, password: str = "", is_tarball: bool = False) -> str:
    """
    Start a background sync task and return task ID for progress tracking.
    """
    global _sync_task_counter, _sync_tasks
    
    _sync_task_counter += 1
    task_id = f"sync_{_sync_task_counter}_{int(time.time())}"
    
    _sync_tasks[task_id] = {
        'task_id': task_id,
        'dut_id': dut_id,
        'dut_ip': dut_ip,
        'platform': platform,
        'date': date,
        'status': 'starting',
        'progress': 0,
        'message': 'Initializing sync...',
        'started_at': datetime.now().isoformat(),
        'completed_at': None,
        'error': None
    }
    
    def sync_worker():
        try:
            # Update status: connecting
            _sync_tasks[task_id]['status'] = 'connecting'
            _sync_tasks[task_id]['progress'] = 10
            _sync_tasks[task_id]['message'] = f'Connecting to {dut_ip}...'
            
            local_base_dir = f'/home/NUI/test_report/ALL_DB/{lab_name}/{platform}/{dut_name}'
            local_dir = f'{local_base_dir}/all_test_{date}'
            
            # Create local directory
            os.makedirs(local_dir, exist_ok=True)
            
            # Update status: downloading
            _sync_tasks[task_id]['status'] = 'downloading'
            _sync_tasks[task_id]['progress'] = 20
            _sync_tasks[task_id]['message'] = f'Downloading report: {date}'
            
            if is_tarball:
                # Download tar.gz file
                remote_file = f'/home/NUI/test_report/{platform}/all_test_{date}.tar.gz'
                local_tarball = os.path.join(local_dir, f'all_test_{date}.tar.gz')
                
                if password:
                    env = os.environ.copy()
                    env['SSHPASS'] = password
                    scp_command = [
                        'sshpass', '-e',
                        'scp', '-r',
                        '-o', 'ConnectTimeout=10',
                        '-o', 'StrictHostKeyChecking=no',
                        f'root@{dut_ip}:{remote_file}',
                        local_tarball
                    ]
                else:
                    scp_command = [
                        'scp', '-r',
                        '-o', 'ConnectTimeout=10',
                        '-o', 'StrictHostKeyChecking=no',
                        f'root@{dut_ip}:{remote_file}',
                        local_tarball
                    ]
            else:
                # Download entire directory
                remote_dir = f'/home/NUI/test_report/{platform}/all_test_{date}/'
                
                if password:
                    env = os.environ.copy()
                    env['SSHPASS'] = password
                    scp_command = [
                        'sshpass', '-e',
                        'scp', '-r',
                        '-o', 'ConnectTimeout=10',
                        '-o', 'StrictHostKeyChecking=no',
                        f'root@{dut_ip}:{remote_dir}',
                        local_base_dir
                    ]
                else:
                    scp_command = [
                        'scp', '-r',
                        '-o', 'ConnectTimeout=10',
                        '-o', 'StrictHostKeyChecking=no',
                        f'root@{dut_ip}:{remote_dir}',
                        local_base_dir
                    ]
                    env = None
            
            result = subprocess.run(
                scp_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,
                text=True,
                env=env if password else None
            )
            
            if result.returncode != 0:
                raise Exception(result.stderr.strip() or 'SCP failed')
            
            # Update DUT status - clear new report flag
            _sync_tasks[task_id]['status'] = 'completed'
            _sync_tasks[task_id]['progress'] = 100
            _sync_tasks[task_id]['message'] = 'Download completed successfully'
            _sync_tasks[task_id]['completed_at'] = datetime.now().isoformat()
            _sync_tasks[task_id]['local_path'] = local_dir
            
            status_data = load_lab_status()
            if dut_id in status_data:
                status_data[dut_id]['has_new_reports'] = False
                status_data[dut_id]['new_reports_count'] = 0
                status_data[dut_id]['last_synced_at'] = datetime.now().isoformat()
                save_lab_status(status_data)
            
            print(f"[LAB_MONITOR] Sync completed: {task_id} - {date}")
            
        except subprocess.TimeoutExpired:
            _sync_tasks[task_id]['status'] = 'failed'
            _sync_tasks[task_id]['error'] = 'Operation timeout'
            _sync_tasks[task_id]['completed_at'] = datetime.now().isoformat()
        except Exception as e:
            _sync_tasks[task_id]['status'] = 'failed'
            _sync_tasks[task_id]['error'] = str(e)
            _sync_tasks[task_id]['completed_at'] = datetime.now().isoformat()
            print(f"[LAB_MONITOR] Sync failed: {task_id} - {e}")
    
    # Start sync in background thread
    thread = threading.Thread(target=sync_worker, daemon=True)
    thread.start()
    
    return task_id


def get_sync_task_status(task_id: str) -> Dict:
    """
    Get the current status of a sync task.
    """
    if task_id not in _sync_tasks:
        return {'success': False, 'error': 'Task not found'}
    
    task_info = _sync_tasks[task_id].copy()
    task_info['success'] = True
    return task_info


def cleanup_old_sync_tasks():
    """
    Remove completed/failed tasks older than 1 hour to prevent memory buildup.
    """
    global _sync_tasks
    
    current_time = datetime.now()
    tasks_to_remove = []
    
    for task_id, task_info in _sync_tasks.items():
        if task_info['completed_at']:
            completed_time = datetime.fromisoformat(task_info['completed_at'])
            if (current_time - completed_time).total_seconds() > 3600:  # 1 hour
                tasks_to_remove.append(task_id)
    
    for task_id in tasks_to_remove:
        del _sync_tasks[task_id]
    
    if tasks_to_remove:
        print(f"[LAB_MONITOR] Cleaned up {len(tasks_to_remove)} old sync tasks")

# ============================================================================
# Testing Status Functions
# ============================================================================

def check_dut_testing(dut_id: str) -> Dict:
    """
    Check if a DUT is currently running tests.
    Returns dict with 'success' and 'testing' (boolean).
    """
    try:
        status = load_lab_status()
        dut_status = status.get(dut_id, {})
        
        # Check if status is 'testing'
        is_testing = dut_status.get('status') == 'testing'
        
        return {
            'success': True,
            'testing': is_testing,
            'dut_id': dut_id
        }
    except Exception as e:
        print(f"[LAB_MONITOR] Error checking DUT testing status: {e}")
        return {
            'success': False,
            'testing': False,
            'error': str(e)
        }


def check_all_duts_testing() -> Dict:
    """
    Check which DUTs are currently running tests.
    Returns dict with list of testing DUTs.
    """
    try:
        status = load_lab_status()
        testing_duts = []
        
        for dut_id, dut_status in status.items():
            if dut_status.get('status') == 'testing':
                testing_duts.append({
                    'dut_id': dut_id,
                    'last_checked': dut_status.get('last_checked'),
                    'last_seen': dut_status.get('last_seen')
                })
        
        return {
            'success': True,
            'testing_duts': testing_duts,
            'count': len(testing_duts)
        }
    except Exception as e:
        print(f"[LAB_MONITOR] Error checking all DUTs testing status: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================================
# Status Checker Configuration
# ============================================================================

# Default checker configuration
_status_checker_config = {
    'enabled': True,
    'interval': 60,  # seconds
    'last_run': None
}

def get_status_checker_config() -> Dict:
    """Get status checker configuration."""
    return {
        'success': True,
        'config': _status_checker_config.copy()
    }


def update_status_checker_interval(interval: int) -> Dict:
    """Update status checker interval."""
    global _status_checker_config
    
    if interval < 10:
        return {
            'success': False,
            'error': 'Interval must be at least 10 seconds'
        }
    
    _status_checker_config['interval'] = interval
    
    return {
        'success': True,
        'config': _status_checker_config.copy()
    }

def get_dut_diff_summary(dut_id: str, date_curr: str, date_prev: str) -> Dict:
    """
    Get diff of test results for a DUT between two dates.
    """
    try:
        # Find DUT information
        config = load_lab_config()
        dut_info = None
        lab_name = None
        platform_name = None
        
        for lab in config.get('labs', []):
            for platform in lab.get('platforms', []):
                for dut in platform.get('duts', []):
                    if dut.get('id') == dut_id:
                        dut_info = dut
                        lab_name = lab.get('name', '')
                        platform_name = platform.get('name', '')
                        break
                if dut_info:
                    break
            if dut_info:
                break
        
        if not dut_info or not lab_name or not platform_name:
            return {'success': False, 'error': 'DUT not found'}
        
        dut_name = dut_info.get('name', '')
        
        # Use dashboard module to get diff
        import dashboard as dashboard_module
        original_base = dashboard_module.TEST_REPORT_BASE
        try:
            # Temporarily set TEST_REPORT_BASE to DUT's directory
            dashboard_module.TEST_REPORT_BASE = f'/home/NUI/test_report/ALL_DB/{lab_name}/{platform_name}/{dut_name}'
            
            # Get diff using dashboard module (empty platform since path already includes it)
            diff = dashboard_module.get_diff_summary('', date_curr, date_prev)
            
            return {'success': True, 'diff': diff}
        finally:
            dashboard_module.TEST_REPORT_BASE = original_base
            
    except Exception as e:
        logger.error(f"Error getting DUT diff: {e}")
        return {'success': False, 'error': str(e)}
