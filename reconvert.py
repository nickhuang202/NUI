#!/usr/bin/env python3
"""
Script to generate FBOSS config for multiple platforms
Enhanced version with topology integration and profile mapping
Supports: minipack3ba, minipack3n, wedge800bact, wedge800cact
"""

import subprocess
import json
import os
import csv
import sys

# Get the script directory for relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ======================
# QSFP Test Configs
# ======================
QSFP_TEST_CONFIGS = {
    "MINIPACK3BA": {
        "dir": os.path.join(SCRIPT_DIR, "qsfp_test_configs/MINIPACK3BA"),
        "file": "montblanc.materialized_JSON",
        "url": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/qsfp_test_configs/montblanc.materialized_JSON",
        "required": True
    },
    "MINIPACK3N": {
        "dir": os.path.join(SCRIPT_DIR, "qsfp_test_configs/MINIPACK3N"),
        "file": "minipack3n.materialized_JSON",
        "url": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/qsfp_test_configs/minipack3n.materialized_JSON",
        "required": True
    },
    "WEDGE800BACT": {
        "dir": os.path.join(SCRIPT_DIR, "qsfp_test_configs/WEDGE800BACT"),
        "file": "wedge800bact.materialized_JSON",
        "url": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/qsfp_test_configs/wedge800bact.materialized_JSON",
        "required": False,  # File not available in upstream repo
        "note": "Not available in upstream repo, skip download"
    }
}

def ensure_qsfp_test_configs():
    """
    Ensure qsfp_test_configs directory structure exists and files are downloaded
    """
    print("\n" + "="*70)
    print("Checking QSFP Test Configs")
    print("="*70)
    
    for platform, config in QSFP_TEST_CONFIGS.items():
        dir_path = config["dir"]
        file_path = os.path.join(dir_path, config["file"])
        url = config["url"]
        required = config.get("required", True)
        note = config.get("note", "")
        
        # Create directory if not exists
        if not os.path.exists(dir_path):
            print(f"\n[{platform}] Creating directory: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
        
        # Check if file exists
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            if file_size > 100:  # Valid file should be larger than 100 bytes
                print(f"[{platform}] ✓ File exists: {config['file']} ({file_size} bytes)")
            else:
                # File exists but too small, likely a 404 error page
                print(f"[{platform}] ✗ File corrupted (only {file_size} bytes)")
                if not required:
                    print(f"[{platform}] ⚠ {note}")
                    continue
                os.remove(file_path)
                print(f"[{platform}] Removed corrupted file, will re-download...")
        
        # Download if file doesn't exist or was corrupted
        if not os.path.exists(file_path):
            if not required:
                print(f"[{platform}] ⚠ File not found: {config['file']}")
                print(f"[{platform}] ⚠ {note}")
                continue
                
            print(f"[{platform}] ✗ File not found: {config['file']}")
            print(f"[{platform}] Downloading from GitHub...")
            
            try:
                # Use curl to download
                result = subprocess.run(
                    ["curl", "-L", "-o", file_path, url],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0 and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    if file_size > 100:
                        print(f"[{platform}] ✓ Downloaded successfully ({file_size} bytes)")
                    else:
                        print(f"[{platform}] ✗ Download failed (file too small: {file_size} bytes)")
                        os.remove(file_path)
                else:
                    print(f"[{platform}] ✗ Download failed: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print(f"[{platform}] ✗ Download timeout")
            except Exception as e:
                print(f"[{platform}] ✗ Error: {e}")
    
    print("\n" + "="*70)

# ======================
# Platform Configuration
# ======================
PLATFORMS = {
    "minipack3ba": {
        "local": {
            "config": "/home/NUI/link_test_configs/MINIPACK3BA/montblanc.materialized_JSON",
            "csv": "/home/NUI/Topology/MINIPACK3BA/montblanc_port_profile_mapping.csv",
            "topology": "/home/NUI/Topology/MINIPACK3BA/montblanc.materialized_JSON"
        },
        "urls": {
            "config": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/montblanc.materialized_JSON",
            "csv": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/lib/platform_mapping_v2/platforms/montblanc/montblanc_port_profile_mapping.csv",
            "topology": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/montblanc.materialized_JSON"
        },
        "output": "montblanc.materialized_JSON.tmp"
    },
    "minipack3n": {
        "local": {
            "config": "/home/NUI/link_test_configs/MINIPACK3N/minipack3n.materialized_JSON",
            "csv": "/home/NUI/Topology/MINIPACK3N/minipack3n_port_profile_mapping.csv",
            "topology": "/home/NUI/Topology/MINIPACK3N/minipack3n.materialized_JSON"
        },
        "urls": {
            "config": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/minipack3n.materialized_JSON",
            "csv": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/lib/platform_mapping_v2/platforms/minipack3n/minipack3n_port_profile_mapping.csv",
            "topology": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/minipack3n.materialized_JSON"
        },
        "output": "minipack3n.materialized_JSON.tmp"
    },
    "wedge800bact": {
        "local": {
            "config": os.path.join(SCRIPT_DIR, "link_test_configs/WEDGE800BACT/wedge800bact.materialized_JSON"),
            "csv": os.path.join(SCRIPT_DIR, "Topology/WEDGE800BACT/wedge800bact_port_profile_mapping.csv"),
            "topology": os.path.join(SCRIPT_DIR, "Topology/WEDGE800BACT/wedge800bact.materialized_JSON")
        },
        "urls": {
            "config": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/wedge800bact.materialized_JSON",
            "csv": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/lib/platform_mapping_v2/platforms/wedge800bact/wedge800bact_port_profile_mapping.csv",
            "topology": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/wedge800bact.materialized_JSON"
        },
        "output": "wedge800bact.materialized_JSON.tmp"
    },
    "wedge800cact": {
        "local": {
            "config": "/home/NUI/link_test_configs/WEDGE800CACT/wedge800bact.materialized_JSON",
            "csv": "/home/NUI/Topology/WEDGE800CACT/wedge800bact_port_profile_mapping.csv",
            "topology": "/home/NUI/Topology/WEDGE800CACT/wedge800bact.materialized_JSON"
        },
        "urls": {
            "config": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/wedge800bact.materialized_JSON",
            "csv": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/lib/platform_mapping_v2/platforms/wedge800bact/wedge800bact_port_profile_mapping.csv",
            "topology": "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/wedge800bact.materialized_JSON"
        },
        "output": "wedge800cact.materialized_JSON.tmp"
    }
}

THRIFT_FILE = os.path.join(SCRIPT_DIR, "fboss_src/switch_config.thrift")

def download_file(url, output_file):
    """Download file using curl -O"""
    print(f"  Downloading from URL...")
    result = subprocess.run(["curl", "-o", output_file, url], capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Error downloading file: {result.stderr}")
    print(f"  Downloaded successfully to {output_file}")

def get_file(local_path, url, temp_file):
    """
    Get file from local path or download from URL
    Priority: local file > download from URL
    Returns: path to the file to use
    """
    print(f"Checking file: {os.path.basename(local_path)}")
    
    # Check if local file exists
    if os.path.exists(local_path):
        print(f"  [OK] Using local file: {local_path}")
        return local_path
    else:
        print(f"  [X] Local file not found: {local_path}")
        download_file(url, temp_file)
        
        # Also save a copy to the target location for future use
        try:
            target_dir = os.path.dirname(local_path)
            os.makedirs(target_dir, exist_ok=True)
            
            with open(temp_file, 'r') as src:
                content = src.read()
            with open(local_path, 'w') as dst:
                dst.write(content)
            
            print(f"  Saved a copy to: {local_path}")
        except Exception as e:
            print(f"  Warning: Could not save copy to {local_path}: {e}")
        
        return temp_file

def parse_csv_mapping(csv_file):
    """Parse CSV and extract port name to logical port ID and Port_Type mapping"""
    port_mapping = {}
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            port_name = row['Port_Name']
            logical_id = int(row['Logical_PortID'])
            port_type = int(row.get('Port_Type', 0))  # Default to 0 if not present
            port_mapping[port_name] = {
                'logical_id': logical_id,
                'port_type': port_type
            }
    return port_mapping

def parse_profile_speed_mapping(thrift_file):
    """Parse switch_config.thrift to extract profile ID to speed and lane count mapping"""
    profile_speed_map = {}
    profile_lane_map = {}  # New: track lane count per profile
    
    try:
        with open(thrift_file, 'r') as f:
            content = f.read()
            
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'cfg::PortProfileID' in line or 'PROFILE_' in line:
                if '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        profile_id = parts[1].strip().rstrip(',').strip()
                        if profile_id.isdigit():
                            pid = int(profile_id)
                            
                            # Extract speed
                            if '800G' in line or '800g' in line.lower():
                                profile_speed_map[pid] = 800000
                            elif '400G' in line or '400g' in line.lower():
                                profile_speed_map[pid] = 400000
                            elif '200G' in line or '200g' in line.lower():
                                profile_speed_map[pid] = 200000
                            elif '100G' in line or '100g' in line.lower():
                                profile_speed_map[pid] = 100000
                            elif '50G' in line or '50g' in line.lower():
                                profile_speed_map[pid] = 50000
                            elif '25G' in line or '25g' in line.lower():
                                profile_speed_map[pid] = 25000
                            elif '10G' in line or '10g' in line.lower():
                                profile_speed_map[pid] = 10000
                            
                            # Extract lane count from profile name (e.g., PROFILE_200G_4_PAM4 -> 4 lanes)
                            import re
                            match = re.search(r'PROFILE_\d+G_(\d+)_', line)
                            if match:
                                lane_count = int(match.group(1))
                                profile_lane_map[pid] = lane_count
    except Exception as e:
        print(f"Warning: Could not parse thrift file: {e}")
    
    # Fallback default mappings
    default_mappings = {
        39: 800000, 38: 400000, 37: 200000, 36: 100000,
        25: 200000, 23: 100000, 47: 200000, 22: 50000,
        21: 25000, 20: 10000, 24: 200000, 45: 400000,
        50: 800000, 54: 200000, 55: 100000,
    }
    
    # Default lane count mappings
    default_lane_mappings = {
        39: 8,  # 800G_8_PAM4
        38: 4,  # 400G_4_PAM4
        25: 4,  # 200G_4_PAM4
        23: 4,  # 100G_4_NRZ
        47: 1,  # 100G_1_PAM4
        24: 4,  # 200G_4_PAM4_COPPER
        45: 4,  # 400G_4_PAM4_COPPER
        50: 8,  # 800G_8_PAM4_COPPER
        54: 2,  # 200G_2_PAM4_COPPER
        55: 2,  # 100G_2_PAM4_COPPER
    }
    
    for pid, speed in default_mappings.items():
        if pid not in profile_speed_map:
            profile_speed_map[pid] = speed
    
    for pid, lanes in default_lane_mappings.items():
        if pid not in profile_lane_map:
            profile_lane_map[pid] = lanes
    
    return profile_speed_map, profile_lane_map

def load_topology(topology_file):
    """Load topology file and extract interface information"""
    with open(topology_file, 'r') as f:
        topology = json.load(f)
    
    interfaces_info = {}
    
    if "pimInfo" in topology and len(topology["pimInfo"]) > 0:
        pim = topology["pimInfo"][0]
        if "interfaces" in pim:
            for port_name, port_info in pim["interfaces"].items():
                interfaces_info[port_name] = {
                    "neighbor": port_info.get("neighbor", ""),
                    "profileID": port_info.get("profileID", 38),
                    "hasTransceiver": port_info.get("hasTransceiver", True)
                }
    
    return interfaces_info

def count_connections(topology_info):
    """
    Count unique connections (neighbor pairs) from topology.
    Each connection is counted once even though it appears twice (bidirectional).
    """
    seen_pairs = set()
    connection_count = 0
    
    for port_name, port_info in topology_info.items():
        neighbor = port_info.get("neighbor", "")
        if neighbor:  # Only count ports with neighbors
            # Create a normalized pair (sorted tuple) to avoid counting both directions
            pair = tuple(sorted([port_name, neighbor]))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                connection_count += 1
    
    return connection_count

def get_lane_suffixes_for_speed(speed, lane_count=None):
    """
    Determine which lane suffixes to use based on speed and lane count
    
    Lane count indicates how many physical lanes the profile uses:
    - 8 lanes: only /1 (full port)
    - 4 lanes: /1, /5 (2 breakout ports)
    - 2 lanes: /1, /3, /5, /7 (4 breakout ports) 
    - 1 lane: /1, /2, /3, /4, /5, /6, /7, /8 (8 breakout ports)
    
    Examples:
    - 800G_8_PAM4 (8 lanes): only /1
    - 400G_4_PAM4 (4 lanes): /1, /5
    - 200G_4_PAM4 (4 lanes): /1, /5 (NOT /1,/3,/5,/7)
    - 100G_4_NRZ (4 lanes): /1, /5
    - 100G_2_PAM4 (2 lanes): /1, /3, /5, /7
    - 50G_1_PAM4 (1 lane): /1, /2, /3, /4, /5, /6, /7, /8
    """
    # If lane_count is provided, use it to determine breakout
    if lane_count is not None:
        if lane_count == 8:
            return [1]
        elif lane_count == 4:
            return [1, 5]
        elif lane_count == 2:
            return [1, 3, 5, 7]
        elif lane_count == 1:
            return [1, 2, 3, 4, 5, 6, 7, 8]
    
    # Fallback to speed-based logic (with corrected mappings)
    if speed == 800000:
        return [1]  # 800G uses 8 lanes
    elif speed == 400000:
        return [1, 5]  # 400G typically uses 4 lanes (2 breakout)
    elif speed == 200000:
        return [1, 5]  # 200G uses 4 lanes (2 breakout), NOT 4 breakout!
    elif speed == 100000:
        return [1, 5]  # 100G typically uses 4 lanes (2 breakout)
    else:
        return [1, 5]

def generate_port_names_with_topology(topology_info, profile_speed_map, profile_lane_map, platform=None):
    """
    Generate port names based on topology and speed requirements
    For minipack3n: Follow topology file order for port generation
    For wedge800bact: Use actual lanes from topology (not speed-based)
    For other platforms: Process ports 1-64 in order with profile-based lane count
    If port not in topology: create eth1/x/1 with profile 39, speed 800000, state 1
    """
    port_names = []
    port_info_map = {}
    processed_base_ports = set()
    
    # For minipack3n, process ports in topology order; for others, use port number order
    if platform == "minipack3n":
        # First, process ports in topology order (maintaining the order from topology file)
        for port_name in topology_info.keys():
            # Skip service ports (port 65) for now, will add them at the end
            if '/65/' in port_name:
                continue
                
            # Extract base port number (e.g., eth1/35/1 -> 35)
            parts = port_name.split('/')
            if len(parts) == 3 and parts[0] == 'eth1':
                port_num = int(parts[1])
                lane = int(parts[2])
                base_port = f"eth1/{port_num}/1"
                
                # Only process each base port once
                if base_port in processed_base_ports:
                    continue
                processed_base_ports.add(base_port)
                
                # Get port configuration
                topo_info = topology_info[base_port]
                profile_id = topo_info['profileID']
                speed = profile_speed_map.get(profile_id, 400000)
                lane_count = profile_lane_map.get(profile_id, None)
                state = 2  # Normal state
                
                lane_suffixes = get_lane_suffixes_for_speed(speed, lane_count)
                
                for lane in lane_suffixes:
                    full_port_name = f"eth1/{port_num}/{lane}"
                    port_names.append(full_port_name)
                    
                    if full_port_name in topology_info:
                        port_info_map[full_port_name] = topology_info[full_port_name]
                    else:
                        port_info_map[full_port_name] = topo_info
                
                print(f"Port eth1/{port_num}: Speed={speed}, Lanes={lane_suffixes}, ProfileID={profile_id}, State=2")
        
        # Then, add any missing ports (1-64) that are not in topology
        for x in range(1, 65):
            base_port = f"eth1/{x}/1"
            
            if base_port not in processed_base_ports:
                # Port NOT in topology - create default 800G port with state 1
                port_name = base_port
                port_names.append(port_name)
                
                # Create default info for missing port
                port_info_map[port_name] = {
                    "neighbor": "",
                    "profileID": 39,  # Default to profile 39 (800G)
                    "hasTransceiver": True,
                    "state": 1  # Disabled state
                }
                
                print(f"Port eth1/{x}: NOT in topology - Creating default (Speed=800000, Lanes=[1], ProfileID=39, State=1)")
    else:
        # For other platforms: Process ports based on platform
        # WEDGE800BACT: 1-32 ports (+ service port 33), other platforms: 1-64 ports
        max_port = 33 if platform == "wedge800bact" else 65
        for x in range(1, max_port):
            base_port = f"eth1/{x}/1"
            
            if base_port in topology_info:
                # Port exists in topology - use topology configuration
                topo_info = topology_info[base_port]
                profile_id = topo_info['profileID']
                speed = profile_speed_map.get(profile_id, 400000)
                lane_count = profile_lane_map.get(profile_id, None)
                state = 2  # Normal state
                
                # For WEDGE800BACT: Check which lanes actually exist in topology
                # Instead of using speed-based lane generation
                if platform == "wedge800bact":
                    # Find all lanes for this port that exist in topology
                    actual_lanes = []
                    for lane in [1, 2, 3, 4, 5, 6, 7, 8]:
                        check_port = f"eth1/{x}/{lane}"
                        if check_port in topology_info:
                            actual_lanes.append(lane)
                    
                    lane_suffixes = actual_lanes if actual_lanes else [1]
                else:
                    # For other platforms, use profile-based lane generation
                    lane_suffixes = get_lane_suffixes_for_speed(speed, lane_count)
                
                for lane in lane_suffixes:
                    port_name = f"eth1/{x}/{lane}"
                    port_names.append(port_name)
                    
                    if port_name in topology_info:
                        port_info_map[port_name] = topology_info[port_name]
                    else:
                        port_info_map[port_name] = topo_info
                
                print(f"Port eth1/{x}: Speed={speed}, Lanes={lane_suffixes}, ProfileID={profile_id}, State=2")
            else:
                # Port NOT in topology - create default 800G port with state 1
                port_name = base_port
                port_names.append(port_name)
                
                # Create default info for missing port
                port_info_map[port_name] = {
                    "neighbor": "",
                    "profileID": 39,  # Default to profile 39 (800G)
                    "hasTransceiver": True,
                    "state": 1  # Disabled state
                }
                
                print(f"Port eth1/{x}: NOT in topology - Creating default (Speed=800000, Lanes=[1], ProfileID=39, State=1)")
    
    # Add service port
    if platform == "wedge800bact":
        # For wedge800bact: add eth1/33/1 as service port (logicalID=351)
        service_port_name = "eth1/33/1"
        port_names.append(service_port_name)
        if service_port_name in topology_info:
            port_info_map[service_port_name] = topology_info[service_port_name]
            profile_id = topology_info[service_port_name]["profileID"]
            speed = profile_speed_map.get(profile_id, 100000)
            print(f"Port eth1/33 (Service): Speed={speed}, Lanes=[1], ProfileID={profile_id}, State=2")
        else:
            port_info_map[service_port_name] = {
                "neighbor": "eth1/33/1",
                "profileID": 23,
                "hasTransceiver": True,
                "state": 2
            }
            print(f"Port eth1/33 (Service): Default config (Speed=100000, Lanes=[1], ProfileID=23, State=2)")
    elif platform == "minipack3n":
        # For minipack3n: check topology for all lanes
        service_port_lanes = []
        for lane in [1, 2, 3, 4, 5, 6, 7, 8]:
            port_name = f"eth1/65/{lane}"
            if port_name in topology_info:
                service_port_lanes.append(lane)
                port_names.append(port_name)
                port_info_map[port_name] = topology_info[port_name]
        
        # If no service port found in topology, create default eth1/65/1
        if not service_port_lanes:
            port_names.append("eth1/65/1")
            port_info_map["eth1/65/1"] = {
                "neighbor": "eth1/65/1",
                "profileID": 23,
                "hasTransceiver": True,
                "state": 2
            }
            service_port_lanes = [1]
            print(f"Port eth1/65 (Service): Default config (Speed=100000, Lanes=[1], ProfileID=23, State=2)")
        else:
            # Get profile from first service port lane
            first_lane_port = f"eth1/65/{service_port_lanes[0]}"
            profile_id = topology_info[first_lane_port]["profileID"]
            speed = profile_speed_map.get(profile_id, 100000)
            lane_count = profile_lane_map.get(profile_id, None)
            print(f"Port eth1/65 (Service): Speed={speed}, Lanes={service_port_lanes}, ProfileID={profile_id}, State=2")
    else:
        # For other platforms: always use /1 only
        port_names.append("eth1/65/1")
        if "eth1/65/1" in topology_info:
            port_info_map["eth1/65/1"] = topology_info["eth1/65/1"]
            profile_id = topology_info["eth1/65/1"]["profileID"]
            speed = profile_speed_map.get(profile_id, 100000)
            lane_count = profile_lane_map.get(profile_id, None)
            print(f"Port eth1/65 (Service): Speed={speed}, Lanes=[1], ProfileID={profile_id}, State=2")
        else:
            port_info_map["eth1/65/1"] = {
                "neighbor": "eth1/65/1",
                "profileID": 23,
                "hasTransceiver": True,
                "state": 2
            }
            print(f"Port eth1/65 (Service): Default config (Speed=100000, Lanes=[1], ProfileID=23, State=2)")
    
    return port_names, port_info_map

def create_port_object(logical_id, port_name, ingress_vlan, speed, profile_id, neighbor, state=2, is_service_port=False, platform=None, port_type=None):
    """Create port object from template"""
    # For minipack3n, always use ingressVlan = 0
    # For wedge800bact, use the passed ingress_vlan value (starts from 2033)
    if platform == "minipack3n":
        ingress_vlan = 0
    
    # Determine portType: use provided port_type from CSV, fallback to legacy logic
    if port_type is not None:
        # Use Port_Type from CSV mapping
        final_port_type = port_type
    elif is_service_port or logical_id == 351:
        # Legacy: service ports use portType 4
        final_port_type = 4
    else:
        # Default to 0
        final_port_type = 0
    
    port_obj = {
        "logicalID": logical_id,
        "state": state,  # Use dynamic state (1=disabled, 2=enabled)
        "minFrameSize": 64,
        "maxFrameSize": 9412,
        "parserType": 1,
        "routable": True,
        "ingressVlan": ingress_vlan,
        "speed": speed,
        "name": port_name,
        "description": "",
        "queues_DEPRECATED": [],
        "pause": {"tx": False, "rx": False},
        "sFlowIngressRate": 0,
        "sFlowEgressRate": 0,
        "loopbackMode": 0,
        "expectedLLDPValues": {},
        "lookupClasses": [],
        "profileID": profile_id,
        "portType": final_port_type,
        "expectedNeighborReachability": [],
        "drainState": 0,
        "scope": 0,
        "conditionalEntropyRehash": False,
    }
    
    if neighbor:
        port_obj["expectedLLDPValues"]["2"] = neighbor
    
    return port_obj

def create_vlan_object(vlan_id):
    """Create VLAN object from template"""
    return {
        "name": f"vlan{vlan_id}",
        "id": vlan_id,
        "recordStats": True,
        "routable": True,
        "ipAddresses": []
    }

def create_vlanport_object(vlan_id, logical_port):
    """Create VLAN port object from template"""
    return {
        "vlanID": vlan_id,
        "logicalPort": logical_port,
        "spanningTreeState": 2,
        "emitTags": False
    }

def create_interface_object(vlan_id, ipv6_addr, ipv4_addr, platform=None, port_id=None):
    """Create interface object from template"""
    # For minipack3n, always use vlanID = 0
    # For wedge800bact, use the provided vlan_id (2033+)
    if platform == "minipack3n":
        interface_vlan_id = 0
    else:
        interface_vlan_id = vlan_id
    
    # For minipack3n and wedge800bact, set isVirtual to false
    is_virtual = False if platform in ["minipack3n", "wedge800bact"] else True
    
    # For minipack3n, set type to 3; for wedge800bact, set type to 1
    if platform == "minipack3n":
        interface_type = 3
    else:
        interface_type = 1
    
    interface_obj = {
        "intfID": vlan_id,
        "routerID": 0,
        "vlanID": interface_vlan_id,
        "ipAddresses": [ipv6_addr, ipv4_addr],
        "mtu": 9000,
        "isVirtual": is_virtual,
        "isStateSyncDisabled": True,
        "type": interface_type,
        "scope": 0
    }
    
    # For minipack3n, add portID field (wedge800bact doesn't need it)
    if platform == "minipack3n" and port_id is not None:
        interface_obj["portID"] = port_id
    
    return interface_obj

def generate_config(platform, custom_config_name=None):
    """
    Generate FBOSS config for a specific platform
    
    Args:
        platform: Platform name (e.g., 'minipack3ba', 'minipack3n', 'wedge800bact', 'wedge800cact')
        custom_config_name: Optional custom config file name to use from link_test_configs/{platform}/
                           If specified and exists, will copy it as base template
    """
    
    platform_config = PLATFORMS[platform]
    topology_file_path = platform_config["local"]["topology"]
    output_file = platform_config["output"]
    
    # Temporary file names for downloaded files
    temp_config = "temp_config.json"
    temp_csv = "temp_mapping.csv"
    temp_topology = "temp_topology.json"
    
    try:
        # Check if custom config file is specified
        if custom_config_name:
            print("\n" + "="*70)
            print("Step 0: Checking custom config file")
            print("="*70)
            
            # Build path to custom config file
            custom_config_dir = os.path.join(SCRIPT_DIR, f"link_test_configs/{platform.upper()}")
            custom_config_path = os.path.join(custom_config_dir, custom_config_name)
            
            print(f"Looking for custom config: {custom_config_name}")
            print(f"Search path: {custom_config_path}")
            
            if os.path.exists(custom_config_path):
                # Copy custom config as base template
                base_template = f"{platform}.materialized_JSON"
                print(f"  [OK] Found custom config file")
                print(f"  Copying to base template: {base_template}")
                
                try:
                    import shutil
                    shutil.copy2(custom_config_path, base_template)
                    print(f"  [OK] Base template created from: {custom_config_name}")
                    # Use this as the config file
                    config_file = base_template
                except Exception as e:
                    print(f"  [ERROR] Failed to copy file: {e}")
                    print(f"  Falling back to default config")
                    config_file = None
            else:
                print(f"  [X] Custom config file not found: {custom_config_path}")
                print(f"  Falling back to default config")
                config_file = None
        else:
            config_file = None
        
        # Get files (local or download)
        print("\n" + "="*70)
        print("Step 1: Loading required files")
        print("="*70)
        
        if not config_file:
            config_file = get_file(
                platform_config["local"]["config"],
                platform_config["urls"]["config"],
                temp_config
            )
        
        csv_file = get_file(
            platform_config["local"]["csv"],
            platform_config["urls"]["csv"],
            temp_csv
        )
        
        topology_file = get_file(
            platform_config["local"]["topology"],
            platform_config["urls"]["topology"],
            temp_topology
        )
        
        # Load topology information
        print("\n" + "="*70)
        print("Step 2: Loading topology and profile mappings")
        print("="*70)
        
        topology_info = load_topology(topology_file)
        print(f"Loaded topology info for {len(topology_info)} interfaces")
        
        # Count unique connections for ecmp_width calculation
        connection_count = count_connections(topology_info)
        ecmp_width = connection_count * 2
        print(f"Counted {connection_count} unique connections")
        print(f"Calculated ecmp_width: {ecmp_width} (connections × 2)")
        
        profile_speed_map, profile_lane_map = parse_profile_speed_mapping(THRIFT_FILE)
        print(f"Loaded {len(profile_speed_map)} profile speed mappings and {len(profile_lane_map)} lane mappings")
        
        # Read and parse JSON config
        with open(config_file, 'r') as f:
            config = json.load(f)
        print("Config parsed successfully")
        
        # Initialize defaultCommandLineArgs if not present
        if "defaultCommandLineArgs" not in config:
            config["defaultCommandLineArgs"] = {}
        
        # Add common parameters for all platforms
        config["defaultCommandLineArgs"]["enable_1to1_intf_route_table_mapping"] = "true"
        config["defaultCommandLineArgs"]["remediation_enabled"] = "true"
        config["defaultCommandLineArgs"]["ecmp_width"] = str(ecmp_width)
        print(f"Added enable_1to1_intf_route_table_mapping and ecmp_width={ecmp_width} to defaultCommandLineArgs")
        
        # Add remediation_enabled for wedge800bact
        if platform == "wedge800bact":
            config["defaultCommandLineArgs"]["remediation_enabled"] = "true"
            print("Added remediation_enabled to defaultCommandLineArgs for wedge800bact")
        
        # Parse CSV mapping
        port_mapping = parse_csv_mapping(csv_file)
        print(f"Loaded {len(port_mapping)} port mappings from CSV")
        
        # Remove specified objects
        print("\n" + "="*70)
        print("Step 3: Cleaning existing configuration")
        print("="*70)
        
        if "sw" in config:
            objects_to_remove = ["ports", "vlans", "vlanPorts", "interfaces"]
            for obj in objects_to_remove:
                if obj in config["sw"]:
                    del config["sw"][obj]
                    print(f"Removed ['sw']['{obj}']")
        else:
            config["sw"] = {}
        
        # Generate port names
        print("\n" + "="*70)
        print("Step 4: Generating port configurations")
        print("="*70)
        
        port_names, port_info_map = generate_port_names_with_topology(topology_info, profile_speed_map, profile_lane_map, platform)
        print(f"\nTotal ports to create: {len(port_names)}")
        
        # Initialize objects
        ports = []
        vlans = []
        vlan_ports = []
        interfaces = []
        
        vlan_id_start = 2000
        # For wedge800bact, use ingressVlan starting from 2033 (not vlan_id_start)
        # Service port uses 2200
        ingress_vlan_start = 2033 if platform == "wedge800bact" else 2000
        service_port_vlan = 2200  # Special VLAN for service port
        ipv6_base = 2401
        # For minipack3n and wedge800bact: start from 11.0.0.0/24; for others: 10.0.0.0/24
        ipv4_second_octet = 1 if platform in ["minipack3n", "wedge800bact"] else 0
        
        print("\n" + "="*70)
        print("Step 5: Creating configuration objects")
        print("="*70)
        
        # Create default VLANs
        if platform == "minipack3n":
            # For minipack3n, only add default VLAN with id=1
            vlan_obj = {
                "name": "default",
                "id": 1,
                "recordStats": True,
                "routable": False,
                "ipAddresses": []
            }
            vlans.append(vlan_obj)
            print(f"Created default VLAN (id=1) for {platform}")
            
            # Create loopback interface (intfID=10, vlanID=1, isVirtual=False, type=1)
            loopback_intf = {
                "intfID": 10,
                "routerID": 0,
                "vlanID": 1,
                "ipAddresses": ["2400::/64", "10.0.0.0/24"],
                "mtu": 9000,
                "isVirtual": False,
                "isStateSyncDisabled": True,
                "type": 1,
                "scope": 0
            }
            interfaces.append(loopback_intf)
            print(f"Created loopback interface (intfID=10) for {platform}")
        elif platform == "wedge800bact":
            # For wedge800bact, add fbossLoopback0 (id=10) and default (id=4094) VLANs
            vlan_obj = create_vlan_object(10)
            vlan_obj["name"] = "fbossLoopback0"
            vlans.append(vlan_obj)
            
            vlan_obj = create_vlan_object(4094)
            vlan_obj["name"] = "default"
            vlan_obj["routable"] = False
            vlans.append(vlan_obj)
            print(f"Created fbossLoopback0 (id=10) and default (id=4094) VLANs for {platform}")
            
            # Create loopback interface (intfID=10, vlanID=10, isVirtual=True, type=1)
            # Note: Loopback interface is special - it's virtual and type=1
            loopback_intf = {
                "intfID": 10,
                "routerID": 0,
                "vlanID": 10,
                "ipAddresses": ["2400::/64", "10.0.0.0/24"],
                "mtu": 9000,
                "isVirtual": True,
                "isStateSyncDisabled": True,
                "type": 1,
                "scope": 0
            }
            interfaces.append(loopback_intf)
            print(f"Created loopback interface (intfID=10) for {platform}")
        else:
            vlan_obj = create_vlan_object(10)
            vlan_obj["name"] = "fbossLoopback0"
            vlans.append(vlan_obj)
            
            vlan_obj = create_vlan_object(4094)
            vlan_obj["name"] = "default"
            vlan_obj["routable"] = False  # Fixed: default VLAN should not be routable
            vlans.append(vlan_obj)
            
            # Create loopback interface (intfID=10, vlanID=10, isVirtual=False, type=1)
            loopback_intf = {
                "intfID": 10,
                "routerID": 0,
                "vlanID": 10,
                "ipAddresses": ["2531::/64", "140.0.0.0/24"],
                "mtu": 9000,
                "isVirtual": False,
                "isStateSyncDisabled": True,
                "type": 1,
                "scope": 0
            }
            interfaces.append(loopback_intf)
            print(f"Created loopback interface (intfID=10) for {platform}")
        
        # Generate objects for each port
        index = 0
        ports_created = 0
        port_id_counter = 1  # For minipack3n portID field
        
        for port_name in port_names:
            if port_name in port_mapping:
                port_info = port_mapping[port_name]
                logical_id = port_info['logical_id']
                port_type_from_csv = port_info['port_type']
                vlan_id = vlan_id_start + index
                
                # For wedge800bact service port (logicalID=351), use special VLAN 2200
                if platform == "wedge800bact" and logical_id == 351:
                    ingress_vlan_value = service_port_vlan
                elif platform == "wedge800bact":
                    # For regular ports, use separate ingress_vlan counter starting from 2033
                    ingress_vlan_value = ingress_vlan_start + index
                else:
                    ingress_vlan_value = vlan_id
                
                topo_info = port_info_map.get(port_name, {})
                neighbor = topo_info.get("neighbor", "")
                profile_id = topo_info.get("profileID", 38)
                state = topo_info.get("state", 2)  # Get state from topology info
                
                speed = profile_speed_map.get(profile_id, 400000)
                # Check if it's a service port
                # For minipack3n: check port 65 (/65/ in name)
                # For wedge800bact: check logical ID 351
                # For other platforms: check logical ID 351
                if platform == "minipack3n":
                    is_service_port = '/65/' in port_name
                elif platform == "wedge800bact":
                    is_service_port = (logical_id == 351)
                else:
                    is_service_port = (logical_id == 351)
                
                port_obj = create_port_object(
                    logical_id, port_name, ingress_vlan_value, speed, 
                    profile_id, neighbor, state, is_service_port, platform, port_type_from_csv
                )
                ports.append(port_obj)
                ports_created += 1
                
                if ports_created <= 5 or is_service_port:
                    print(f"Created port: {port_name} (ID:{logical_id}, Speed:{speed}, Profile:{profile_id}, State:{state})")
                
                # For wedge800bact, create VLANs and vlanPorts using ingress_vlan_value (2033+)
                # For minipack3n, skip VLAN and vlanPort creation
                if platform == "wedge800bact":
                    # Create VLAN with id=2033, 2034, 2035... or 2200 for service port
                    vlan_obj = create_vlan_object(ingress_vlan_value)
                    vlans.append(vlan_obj)
                    
                    # Create vlanPort mapping
                    vlanport_obj = create_vlanport_object(ingress_vlan_value, logical_id)
                    vlan_ports.append(vlanport_obj)
                elif platform not in ["minipack3n"]:
                    # For other platforms (minipack3ba, wedge800cact)
                    vlan_obj = create_vlan_object(vlan_id)
                    vlans.append(vlan_obj)
                    
                    vlanport_obj = create_vlanport_object(vlan_id, logical_id)
                    vlan_ports.append(vlanport_obj)
                
                ipv6_addr = f"{ipv6_base + index}::/64"
                ipv4_addr = f"{10 + ipv4_second_octet}.0.0.0/24"
                
                # For wedge800bact, use ingress_vlan_value for interface intfID and vlanID
                if platform == "wedge800bact":
                    # Service port (logicalID=351) interface should have isVirtual=True
                    interface_obj = create_interface_object(ingress_vlan_value, ipv6_addr, ipv4_addr, platform, logical_id)
                    # Override isVirtual for service port
                    if logical_id == 351:
                        interface_obj["isVirtual"] = True
                    interfaces.append(interface_obj)
                else:
                    interface_obj = create_interface_object(vlan_id, ipv6_addr, ipv4_addr, platform, logical_id)
                    interfaces.append(interface_obj)
                
                ipv4_second_octet += 1
                index += 1
        
        # Sort ports by logical port ID (except for wedge800bact which maintains connection order)
        print("\n" + "="*70)
        print("Step 6: Finalizing port order")
        print("="*70)
        if platform != "wedge800bact":
            ports.sort(key=lambda x: x['logicalID'])
            print(f"Sorted {len(ports)} ports by logicalID")
        else:
            print(f"Keeping {len(ports)} ports in connection order (not sorting by logicalID)")
        
        # Insert objects into config in the correct order for human comparison
        # Save the existing sw dict and rebuild it with correct key order
        print("\n" + "="*70)
        print("Step 7: Arranging config objects for easy comparison")
        print("="*70)
        
        old_sw = config["sw"]
        new_sw = {}
        
        # Order: version, ports, vlans, vlanPorts, defaultVlan, interfaces, then all other fields
        new_sw["version"] = old_sw.get("version", 0)
        new_sw["ports"] = ports
        new_sw["vlans"] = vlans
        new_sw["vlanPorts"] = vlan_ports
        
        # Add defaultVlan if it exists
        if "defaultVlan" in old_sw:
            new_sw["defaultVlan"] = old_sw["defaultVlan"]
        
        new_sw["interfaces"] = interfaces
        
        # Add all remaining fields in their original order
        for key, value in old_sw.items():
            if key not in ["version", "ports", "vlans", "vlanPorts", "defaultVlan", "interfaces"]:
                new_sw[key] = value
        
        config["sw"] = new_sw
        print(f"Arranged objects: ports, vlans, vlanPorts, interfaces in proper order")
        print(f"Generated: {len(ports)} ports, {len(vlans)} VLANs, {len(vlan_ports)} VLAN ports, {len(interfaces)} interfaces")
        
        # Save output
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n[OK] Config saved to: {output_file}")
        
        # Cleanup temp files
        for temp_file in [temp_config, temp_csv, temp_topology]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        print("\n" + "="*70)
        print("SUCCESS: Configuration generated successfully")
        print("="*70)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def detect_platform_from_fruid(fruid_path="/var/facebook/fboss/fruid.json"):
    """
    Detect platform from fruid.json file
    Maps Product Name to platform identifier
    """
    product_name_map = {
        "MINIPACK3": "minipack3ba",
        "MINIPACK3BA": "minipack3ba",
        "MINIPACK3N": "minipack3n",
        "WEDGE800BACT": "wedge800bact",
        "WEDGE800CACT": "wedge800cact",
        "WEDGE800B": "wedge800bact",
        "WEDGE800C": "wedge800cact",
    }
    
    try:
        print(f"Reading platform info from: {fruid_path}")
        with open(fruid_path, 'r') as f:
            fruid_data = json.load(f)
        
        product_name = fruid_data.get("Information", {}).get("Product Name", "").strip().upper()
        
        if not product_name:
            print("ERROR: 'Product Name' not found in fruid.json")
            return None
        
        print(f"Detected Product Name: {product_name}")
        
        # Try exact match first
        if product_name in product_name_map:
            platform = product_name_map[product_name]
            print(f"Mapped to platform: {platform}")
            return platform
        
        # Try partial match
        for key, value in product_name_map.items():
            if key in product_name:
                platform = value
                print(f"Partial match '{key}' -> platform: {platform}")
                return platform
        
        print(f"ERROR: Unknown product name '{product_name}'")
        print("Supported product names:")
        for pn in product_name_map.keys():
            print(f"  - {pn}")
        return None
        
    except FileNotFoundError:
        print(f"ERROR: fruid.json not found at {fruid_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse fruid.json: {e}")
        return None
    except Exception as e:
        print(f"ERROR: Failed to read fruid.json: {e}")
        return None

def main():
    # First, ensure qsfp_test_configs are downloaded
    ensure_qsfp_test_configs()
    
    # Check command line arguments
    if len(sys.argv) > 3:
        print("Usage: python reconvert.py [platform] [config_filename]")
        print("\nArguments:")
        print("  platform:        Platform name (optional, auto-detected from fruid.json if not specified)")
        print("  config_filename: Custom config file name from link_test_configs/{PLATFORM}/ (optional)")
        print("\nIf platform is not specified, it will be auto-detected from fruid.json")
        print("\nSupported platforms:")
        for platform in PLATFORMS.keys():
            print(f"  - {platform}")
        print("\nExamples:")
        print("  python reconvert.py")
        print("  python reconvert.py wedge800bact")
        print("  python reconvert.py wedge800bact copper_link.json")
        print("  python reconvert.py wedge800bact optics_link_one.json")
        sys.exit(1)
    
    # Parse command line arguments
    custom_config_name = None
    
    if len(sys.argv) >= 2:
        # Platform specified via command line
        platform = sys.argv[1].lower()
        print(f"Using platform from command line: {platform}")
        
        # Check if custom config filename is provided
        if len(sys.argv) == 3:
            custom_config_name = sys.argv[2]
            print(f"Using custom config file: {custom_config_name}")
    else:
        # Auto-detect from fruid.json
        print("="*70)
        print("Auto-detecting platform from fruid.json")
        print("="*70)
        platform = detect_platform_from_fruid()
        if not platform:
            print("\nFailed to auto-detect platform. Please specify manually:")
            print("Usage: python reconvert.py <platform> [config_filename]")
            print("\nSupported platforms:")
            for p in PLATFORMS.keys():
                print(f"  - {p}")
            sys.exit(1)
    
    if platform not in PLATFORMS:
        print(f"ERROR: Unknown platform '{platform}'")
        print("\nSupported platforms:")
        for p in PLATFORMS.keys():
            print(f"  - {p}")
        sys.exit(1)
    
    print("="*70)
    print(f"FBOSS Config Generator - Platform: {platform.upper()}")
    if custom_config_name:
        print(f"Custom Config: {custom_config_name}")
    print("="*70)
    generate_config(platform, custom_config_name)

if __name__ == "__main__":
    main()
