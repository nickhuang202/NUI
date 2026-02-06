"""
Port & Transceiver Routes Blueprint
Handles port status, transceiver information, and absent port detection.
"""

import os
import re
import subprocess
from flask import Blueprint, jsonify
from config.logging_config import get_logger

logger = get_logger(__name__)

# Create blueprint
port_bp = Blueprint('port', __name__, url_prefix='/api')


def is_process_running(name: str) -> bool:
    """Return True if a process matching `name` is running (uses pgrep -f)."""
    try:
        proc = subprocess.run(['pgrep', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc.returncode == 0
    except Exception:
        return False


def parse_fboss2_port_output(output):
    """Parse fboss2 show port output to extract port status."""
    port_status = {}
    lines = output.strip().split('\n')
    
    for line in lines:
        # Skip headers and separator lines
        if not line.strip() or line.startswith('-') or 'Interface' in line:
            continue
        
        # Parse port lines (format: ethX/Y/Z ...)
        if re.match(r'^\s*eth\d+/\d+/\d+', line):
            try:
                parts = re.split(r'\s+', line.strip())
                if len(parts) >= 2:
                    port_name = parts[0]
                    # Link state is typically in second column
                    link_state = parts[1] if len(parts) > 1 else 'Unknown'
                    port_status[port_name] = link_state
            except Exception as e:
                logger.warning(f"Error parsing port line: {line[:50]}... Error: {e}")
                continue
    
    return port_status


def parse_transceiver_output(content):
    """Parse fboss2 show transceiver table format output."""
    ports = []
    
    # Standards for 400G FR4
    TX_MIN_SAFE = -6.0
    TX_MAX_SAFE = 3.0
    RX_MIN_SAFE = -10.0
    RX_MAX_SAFE = 3.0
    
    try:
        lines = content.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines, headers, and separator lines
            if not line_stripped or line_stripped.startswith('-') or 'Interface' in line_stripped:
                continue
            
            # Check for port line (starts with ethX/Y/Z)
            if re.match(r'^\s*eth\d+/\d+/\d+', line):
                try:
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) < 6:
                        continue
                    
                    port_name = parts[0].strip()
                    status = parts[1].strip() if len(parts) > 1 else 'Unknown'
                    transceiver_type = parts[2].strip() if len(parts) > 2 else 'Unknown'
                    
                    # Skip absent ports
                    if transceiver_type == 'Absent' or status == 'Down':
                        continue
                    
                    # Extract data fields
                    vendor = parts[5].strip() if len(parts) > 5 else 'Unknown'
                    serial = parts[6].strip() if len(parts) > 6 else None
                    part_number = parts[7].strip() if len(parts) > 7 else None
                    fw_app_version = parts[8].strip() if len(parts) > 8 else None
                    fw_dsp_version = parts[9].strip() if len(parts) > 9 else None
                    
                    # Parse temperature
                    temperature = None
                    if len(parts) > 10:
                        try:
                            temperature = float(parts[10].strip())
                        except:
                            pass
                    
                    # Parse TX/RX power from later columns
                    tx_power_str = parts[13].strip() if len(parts) > 13 else 'N/A'
                    rx_power_str = parts[14].strip() if len(parts) > 14 else 'N/A'
                    
                    # Extract numeric values
                    tx_powers = []
                    rx_powers = []
                    
                    try:
                        if tx_power_str != 'N/A':
                            tx_values = re.findall(r'-?\d+\.\d+', tx_power_str)
                            tx_powers = [float(v) for v in tx_values]
                    except:
                        pass
                    
                    try:
                        if rx_power_str != 'N/A':
                            rx_values = re.findall(r'-?\d+\.\d+', rx_power_str)
                            rx_powers = [float(v) for v in rx_values]
                    except:
                        pass
                    
                    # Analyze power levels
                    status_level = 'good'
                    issues = []
                    
                    for i, tx in enumerate(tx_powers):
                        if tx < TX_MIN_SAFE or tx > TX_MAX_SAFE:
                            issues.append(f'TX Lane{i}: {tx:.2f}dBm out of range')
                            status_level = 'warning' if status_level == 'good' else 'critical'
                    
                    for i, rx in enumerate(rx_powers):
                        if rx < RX_MIN_SAFE or rx > RX_MAX_SAFE:
                            issues.append(f'RX Lane{i}: {rx:.2f}dBm out of range')
                            status_level = 'warning' if status_level == 'good' else 'critical'
                    
                    # Calculate averages and ranges
                    tx_avg = sum(tx_powers) / len(tx_powers) if tx_powers else None
                    rx_avg = sum(rx_powers) / len(rx_powers) if rx_powers else None
                    tx_range = (max(tx_powers) - min(tx_powers)) if tx_powers else None
                    rx_range = (max(rx_powers) - min(rx_powers)) if rx_powers else None
                    
                    ports.append({
                        'port': port_name,
                        'vendor': vendor,
                        'serial': serial,
                        'part_number': part_number,
                        'type': transceiver_type,
                        'temperature': temperature,
                        'tx_power': tx_powers,
                        'rx_power': rx_powers,
                        'tx_avg': tx_avg,
                        'rx_avg': rx_avg,
                        'tx_range': tx_range,
                        'rx_range': rx_range,
                        'fw_app_version': fw_app_version,
                        'fw_dsp_version': fw_dsp_version,
                        'status': status_level,
                        'issues': issues
                    })
                
                except Exception as e:
                    logger.warning(f"Error parsing transceiver line: {line[:50]}... Error: {e}")
                    continue
    
    except Exception as e:
        logger.error(f"Error in parse_transceiver_output: {e}")
    
    # Calculate summary
    summary = {'good': 0, 'warning': 0, 'critical': 0}
    for port in ports:
        summary[port['status']] = summary.get(port['status'], 0) + 1
    
    return {'ports': ports, 'summary': summary}


# ============================================================================
# Port Status Endpoints
# ============================================================================

@port_bp.route('/port_status')
def api_port_status():
    """Run fboss2 show port and return port LinkState mapping."""
    try:
        # Check if both services are running
        qsfp_running = is_process_running('qsfp_service')
        sai_running = is_process_running('sai_mono_link_test-sai_impl')
        
        if not (qsfp_running and sai_running):
            logger.info(f'[API] Services not running: qsfp={qsfp_running}, sai={sai_running}')
            return jsonify({'error': 'Services not running', 'ports': {}}), 503
        
        logger.info('[API] Running fboss2 show port...')
        # Run fboss2 show port
        proc = subprocess.run(['fboss2', 'show', 'port'], capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            logger.error(f'[API] fboss2 failed: {proc.stderr[:200]}')
            return jsonify({'error': f'fboss2 failed: {proc.stderr}', 'ports': {}}), 500
        
        logger.info(f'[API] fboss2 output length: {len(proc.stdout)}')
        port_status = parse_fboss2_port_output(proc.stdout)
        
        # Only save to file if output contains valid port data
        output_file = '/opt/fboss/fboss2_show_port.txt'
        if len(port_status) > 0 and len(proc.stdout.strip()) > 0:
            try:
                os.makedirs('/opt/fboss', exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(proc.stdout)
                logger.info(f'[API] Saved output to {output_file} ({len(port_status)} ports)')
            except Exception as e:
                logger.warning(f'[API] Could not save to {output_file}: {e}')
        else:
            logger.info('[API] Skipping save: output empty or no valid ports found')
        
        logger.info(f'[API] Returning {len(port_status)} ports')
        return jsonify({'ports': port_status})
    except FileNotFoundError:
        logger.error('[API] fboss2 not found')
        return jsonify({'error': 'fboss2 not found', 'ports': {}}), 404
    except subprocess.TimeoutExpired:
        logger.error('[API] fboss2 timeout')
        return jsonify({'error': 'fboss2 timeout', 'ports': {}}), 504
    except Exception as e:
        logger.error(f'[API] Exception: {e}')
        return jsonify({'error': str(e), 'ports': {}}), 500


# ============================================================================
# Transceiver Endpoints
# ============================================================================

@port_bp.route('/absent_ports')
def api_absent_ports():
    """Read fboss2 show transceivers output and return list of absent ports."""
    # Try multiple possible locations for the transceivers file
    possible_paths = [
        '/opt/fboss/fboss2_show_transceivers.txt',
        'fboss2_show_transceivers.txt',
        '../fboss2_show_transceivers.txt',
        'test_report/fboss2_show_transceivers.txt'
    ]
    
    output_file = None
    for path in possible_paths:
        if os.path.exists(path):
            output_file = path
            logger.info(f'[API] Found transceivers file at: {path}')
            break
    
    try:
        # If file doesn't exist, return empty absent ports list
        if not output_file:
            logger.info('[API] Transceivers file not found - treating all ports as present')
            return jsonify({'absentPorts': [], 'totalPorts': 0, 'info': 'No transceiver file found'})
        
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if not content or len(content) < 10:
            logger.info('[API] Transceivers file is empty')
            return jsonify({'absentPorts': [], 'totalPorts': 0, 'info': 'Transceiver file is empty'})
        
        # Parse the transceiver output to find absent ports
        absent_ports = []
        lines = content.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith('-') or 'Interface' in line_stripped:
                continue
            
            if re.match(r'^\s*eth\d+/\d+/\d+', line):
                try:
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) < 3:
                        continue
                    
                    port_name = parts[0].strip()
                    status = parts[1].strip() if len(parts) > 1 else 'Unknown'
                    transceiver_type = parts[2].strip() if len(parts) > 2 else 'Unknown'
                    
                    if transceiver_type == 'Absent' or status == 'Absent':
                        absent_ports.append(port_name)
                
                except Exception as e:
                    logger.warning(f'Error parsing line: {line[:50]}... Error: {e}')
                    continue
        
        logger.info(f'[API] Found {len(absent_ports)} absent ports')
        return jsonify({'absentPorts': absent_ports, 'totalPorts': len(absent_ports)})
        
    except Exception as e:
        logger.error(f'[API] Error reading absent ports: {e}')
        return jsonify({'absentPorts': [], 'error': str(e)}), 200


@port_bp.route('/present_transceivers')
def api_present_transceivers():
    """Read fboss2 show transceivers output and return list of present transceiver ports."""
    possible_paths = [
        '/opt/fboss/fboss2_show_transceivers.txt',
        'fboss2_show_transceivers.txt',
        '../fboss2_show_transceivers.txt',
        'test_report/fboss2_show_transceivers.txt'
    ]
    
    output_file = None
    for path in possible_paths:
        if os.path.exists(path):
            output_file = path
            logger.info(f'[API] Found transceivers file at: {path}')
            break
    
    try:
        if not output_file:
            logger.info('[API] Transceivers file not found')
            return jsonify({'presentPorts': [], 'totalPorts': 0, 'info': 'No transceiver file found'})
        
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if not content or len(content) < 10:
            logger.info('[API] Transceivers file is empty')
            return jsonify({'presentPorts': [], 'totalPorts': 0, 'info': 'Transceiver file is empty'})
        
        # Parse the transceiver output to find present ports
        present_ports = []
        lines = content.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith('-') or 'Interface' in line_stripped:
                continue
            
            if re.match(r'^\s*eth\d+/\d+/\d+', line):
                try:
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) < 3:
                        continue
                    
                    port_name = parts[0].strip()
                    transceiver_type = parts[2].strip() if len(parts) > 2 else 'Unknown'
                    
                    # Only include ports where transceiver is present (not Absent)
                    if transceiver_type != 'Absent':
                        present_ports.append(port_name)
                
                except Exception as e:
                    logger.warning(f'Error parsing line: {line[:50]}... Error: {e}')
                    continue
        
        logger.info(f'[API] Found {len(present_ports)} present transceivers')
        return jsonify({'presentPorts': present_ports, 'totalPorts': len(present_ports)})
        
    except Exception as e:
        logger.error(f'[API] Error reading present transceivers: {e}')
        return jsonify({'presentPorts': [], 'error': str(e)}), 200


@port_bp.route('/transceiver_info')
def api_transceiver_info():
    """Parse fboss2 show transceiver output and analyze TX/RX power levels."""
    possible_paths = [
        '/opt/fboss/fboss2_show_transceivers.txt',
        'fboss2_show_transceivers.txt',
        '../fboss2_show_transceivers.txt',
        'test_report/fboss2_show_transceivers.txt'
    ]
    
    output_file = None
    for path in possible_paths:
        if os.path.exists(path):
            output_file = path
            logger.info(f'[API] Found transceiver file at: {path}')
            break
    
    try:
        if not output_file:
            error_msg = f'File not found in any of these locations: {", ".join(possible_paths)}'
            logger.info(f'[API] {error_msg}')
            return jsonify({'ports': [], 'summary': {'good': 0, 'warning': 0, 'critical': 0}, 'error': error_msg}), 200
        
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if not content or len(content) < 10:
            logger.info('[API] File is empty or too small')
            return jsonify({'ports': [], 'summary': {'good': 0, 'warning': 0, 'critical': 0}, 'error': 'File is empty'}), 200
        
        logger.info(f'[API] Read {len(content)} bytes from {output_file}')
        
        # Parse the transceiver data
        transceiver_data = parse_transceiver_output(content)
        
        logger.info(f'[API] Parsed {len(transceiver_data.get("ports", []))} transceivers')
        return jsonify(transceiver_data)
        
    except Exception as e:
        logger.error(f'[API] Error reading transceiver info: {e}')
        return jsonify({'ports': [], 'summary': {'good': 0, 'warning': 0, 'critical': 0}, 'error': str(e)}), 500
