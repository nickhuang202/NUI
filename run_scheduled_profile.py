#!/usr/bin/env python3
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
import subprocess
import time

# Setup logging suitable for a background cron job
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [CRON_RUNNER] %(message)s',
    handlers=[
        logging.FileHandler('/home/NUI/logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SCHEDULES_DIR = '/home/NUI/schedules'
TEST_PROCEDURES_DIR = '/home/NUI/test_procedures'
TEST_SCRIPT_DIR = '/home/NUI/test_script'
EXECUTION_STATUS_FILE = '/home/NUI/.schedule_execution_status.json'


def get_safe_profile_filepath(profile_name):
    """Sanitize profile name to match schedule API file naming and prevent path traversal."""
    safe_name = "".join([c for c in str(profile_name) if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    if not safe_name:
        return None
    return os.path.join(SCHEDULES_DIR, f"{safe_name}.json")


def write_execution_status(status_data):
    """Persist schedule execution status for UI polling."""
    payload = {
        'running': False,
        'profile_name': None,
        'current_test_title': None,
        'pid': None,
        'updated_at': datetime.now().isoformat()
    }
    payload.update(status_data or {})
    if isinstance(payload.get('pid'), bool):
        payload['pid'] = None
    if not isinstance(payload.get('running'), bool):
        payload['running'] = bool(payload.get('running'))
    payload['updated_at'] = datetime.now().isoformat()

    try:
        with open(EXECUTION_STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write execution status: {e}")


def load_test_procedure(procedure_name):
    """Load a saved test procedure and return normalized config dict."""
    filepath = os.path.join(TEST_PROCEDURES_DIR, f"{procedure_name}.json")
    if not os.path.exists(filepath):
        logger.error(f"Procedure file not found: {filepath}")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Backward compatibility: some procedure files are wrapped as
        # {"name": "...", "config": {...}}
        if isinstance(data, dict) and isinstance(data.get('config'), dict):
            return data['config']

        if isinstance(data, dict):
            return data

        logger.error(f"Invalid procedure format in {filepath}")
        return None
    except Exception as e:
        logger.error(f"Failed to load procedure {filepath}: {e}")
        return None


def build_test_items_string(test_items):
    """Convert test_items object to comma-separated format for run_all_test.sh."""
    if not isinstance(test_items, dict):
        return ''

    selected_items = []

    flat_format_keys = {
        'sai_t0', 'sai_t1', 'sai_t2',
        'agent_t0', 'agent_t1', 'agent_t2',
        'link_t0', 'link_t1', 'link_t2',
        'link', 'link_test', 'evt', 'evt_exit'
    }
    has_flat_format = any(key in flat_format_keys for key in test_items.keys())

    if has_flat_format:
        for level in ['t0', 't1', 't2']:
            if test_items.get(f'sai_{level}'):
                selected_items.append(f'SAI_{level.upper()}')

        for level in ['t0', 't1', 't2']:
            if test_items.get(f'agent_{level}'):
                selected_items.append(f'AGENT_{level.upper()}')

        for level in ['t0', 't1', 't2']:
            if test_items.get(f'link_{level}'):
                selected_items.append(f'LINK_{level.upper()}')

        if test_items.get('evt') or test_items.get('evt_exit'):
            selected_items.append('EVT_EXIT')
    else:
        if isinstance(test_items.get('sai'), list):
            for level in test_items['sai']:
                selected_items.append(f'SAI_{str(level).upper()}')

        if isinstance(test_items.get('agenthw'), list):
            for level in test_items['agenthw']:
                selected_items.append(f'AGENT_{str(level).upper()}')

        if test_items.get('link'):
            selected_items.append('LINK_T0')

        if test_items.get('evt') or test_items.get('evt_exit'):
            selected_items.append('EVT_EXIT')

    return ','.join(selected_items)

def run_test_item(test_item, profile_name, dry_run=False):
    """
    Execute a single test item from the profile.
    This simulates kicking off the actual test execution engine.
    In NUI, this might involve calling run_all_test.sh or using the TestExecutionManager.
    """
    test_title = test_item.get('title', 'Unknown Test')
    logger.info(f"[{profile_name}] Executing test: {test_title}")

    procedure = load_test_procedure(test_title)
    if not procedure:
        logger.error(f"[{profile_name}] Cannot execute '{test_title}' - procedure config missing")
        return False

    script = procedure.get('script')
    bin_file = procedure.get('bin')
    test_level = procedure.get('test_level')
    topology = procedure.get('topology')
    test_items = procedure.get('test_items')
    clean_fboss = bool(procedure.get('clean_fboss', False))

    if not script or not bin_file:
        logger.error(f"[{profile_name}] Procedure '{test_title}' missing required fields: script/bin")
        return False

    script_path = os.path.join(TEST_SCRIPT_DIR, script)
    if not os.path.exists(script_path):
        logger.error(f"[{profile_name}] Script not found for '{test_title}': {script_path}")
        return False

    cmd = ['bash', script_path, bin_file]

    if script in ('SAI_TX_test.sh', 'Agent_HW_T0_test.sh', 'Agent_HW_TX_test.sh'):
        if test_level:
            cmd.append(test_level)
    elif script in ('Link_T0_test.sh', 'Link_T1_test.sh', 'ExitEVT.sh'):
        if not topology:
            logger.error(f"[{profile_name}] Procedure '{test_title}' requires topology for script '{script}'")
            return False
        cmd.append(topology)
    elif script == 'run_all_test.sh':
        if not topology:
            logger.error(f"[{profile_name}] Procedure '{test_title}' requires topology for run_all_test.sh")
            return False
        cmd.append(topology)
        test_items_str = build_test_items_string(test_items)
        if test_items_str:
            cmd.append(test_items_str)

    if clean_fboss:
        if dry_run:
            logger.info(
                f"[{profile_name}] [DRY-RUN] Would clean /opt/fboss before '{test_title}'"
            )
        else:
            try:
                if os.path.exists('/opt/fboss'):
                    logger.info(f"[{profile_name}] Cleaning /opt/fboss before '{test_title}'")
                    subprocess.run(['rm', '-rf', '/opt/fboss'], timeout=10)
                else:
                    logger.info(f"[{profile_name}] /opt/fboss does not exist, skip clean before '{test_title}'")
            except Exception as e:
                logger.warning(f"[{profile_name}] Failed to clean /opt/fboss before '{test_title}': {e}")

    if dry_run:
        logger.info(
            f"[{profile_name}] [DRY-RUN] Would start '{test_title}' with command: {' '.join(cmd)}"
        )
        return True

    try:
        process = subprocess.Popen(
            cmd,
            cwd=TEST_SCRIPT_DIR,
            start_new_session=True
        )
        logger.info(
            f"[{profile_name}] Started '{test_title}' (PID={process.pid}) with command: {' '.join(cmd)}"
        )
        return process.pid
    except Exception as e:
        logger.error(f"[{profile_name}] Failed to execute '{test_title}': {e}")
        return False

def load_profile(profile_name):
    filepath = get_safe_profile_filepath(profile_name)
    if not filepath:
        logger.error(f"Invalid profile name: {profile_name}")
        return None

    if not os.path.exists(filepath):
        logger.error(f"Profile file not found: {filepath}")
        return None
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load profile {filepath}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description='Run a saved schedule profile and execute its test procedures.'
    )
    parser.add_argument('profile_name', help='Scheduled profile name (without .json)')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show planned execution (including commands/timing) without sleep or process launch'
    )
    args = parser.parse_args()

    profile_name = args.profile_name
    dry_run = args.dry_run

    logger.info(f"=== Starting scheduled execution for profile: '{profile_name}' ===")
    if dry_run:
        logger.info(f"=== DRY-RUN mode enabled for profile: '{profile_name}' ===")
    else:
        write_execution_status({
            'running': False,
            'profile_name': profile_name,
            'current_test_title': None,
            'pid': None
        })
    
    profile_data = load_profile(profile_name)
    if not profile_data:
        sys.exit(1)
        
    tests = profile_data.get('tests', [])
    if not tests:
        logger.info(f"No tests defined in profile '{profile_name}'. Exiting.")
        sys.exit(0)
        
    # In a full robust implementation, since the cron triggers at 00:00 (midnight),
    # this script would read the timeline start times of each test, and use the 'sched' module 
    # or background threading to sleep and trigger each test exactly when intended during the day.
    # For now, we simulate iterating over the tests to log their intended execution flow.
    logger.info(f"Profile '{profile_name}' contains {len(tests)} scheduled test procedures.")
    
    # Sort tests by their start time offset
    tests.sort(key=lambda t: t.get('startOffsetMinutes', 0))
    
    launched_count = 0

    for idx, test in enumerate(tests):
        title = test.get('title')
        start_offset = test.get('startOffsetMinutes', 0)
        duration = test.get('durationMinutes', 30)
        
        # Calculate intended execution time
        today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        intended_time = today_midnight + timedelta(minutes=start_offset)
        
        logger.info(f"[{idx+1}/{len(tests)}] Test '{title}' scheduled for {intended_time.strftime('%H:%M')} (Duration: {duration}m)")

        wait_seconds = (intended_time - datetime.now()).total_seconds()
        if dry_run and wait_seconds > 0:
            logger.info(f"[{profile_name}] [DRY-RUN] Would wait {int(wait_seconds)}s for '{title}' start time")
        elif wait_seconds > 0:
            logger.info(f"[{profile_name}] Waiting {int(wait_seconds)}s for '{title}' start time")
            time.sleep(wait_seconds)
        else:
            if dry_run:
                logger.info(f"[{profile_name}] [DRY-RUN] '{title}' start time already passed, would launch immediately")
            else:
                logger.info(f"[{profile_name}] '{title}' start time already passed, launching immediately")

        launch_result = run_test_item(test, profile_name, dry_run=dry_run)
        if launch_result:
            launched_count += 1
            if not dry_run:
                safe_pid = launch_result if isinstance(launch_result, int) and not isinstance(launch_result, bool) else None
                write_execution_status({
                    'running': True,
                    'profile_name': profile_name,
                    'current_test_title': title,
                    'pid': safe_pid
                })

    logger.info(
        f"=== Completed scheduled execution dispatch for profile: '{profile_name}'. "
        f"Launched {launched_count}/{len(tests)} tests ==="
    )

if __name__ == "__main__":
    main()
