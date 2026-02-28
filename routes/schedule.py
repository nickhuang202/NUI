import os
import json
import logging
import psutil
import socket
import sys
import subprocess
from flask import Blueprint, jsonify, request

from services.crontab_service import CrontabService
import lab_monitor

logger = logging.getLogger(__name__)

schedule_bp = Blueprint('schedule', __name__, url_prefix='/api/schedule')
cron_service = CrontabService()
EXECUTION_STATUS_FILE = '/home/NUI/.schedule_execution_status.json'
RUNNER_SCRIPT_PATH = '/home/NUI/run_scheduled_profile.py'


def _is_process_alive(pid):
    """Check whether a process is still alive."""
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_execution_status():
    """Read and normalize current schedule execution status."""
    default_status = {
        'running': False,
        'profile_name': None,
        'current_test_title': None,
        'pid': None,
        'updated_at': None
    }

    if not os.path.isfile(EXECUTION_STATUS_FILE):
        return default_status

    try:
        with open(EXECUTION_STATUS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read execution status file: {e}")
        return default_status

    if not isinstance(data, dict):
        return default_status

    status = {**default_status, **data}
    pid = status.get('pid')

    if status.get('running') and not _is_process_alive(pid):
        status['running'] = False
        status['current_test_title'] = None
        status['pid'] = None

        try:
            with open(EXECUTION_STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update execution status file: {e}")

    return status


def _is_repeating_rule(rule_type):
    return rule_type in ('daily', 'weekly', 'monthly', 'custom')


def _should_auto_start_today_runner(rule_type):
    return rule_type in ('single', 'daily', 'weekly', 'monthly', 'custom')


def _is_profile_runner_active(profile_name):
    """Check whether a runner process for a specific profile is already active."""
    for proc in psutil.process_iter(['cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            if not cmdline:
                continue

            has_runner_script = any('run_scheduled_profile.py' in part for part in cmdline)
            has_profile_arg = profile_name in cmdline
            if has_runner_script and has_profile_arg:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False


def _start_today_runner(profile_name):
    """Start today's runner immediately after saving an auto-startable schedule profile."""
    if _is_profile_runner_active(profile_name):
        return False, None, 'already-running'

    if not os.path.isfile(RUNNER_SCRIPT_PATH):
        return False, None, 'runner-script-missing'

    python_exec = '/home/NUI/.venv/bin/python3' if os.path.isfile('/home/NUI/.venv/bin/python3') else sys.executable

    process = subprocess.Popen(
        [python_exec, RUNNER_SCRIPT_PATH, profile_name],
        cwd='/home/NUI',
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    return True, process.pid, 'started'

def get_sys_platform():
    """Detect platform name from fruid.json file or cached file."""
    cache_path = os.path.join(os.getcwd(), '.platform_cache')
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, 'r') as f:
                plat = f.read().strip()
                if plat:
                    return plat
        except:
            pass
            
    fruid_path = '/var/facebook/fboss/fruid.json'
    if not os.path.isfile(fruid_path):
        return 'Unknown'
    
    try:
        with open(fruid_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        info = data.get('Information') or {}
        prod = info.get('Product Name') or info.get('Product') or info.get('ProductName')
        
        if isinstance(prod, str):
            product = prod.strip().upper()
            if product in ('MINIPACK3', 'MINIPACK3BA'):
                return 'MINIPACK3BA'
            elif product == 'MINIPACK3N':
                return 'MINIPACK3N'
            elif product == 'WEDGE800BACT':
                return 'WEDGE800BACT'
            elif product == 'WEDGE800CACT':
                return 'WEDGE800CACT'
    except:
        pass
    return 'Unknown'

@schedule_bp.route('/sysinfo', methods=['GET'])
def get_sysconfig():
    """Get system hardware information."""
    dut_id = (request.args.get('dut_id') or '').strip()
    if dut_id:
        result = lab_monitor.remote_get_schedule_sysinfo(dut_id)
        status_code = int(result.get('status_code', 200 if result.get('success') else 500))
        return jsonify(result), status_code

    try:
        hostname = socket.gethostname()
        cpu_percent = psutil.cpu_percent(interval=None) # Non-blocking read
        mem = psutil.virtual_memory()

        return jsonify({
            'success': True,
            'hostname': hostname,
            'platform': get_sys_platform(),
            'cpu_percent': cpu_percent,
            'mem_used_gb': round(mem.used / (1024**3), 2),
            'mem_total_gb': round(mem.total / (1024**3), 2),
            'mem_percent': mem.percent
        })
    except Exception as e:
        logger.error(f"Error fetching sysinfo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/execution-status', methods=['GET'])
def get_execution_status():
    """Get current scheduled profile execution status for UI."""
    dut_id = (request.args.get('dut_id') or '').strip()
    if dut_id:
        result = lab_monitor.remote_get_schedule_execution_status(dut_id)
        status_code = int(result.get('status_code', 200 if result.get('success') else 500))
        return jsonify(result), status_code

    try:
        status = _read_execution_status()
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        logger.error(f"Error reading execution status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

SCHEDULES_DIR = os.path.join(os.getcwd(), 'schedules')
if not os.path.exists(SCHEDULES_DIR):
    os.makedirs(SCHEDULES_DIR)

def get_safe_filepath(profile_name):
    # Basic sanitization to prevent path traversal
    safe_name = "".join([c for c in profile_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    if not safe_name:
        return None
    return os.path.join(SCHEDULES_DIR, f"{safe_name}.json")

@schedule_bp.route('/profiles', methods=['GET'])
def list_profiles():
    """List all saved daily profiles."""
    dut_id = (request.args.get('dut_id') or '').strip()
    if dut_id:
        result = lab_monitor.remote_list_schedule_profiles(dut_id)
        status_code = int(result.get('status_code', 200 if result.get('success') else 500))
        return jsonify(result), status_code

    try:
        profiles = []
        for filename in os.listdir(SCHEDULES_DIR):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(SCHEDULES_DIR, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        profiles.append({
                            'name': data.get('profile_name', filename[:-5]),
                            'cron_rule': data.get('cron_rule', {}),
                            'filename': filename
                        })
                except json.JSONDecodeError:
                    continue
        return jsonify({'success': True, 'profiles': profiles})
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/profiles/<path:profile_name>', methods=['GET'])
def get_profile(profile_name):
    """Get a specific profile's full data."""
    dut_id = (request.args.get('dut_id') or '').strip()
    if dut_id:
        result = lab_monitor.remote_get_schedule_profile(dut_id, profile_name)
        status_code = int(result.get('status_code', 200 if result.get('success') else 500))
        return jsonify(result), status_code

    filepath = get_safe_filepath(profile_name)
    if not filepath or not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'Profile not found'}), 404
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({'success': True, 'profile_name': profile_name, 'data': data})
    except Exception as e:
        logger.error(f"Error reading profile {profile_name}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/profiles', methods=['POST'])
def save_profile():
    """Save or update a daily profile and sync with crontab."""
    dut_id = (request.args.get('dut_id') or '').strip()

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    if dut_id:
        result = lab_monitor.remote_save_schedule_profile(dut_id, data)
        status_code = int(result.get('status_code', 200 if result.get('success') else 500))
        return jsonify(result), status_code
        
    profile_name = data.get('profile_name')
    if not profile_name:
        return jsonify({'success': False, 'error': 'Profile name is required'}), 400
        
    filepath = get_safe_filepath(profile_name)
    if not filepath:
        return jsonify({'success': False, 'error': 'Invalid profile name'}), 400
        
    try:
        # Save to filesystem
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        # Sync with Crontab
        cron_rule = data.get('cron_rule', {})
        synced = cron_service.sync_profile(profile_name, cron_rule)

        rule_type = (cron_rule or {}).get('type')
        tests = data.get('tests', [])

        today_runner_started = False
        today_runner_pid = None
        today_runner_reason = 'rule-not-auto-started'

        if _should_auto_start_today_runner(rule_type) and isinstance(tests, list) and len(tests) > 0:
            try:
                today_runner_started, today_runner_pid, today_runner_reason = _start_today_runner(profile_name)
            except Exception as runner_error:
                logger.warning(f"[SCHEDULE] Failed to auto-start today runner for '{profile_name}': {runner_error}")
                today_runner_started = False
                today_runner_pid = None
                today_runner_reason = 'start-failed'
        elif _should_auto_start_today_runner(rule_type):
            today_runner_reason = 'no-tests'
        
        logger.info(
            f"[SCHEDULE] Saved profile: {profile_name}, Cron synced: {synced}, "
            f"today runner started: {today_runner_started}, reason: {today_runner_reason}"
        )
        return jsonify({
            'success': True,
            'message': f'Profile "{profile_name}" saved successfully',
            'cron_synced': synced,
            'today_runner_started': today_runner_started,
            'today_runner_pid': today_runner_pid,
            'today_runner_reason': today_runner_reason
        })
    except Exception as e:
        logger.error(f"Error saving profile {profile_name}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/profiles/<path:profile_name>', methods=['DELETE'])
def delete_profile(profile_name):
    """Delete a daily profile and remove from crontab."""
    dut_id = (request.args.get('dut_id') or '').strip()
    if dut_id:
        result = lab_monitor.remote_delete_schedule_profile(dut_id, profile_name)
        status_code = int(result.get('status_code', 200 if result.get('success') else 500))
        return jsonify(result), status_code

    filepath = get_safe_filepath(profile_name)
    if not filepath or not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'Profile not found'}), 404
        
    try:
        os.remove(filepath)
        
        # Remove from Crontab
        cron_service.remove_profile(profile_name)
        
        logger.info(f"[SCHEDULE] Deleted profile: {profile_name}")
        return jsonify({'success': True, 'message': f'Profile "{profile_name}" deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting profile {profile_name}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
