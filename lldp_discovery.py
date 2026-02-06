import subprocess
import json
import re
from typing import Dict, List, Optional


def get_network_interfaces() -> List[str]:
    """Get list of available network interfaces."""
    try:
        result = subprocess.run(
            ['ip', '-o', 'link', 'show'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        interfaces = []
        for line in result.stdout.splitlines():
            # Parse interface name from ip link output
            # Format: 1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
            match = re.match(r'^\d+:\s+([^:]+):', line)
            if match:
                iface = match.group(1).strip()
                # Filter out loopback and virtual interfaces
                if not iface.startswith('lo') and not iface.startswith('vir'):
                    interfaces.append(iface)
        
        # If no interfaces found, return default
        return interfaces if interfaces else ['eth0']
    
    except Exception as e:
        print(f"Error getting network interfaces: {e}")
        return ['eth0']


def get_interface_mac(interface: str) -> str:
    """Get MAC address for a specific interface."""
    try:
        # Try using ip command first
        result = subprocess.run(
            ['ip', 'link', 'show', interface],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Parse MAC address from output
        # Format: link/ether 00:a0:c9:00:00:00 brd ff:ff:ff:ff:ff:ff
        for line in result.stdout.splitlines():
            if 'link/ether' in line or 'ether' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'ether' and i + 1 < len(parts):
                        mac = parts[i + 1]
                        # Ensure MAC has colons
                        if ':' in mac and len(mac) == 17:
                            return mac
        
        # Try ifconfig as fallback
        result = subprocess.run(
            ['ifconfig', interface],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Parse MAC from ifconfig output
        # Format: ether 00:a0:c9:00:00:00  txqueuelen 1000  (Ethernet)
        for line in result.stdout.splitlines():
            if 'ether' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'ether' and i + 1 < len(parts):
                        mac = parts[i + 1]
                        # Ensure MAC has colons
                        if ':' in mac and len(mac) == 17:
                            return mac
        
        return '00:00:00:00:00:01'
    
    except Exception as e:
        print(f"Error getting MAC address for {interface}: {e}")
        return '00:00:00:00:00:01'


def get_lldp_neighbors(interface: Optional[str] = None) -> Dict:
    """
    Get LLDP neighbors information.
    
    Args:
        interface: Specific interface to query, or None for all interfaces
    
    Returns:
        Dictionary containing topology information
    """
    try:
        # Try to get LLDP information using lldpcli
        if interface:
            cmd = ['lldpcli', 'show', 'neighbors', 'ports', interface, '-f', 'json']
        else:
            cmd = ['lldpcli', 'show', 'neighbors', '-f', 'json']
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            # Try alternative command format without interface
            result = subprocess.run(
                ['lldpcli', 'show', 'neighbors', '-f', 'json'],
                capture_output=True,
                text=True,
                timeout=10
            )
        
        if result.returncode == 0 and result.stdout:
            try:
                lldp_data = json.loads(result.stdout)
                topology = parse_lldp_data(lldp_data, interface)
                topology['using_mock_data'] = False
                return topology
            except json.JSONDecodeError:
                # If JSON parsing fails, try to parse text output
                topology = parse_lldp_text(result.stdout, interface)
                topology['using_mock_data'] = False
                return topology
        else:
            # Return mock data if LLDP is not available
            topology = get_mock_lldp_data(interface)
            topology['using_mock_data'] = True
            topology['mock_reason'] = 'LLDP command returned no data'
            return topology
    
    except FileNotFoundError:
        print("lldpcli not found, using mock data")
        topology = get_mock_lldp_data(interface)
        topology['using_mock_data'] = True
        topology['mock_reason'] = 'lldpcli command not found - install lldpd package'
        return topology
    except Exception as e:
        print(f"Error getting LLDP neighbors: {e}")
        topology = get_mock_lldp_data(interface)
        topology['using_mock_data'] = True
        topology['mock_reason'] = f'Error: {str(e)}'
        return topology


def get_lldp_debug_info(interface: Optional[str] = None) -> Dict:
    """
    Get raw LLDP debug information for troubleshooting.
    
    Args:
        interface: Specific interface to query, or None for all interfaces
    
    Returns:
        Dictionary containing raw LLDP data and debug information
    """
    debug_info = {
        'raw_output': {},
        'commands_tried': [],
        'errors': [],
        'lldp_available': False,
        'interface': interface or 'all',
        'installation_instructions': {}
    }
    
    # Try lldpcli JSON format
    try:
        if interface:
            cmd = ['lldpcli', 'show', 'neighbors', 'ports', interface, '-f', 'json']
        else:
            cmd = ['lldpcli', 'show', 'neighbors', '-f', 'json']
        
        debug_info['commands_tried'].append(' '.join(cmd))
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        debug_info['raw_output']['lldpcli_json'] = {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
        
        if result.returncode == 0 and result.stdout:
            debug_info['lldp_available'] = True
            try:
                debug_info['raw_output']['parsed_json'] = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                debug_info['errors'].append(f'JSON parse error: {str(e)}')
    
    except FileNotFoundError:
        debug_info['errors'].append('lldpcli command not found')
        debug_info['installation_instructions'] = {
            'centos_rhel': 'sudo yum install lldpd && sudo systemctl start lldpd && sudo systemctl enable lldpd',
            'ubuntu_debian': 'sudo apt-get update && sudo apt-get install lldpd && sudo systemctl start lldpd && sudo systemctl enable lldpd',
            'fedora': 'sudo dnf install lldpd && sudo systemctl start lldpd && sudo systemctl enable lldpd',
            'note': 'After installation, wait 30-60 seconds for LLDP to discover neighbors'
        }
    except Exception as e:
        debug_info['errors'].append(f'Error running lldpcli: {str(e)}')
    
    # Try lldpcli text format
    try:
        if interface:
            cmd = ['lldpcli', 'show', 'neighbors', 'ports', interface, 'details']
        else:
            cmd = ['lldpcli', 'show', 'neighbors', 'details']
        
        debug_info['commands_tried'].append(' '.join(cmd))
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        debug_info['raw_output']['lldpcli_text'] = {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    
    except Exception as e:
        debug_info['errors'].append(f'Error running lldpcli text: {str(e)}')
    
    # Get interface information
    try:
        cmd = ['ip', 'link', 'show']
        if interface:
            cmd.append(interface)
        
        debug_info['commands_tried'].append(' '.join(cmd))
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        debug_info['raw_output']['ip_link'] = {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    
    except Exception as e:
        debug_info['errors'].append(f'Error running ip link: {str(e)}')
    
    # Check if lldpd service is running
    try:
        result = subprocess.run(
            ['systemctl', 'status', 'lldpd'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        debug_info['raw_output']['lldpd_status'] = {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode,
            'running': 'active (running)' in result.stdout
        }
    
    except Exception as e:
        debug_info['errors'].append(f'Error checking lldpd status: {str(e)}')
    
    return debug_info


def safe_get_value(data, key, default=''):
    """Safely extract value from LLDP data which can be str, dict, or list."""
    if not data:
        return default
    value = data.get(key, default)
    if isinstance(value, dict):
        return value.get('value', default)
    elif isinstance(value, list) and len(value) > 0:
        if isinstance(value[0], dict):
            return value[0].get('value', default)
        return value[0]
    elif isinstance(value, str):
        return value
    return default


def parse_lldp_data(lldp_data: Dict, interface: Optional[str] = None) -> Dict:
    """Parse LLDP JSON data into topology format."""
    
    topology = {
        'nodes': [],
        'links': [],
        'local_system': {}
    }
    
    # Get real local system information first
    local_info = get_local_system_info()
    hostname = local_info.get('hostname', 'Local System')
    ip_addresses = local_info.get('ip_addresses', [])
    mgmt_ip = ip_addresses[0] if ip_addresses else ''
    
    # Try to get MAC address for the interface
    interface_to_check = interface if interface else 'eth0'
    mac_address = get_interface_mac(interface_to_check)
    
    # Set local system info with real data
    topology['local_system'] = {
        'name': hostname,
        'description': f'Local System ({interface_to_check})',
        'id': mac_address,
        'mgmt-ip': mgmt_ip
    }
    
    # Add local node
    local_node = {
        'id': 'local',
        'label': hostname,
        'type': 'local',
        'details': topology['local_system']
    }
    topology['nodes'].append(local_node)
    
    # Extract neighbor information from LLDP data
    if 'lldp' in lldp_data:
        lldp_info = lldp_data['lldp']
        
        # Get neighbor info from interfaces
        if 'interface' in lldp_info:
            interfaces = lldp_info['interface']
            
            # Handle case where interfaces might be a list or dict
            if isinstance(interfaces, list):
                # Each list item is a dict like {"eth0": {...}}
                # Process each item in the list
                for interface_entry in interfaces:
                    if isinstance(interface_entry, dict):
                        # Each entry is {"interface_name": {...neighbor_data...}}
                        for iface_name, iface_data in interface_entry.items():
                            # Filter by interface if specified
                            if interface and iface_name != interface:
                                continue
                            
                            # Process this neighbor
                            process_neighbor(iface_name, iface_data, topology)
            elif isinstance(interfaces, dict):
                # Single interface case: {"eth0": {...}}
                for iface_name, iface_data in interfaces.items():
                    # Filter by interface if specified
                    if interface and iface_name != interface:
                        continue
                    
                    # Check if iface_data is a list of neighbors or single neighbor
                    if isinstance(iface_data, list):
                        for neighbor in iface_data:
                            process_neighbor(iface_name, neighbor, topology)
                    else:
                        process_neighbor(iface_name, iface_data, topology)
    
    return topology


def process_neighbor(iface_name: str, iface_data: Dict, topology: Dict):
    """Helper function to process a single neighbor from LLDP data."""
    if 'chassis' in iface_data:
        remote_chassis = iface_data['chassis']
        
        # Handle case where chassis contains hostname as key
        # e.g., {"MINIPACK3N-TAICHUNG-DVT": {...actual_data...}}
        if isinstance(remote_chassis, dict) and not any(k in remote_chassis for k in ['id', 'descr', 'mgmt-ip']):
            # Chassis is wrapped with hostname, extract it
            for hostname_key, chassis_data in remote_chassis.items():
                if isinstance(chassis_data, dict):
                    remote_chassis = chassis_data
                    # Store the hostname if not in the data
                    if 'name' not in remote_chassis:
                        remote_chassis['name'] = hostname_key
                    break
        
        if isinstance(remote_chassis, list):
            remote_chassis = remote_chassis[0] if remote_chassis else {}
        
        remote_id = safe_get_value(remote_chassis, 'id', f'unknown-{iface_name}')
        remote_name = safe_get_value(remote_chassis, 'name', remote_id)
        
        # Get capability
        capability = remote_chassis.get('capability', [])
        if isinstance(capability, dict):
            capability = [capability.get('type', 'Unknown')]
        elif isinstance(capability, list):
            capability = [cap.get('type', str(cap)) if isinstance(cap, dict) else str(cap) for cap in capability]
        elif isinstance(capability, str):
            capability = [capability]
        
        # Get management IP (handle list or single value)
        mgmt_ip = safe_get_value(remote_chassis, 'mgmt-ip', '')
        if isinstance(mgmt_ip, list):
            mgmt_ip = mgmt_ip[0] if mgmt_ip else ''
        
        # Check if node already exists
        if not any(node['id'] == remote_id for node in topology['nodes']):
            remote_node = {
                'id': remote_id,
                'label': remote_name,
                'type': 'remote',
                'details': {
                    'name': remote_name,
                    'id': remote_id,
                    'description': safe_get_value(remote_chassis, 'descr', ''),
                    'mgmt-ip': mgmt_ip,
                    'capability': capability
                }
            }
            topology['nodes'].append(remote_node)
        
        # Add link
        port_info = iface_data.get('port', {})
        if isinstance(port_info, list):
            port_info = port_info[0] if port_info else {}
        remote_port = safe_get_value(port_info, 'descr', safe_get_value(port_info, 'id', 'unknown'))
        
        link = {
            'source': 'local',
            'target': remote_id,
            'local_port': iface_name,
            'remote_port': remote_port,
            'label': f"{iface_name} ↔ {remote_port}"
        }
        topology['links'].append(link)
    
    return topology


def parse_lldp_text(text_output: str, interface: Optional[str] = None) -> Dict:
    """Parse LLDP text output into topology format."""
    # Simplified text parsing - can be enhanced based on actual output format
    topology = {
        'nodes': [
            {
                'id': 'local',
                'label': 'Local System',
                'type': 'local',
                'details': {}
            }
        ],
        'links': [],
        'local_system': {}
    }
    
    # Basic text parsing logic can be added here
    return topology


def get_mock_lldp_data(interface: Optional[str] = None) -> Dict:
    """Return mock LLDP data for testing when lldpcli is not available."""
    # Get real local system information
    local_info = get_local_system_info()
    hostname = local_info.get('hostname', 'Local System')
    ip_addresses = local_info.get('ip_addresses', [])
    mgmt_ip = ip_addresses[0] if ip_addresses else '192.168.1.100'
    
    # Try to get MAC address for interface
    mac_address = get_interface_mac(interface or 'eth0')
    
    topology = {
        'nodes': [
            {
                'id': 'local',
                'label': hostname,
                'type': 'local',
                'details': {
                    'name': hostname,
                    'description': 'This is the local machine',
                    'id': mac_address,
                    'mgmt-ip': mgmt_ip
                }
            },
            {
                'id': 'distribution-switch',
                'label': 'Distribution',
                'type': 'remote',
                'details': {
                    'name': 'Distribution Switch',
                    'id': '00:00:00:00:00:02',
                    'description': 'Core Distribution Switch',
                    'mgmt-ip': '192.168.1.10',
                    'capability': ['Bridge', 'Router']
                }
            },
            {
                'id': 'west-router',
                'label': 'West Router',
                'type': 'remote',
                'details': {
                    'name': 'West Router',
                    'id': '00:00:00:00:00:03',
                    'description': 'Edge Router - West',
                    'mgmt-ip': '192.168.1.1',
                    'capability': ['Router']
                }
            },
            {
                'id': 'access-2nd',
                'label': 'Access 2nd',
                'type': 'remote',
                'details': {
                    'name': 'Access Switch 2',
                    'id': '00:00:00:00:00:04',
                    'description': 'Access Layer Switch - 2',
                    'mgmt-ip': '192.168.1.20',
                    'capability': ['Bridge']
                }
            }
        ],
        'links': [
            {
                'source': 'local',
                'target': 'distribution-switch',
                'local_port': interface or 'eth0',
                'remote_port': 'Gi 0/1',
                'label': f"{interface or 'eth0'} ↔ Gi 0/1"
            },
            {
                'source': 'distribution-switch',
                'target': 'west-router',
                'local_port': 'Gi 0/1',
                'remote_port': 'Gi 0/0',
                'label': 'Gi 0/1 ↔ Gi 0/0'
            },
            {
                'source': 'distribution-switch',
                'target': 'access-2nd',
                'local_port': 'Fa 0/1',
                'remote_port': 'Gi 0/1',
                'label': 'Fa 0/1 ↔ Gi 0/1'
            }
        ],
        'local_system': {
            'name': hostname,
            'description': 'This is the local machine',
            'id': mac_address,
            'mgmt-ip': mgmt_ip
        }
    }
    
    return topology


def get_local_system_info() -> Dict:
    """Get local system information."""
    try:
        # Try to get hostname
        hostname = subprocess.run(
            ['hostname'],
            capture_output=True,
            text=True,
            timeout=5
        ).stdout.strip()
        
        # Try to get IP addresses using ip command
        ip_result = subprocess.run(
            ['ip', '-4', '-o', 'addr', 'show'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        ip_addresses = []
        if ip_result.returncode == 0:
            # Parse IP addresses from output
            # Format: 2: eth0    inet 172.17.9.199/24 brd 172.17.11.255 scope global eth0\ ...
            for line in ip_result.stdout.splitlines():
                if 'inet' in line and 'scope global' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'inet' and i + 1 < len(parts):
                            ip_with_prefix = parts[i + 1]
                            ip = ip_with_prefix.split('/')[0]
                            ip_addresses.append(ip)
        
        # Fallback to hostname -I if no IPs found
        if not ip_addresses:
            ip_result = subprocess.run(
                ['hostname', '-I'],
                capture_output=True,
                text=True,
                timeout=5
            )
            ip_addresses = ip_result.stdout.strip().split() if ip_result.returncode == 0 else []
        
        return {
            'hostname': hostname,
            'ip_addresses': ip_addresses
        }
    except Exception as e:
        print(f"Error getting local system info: {e}")
        return {
            'hostname': 'localhost',
            'ip_addresses': []
        }


def configure_lldp_tx(interface: str, enable: bool = True) -> Dict:
    """
    Configure LLDP transmission on an interface.
    
    Args:
        interface: Interface name (e.g., 'eth0')
        enable: True to enable TX, False to disable
    
    Returns:
        Dictionary with status and message
    """
    try:
        if enable:
            # Enable TX and RX (correct syntax is rx-and-tx, not tx-and-rx)
            cmd = ['lldpcli', 'configure', 'ports', interface, 'lldp', 'status', 'rx-and-tx']
        else:
            # Disable TX, RX only
            cmd = ['lldpcli', 'configure', 'ports', interface, 'lldp', 'status', 'rx-only']
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return {
                'success': True,
                'message': f"LLDP TX {'enabled' if enable else 'disabled'} on {interface}",
                'interface': interface,
                'tx_enabled': enable
            }
        else:
            return {
                'success': False,
                'message': f"Failed to configure LLDP: {result.stderr}",
                'error': result.stderr
            }
    
    except Exception as e:
        return {
            'success': False,
            'message': f"Error configuring LLDP: {str(e)}",
            'error': str(e)
        }


def get_lldp_status(interface: Optional[str] = None) -> Dict:
    """
    Get LLDP configuration status and statistics.
    
    Args:
        interface: Interface to check (optional)
    
    Returns:
        Dictionary with LLDP status information including TX/RX status and statistics
    """
    try:
        # Get interface status to determine TX/RX state
        interfaces_cmd = ['lldpcli', 'show', 'interfaces']
        interfaces_result = subprocess.run(
            interfaces_cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        tx_enabled = False
        rx_enabled = False
        
        if interfaces_result.returncode == 0:
            # Parse interface output to find TX/RX status
            output = interfaces_result.stdout
            if interface:
                # Look for the specific interface section
                lines = output.split('\n')
                in_interface_section = False
                for line in lines:
                    if f'Interface:    {interface}' in line:
                        in_interface_section = True
                    elif in_interface_section:
                        if 'Administrative status:' in line:
                            status_line = line.lower()
                            if 'rx and tx' in status_line or 'tx and rx' in status_line:
                                tx_enabled = True
                                rx_enabled = True
                            elif 'rx' in status_line:
                                rx_enabled = True
                            elif 'tx' in status_line:
                                tx_enabled = True
                            break
                        elif 'Interface:' in line:
                            # Reached next interface
                            break
        
        # Get statistics
        tx_packets = 0
        rx_packets = 0
        
        if interface:
            stats_cmd = ['lldpcli', 'show', 'statistics', 'ports', interface]
        else:
            stats_cmd = ['lldpcli', 'show', 'statistics', 'summary']
        
        stats_result = subprocess.run(
            stats_cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if stats_result.returncode == 0:
            # Parse statistics output
            output = stats_result.stdout
            for line in output.split('\n'):
                if 'Transmitted:' in line:
                    try:
                        tx_packets = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif 'Received:' in line:
                    try:
                        rx_packets = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
        
        # Get neighbor count
        neighbor_count = 0
        if interface:
            neighbors_cmd = ['lldpcli', 'show', 'neighbors', 'ports', interface, '-f', 'json']
        else:
            neighbors_cmd = ['lldpcli', 'show', 'neighbors', '-f', 'json']
        
        neighbors_result = subprocess.run(
            neighbors_cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if neighbors_result.returncode == 0 and neighbors_result.stdout:
            try:
                neighbors_data = json.loads(neighbors_result.stdout)
                if 'lldp' in neighbors_data and 'interface' in neighbors_data['lldp']:
                    neighbor_count = len(neighbors_data['lldp']['interface'])
            except json.JSONDecodeError:
                pass
        
        return {
            'tx_enabled': tx_enabled,
            'rx_enabled': rx_enabled,
            'tx_packets': tx_packets,
            'rx_packets': rx_packets,
            'neighbor_count': neighbor_count,
            'lldp_running': True
        }
    
    except Exception as e:
        return {
            'tx_enabled': False,
            'rx_enabled': False,
            'tx_packets': 0,
            'rx_packets': 0,
            'neighbor_count': 0,
            'lldp_running': False,
            'error': str(e)
        }

