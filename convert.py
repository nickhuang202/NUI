import json
import argparse
import csv
import re
import os
from pathlib import Path
from urllib.request import urlopen
from typing import List, Dict

# Platform configuration mapping
PLATFORM_CONFIG = {
    'MINIPACK3BA': {
        'url': 'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/montblanc.materialized_JSON',
        'local_path': 'link_test_configs/MINIPACK3BA/montblanc.materialized_JSON',
        'filename': 'montblanc.materialized_JSON'
    },
    'MINIPACK3N': {
        'url': 'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/minipack3n.materialized_JSON',
        'local_path': 'link_test_configs/MINIPACK3N/minipack3n.materialized_JSON',
        'filename': 'minipack3n.materialized_JSON'
    },
    'WEDGE800BACT': {
        'url': 'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/wedge800bact.materialized_JSON',
        'local_path': 'link_test_configs/WEDGE800BACT/wedge800bact.materialized_JSON',
        'filename': 'wedge800bact.materialized_JSON'
    },
    'WEDGE800CACT': {
        'url': 'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/wedge800bact.materialized_JSON',
        'local_path': 'link_test_configs/WEDGE800CACT/wedge800bact.materialized_JSON',
        'filename': 'wedge800bact.materialized_JSON'
    }
}

def detect_platform():
    """Detect platform from /var/facebook/fboss/fruid.json"""
    fruid_path = '/var/facebook/fboss/fruid.json'
    
    if not os.path.isfile(fruid_path):
        print(f"Warning: FRUID file not found: {fruid_path}")
        return None
    
    try:
        with open(fruid_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract Product Name from Information section
        info = data.get('Information', {})
        product = info.get('Product Name') or info.get('Product') or info.get('ProductName')
        
        if not product:
            print("Warning: Product Name not found in FRUID file")
            return None
        
        product = product.strip().upper()
        print(f"Detected Product: {product}")
        
        # Map product name to platform
        if product in ('MINIPACK3', 'MINIPACK3BA'):
            return 'MINIPACK3BA'
        elif product == 'MINIPACK3N':
            return 'MINIPACK3N'
        elif product == 'WEDGE800BACT':
            return 'WEDGE800BACT'
        elif product == 'WEDGE800CACT':
            return 'WEDGE800CACT'
        else:
            print(f"Warning: Unsupported product type: {product}")
            return None
            
    except Exception as e:
        print(f"Warning: Error reading FRUID file: {e}")
        return None

def get_config_source(platform=None):
    """Get config source (local file or URL) based on platform
    
    Args:
        platform: Platform name (MINIPACK3BA, MINIPACK3N, etc.) or None for auto-detect
        
    Returns:
        tuple: (source_path, platform_name) where source_path is the file path or URL
    """
    # Auto-detect platform if not specified
    if platform is None:
        platform = detect_platform()
        if platform is None:
            raise ValueError("Unable to auto-detect platform, please use --platform parameter to specify manually")
    
    # Normalize platform name
    platform = platform.upper()
    
    if platform not in PLATFORM_CONFIG:
        raise ValueError(f"Unsupported platform: {platform}. Supported platforms: {', '.join(PLATFORM_CONFIG.keys())}")
    
    config = PLATFORM_CONFIG[platform]
    local_path = config['local_path']
    url = config['url']
    
    # Check if local file exists (try both relative and absolute paths)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try relative to script directory
    local_full_path = os.path.join(script_dir, local_path)
    
    if os.path.isfile(local_full_path):
        print(f"Using local file: {local_full_path}")
        return local_full_path, platform
    
    # Try as absolute path from /home/NUI
    alt_path = os.path.join('/home/NUI', local_path)
    if os.path.isfile(alt_path):
        print(f"Using local file: {alt_path}")
        return alt_path, platform
    
    # Fall back to URL
    print(f"Local file not found, will download from URL: {url}")
    return url, platform

def load_json(source):
    """Support URL or local file loading JSON"""
    if source.startswith("http://") or source.startswith("https://"):
        print(f"Downloading from URL: {source}")
        with urlopen(source) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        print(f"Reading from local file: {source}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

def generate_topology(config_json):
    """Generate link_test_topology JSON from link_test_configs"""
    # Check if it's already in topology format
    if 'pimInfo' in config_json:
        print("Input is already in topology format, returning directly")
        return config_json
    
    ports = config_json["sw"]["ports"]
    
    interfaces = {}
    
    for port in ports:
        name = port.get("name")
        if not name:
            continue
        
        expected = port.get("expectedLLDPValues", {})
        if "2" not in expected:
            continue  # Only process ports with explicit LLDP expected neighbors
        
        neighbor = expected["2"]
        profile_id = port.get("profileID", 0)  # Get the port's profileID directly
        
        # Add bidirectionally (preserve actual values even if profileID differs)
        interfaces[name] = {
            "neighbor": neighbor,
            "profileID": profile_id,
            "hasTransceiver": True
        }
        # Reverse direction (if neighbor also exists in config, usually it does, but added here for completeness)
        # Note: if neighbor port doesn't have its own expectedLLDPValues, it will still be added (based on this port's info)
        if neighbor not in interfaces:
            # Need to find the actual profileID of the neighbor port
            neighbor_profile = profile_id  # Default to the same one
            for p in ports:
                if p.get("name") == neighbor:
                    neighbor_profile = p.get("profileID", 0)
                    break
            interfaces[neighbor] = {
                "neighbor": name,
                "profileID": neighbor_profile,
                "hasTransceiver": True
            }
    
    topology = {
        "platform": "wedge800bact",
        "pimInfo": [
            {
                "slot": 1,
                "pimName": "",
                "interfaces": interfaces,
                "tcvrs": {}
            }
        ]
    }
    
    return topology

def get_expected_neighbor_name(port: dict) -> str:
    """Extract the expected neighbor name from expectedLLDPValues."""
    lldp_values = port.get('expectedLLDPValues', {})
    
    # Handle different formats: {"name": "..."} or {"2": "..."}
    if isinstance(lldp_values, dict):
        if 'name' in lldp_values:
            return lldp_values['name']
        elif '2' in lldp_values:
            return lldp_values['2']
        # Try to find any value that looks like a port name
        for value in lldp_values.values():
            if isinstance(value, str) and 'eth' in value:
                return value
    
    return None

def validate_port_pairs(config_json) -> List[Dict]:
    """Validate port pairs in the configuration JSON.
    
    Checks:
    1. Each port's expectedLLDPValues neighbor points back to it
    2. Port pairs have matching profileID
    3. Port pairs have matching speed
    
    Returns list of issues found.
    """
    ports = config_json.get('sw', {}).get('ports', [])
    issues = []
    
    if not ports:
        return issues
    
    # Create a lookup dictionary by port name
    port_by_name = {}
    for port in ports:
        port_name = port.get('name')
        if port_name:
            port_by_name[port_name] = port
    
    checked_pairs = set()  # Track checked pairs to avoid duplicate checks
    
    # Check each port
    for port in ports:
        port_name = port.get('name')
        port_id = port.get('logicalID')
        port_speed = port.get('speed')
        port_profile = port.get('profileID')
        
        # Get expected neighbor
        neighbor_name = get_expected_neighbor_name(port)
        
        if not neighbor_name:
            # Skip ports without expected neighbors
            continue
        
        # Create a pair tuple (sorted to avoid duplicates)
        pair = tuple(sorted([port_name, neighbor_name]))
        if pair in checked_pairs:
            continue
        checked_pairs.add(pair)
        
        # Find the neighbor port
        neighbor_port = port_by_name.get(neighbor_name)
        
        if not neighbor_port:
            issue = {
                'port': port_name,
                'logicalID': port_id,
                'issue': f"Neighbor port '{neighbor_name}' not found in config"
            }
            issues.append(issue)
            continue
        
        neighbor_id = neighbor_port.get('logicalID')
        neighbor_speed = neighbor_port.get('speed')
        neighbor_profile = neighbor_port.get('profileID')
        neighbor_expected = get_expected_neighbor_name(neighbor_port)
        
        # Validation checks
        
        # Check 1: Neighbor's expectedLLDPValues should point back to original port
        if neighbor_expected != port_name:
            issue = {
                'port': port_name,
                'logicalID': port_id,
                'neighbor': neighbor_name,
                'issue': f"Neighbor's expectedLLDPValues is '{neighbor_expected}', expected '{port_name}'"
            }
            issues.append(issue)
        
        # Check 2: ProfileID should match
        if port_profile != neighbor_profile:
            issue = {
                'port': port_name,
                'logicalID': port_id,
                'neighbor': neighbor_name,
                'issue': f"ProfileID mismatch: {port_profile} vs {neighbor_profile}"
            }
            issues.append(issue)
        
        # Check 3: Speed should match
        if port_speed != neighbor_speed:
            issue = {
                'port': port_name,
                'logicalID': port_id,
                'neighbor': neighbor_name,
                'issue': f"Speed mismatch: {port_speed} vs {neighbor_speed}"
            }
            issues.append(issue)
    
    return issues

def validate_topology(topology_json) -> List[Dict]:
    """Validate port pairs in the materialized topology JSON.
    
    Checks:
    1. Each interface's neighbor points back to it
    2. Interface pairs have matching profileID
    
    Returns list of issues found.
    """
    issues = []
    
    # Extract interfaces from pimInfo
    interfaces = {}
    for pim in topology_json.get('pimInfo', []):
        interfaces.update(pim.get('interfaces', {}))
    
    if not interfaces:
        return issues
    
    checked_pairs = set()
    
    # Check each interface
    for port_name, port_info in interfaces.items():
        neighbor_name = port_info.get('neighbor')
        port_profile = port_info.get('profileID')
        
        if not neighbor_name:
            continue
        
        # Create a pair tuple (sorted to avoid duplicates)
        pair = tuple(sorted([port_name, neighbor_name]))
        if pair in checked_pairs:
            continue
        checked_pairs.add(pair)
        
        # Find the neighbor interface
        neighbor_info = interfaces.get(neighbor_name)
        
        if not neighbor_info:
            issue = {
                'port': port_name,
                'issue': f"Neighbor port '{neighbor_name}' not found in topology"
            }
            issues.append(issue)
            continue
        
        neighbor_profile = neighbor_info.get('profileID')
        neighbor_expected = neighbor_info.get('neighbor')
        
        # Validation checks
        
        # Check 1: Neighbor's neighbor should point back to original port
        if neighbor_expected != port_name:
            issue = {
                'port': port_name,
                'neighbor': neighbor_name,
                'issue': f"Neighbor's neighbor is '{neighbor_expected}', expected '{port_name}'"
            }
            issues.append(issue)
        
        # Check 2: ProfileID should match
        if port_profile != neighbor_profile:
            issue = {
                'port': port_name,
                'neighbor': neighbor_name,
                'issue': f"ProfileID mismatch: {port_profile} vs {neighbor_profile}"
            }
            issues.append(issue)
    
    return issues

def extract_port_number(port_name: str) -> int:
    """Extract port number from port name like 'eth1/17/1' -> 17"""
    match = re.search(r'eth1/(\d+)/', port_name)
    if match:
        return int(match.group(1))
    return None

def generate_csv_report(topology_json, source_filename: str, output_csv: str):
    """Generate CSV report with port numbers and profileIDs.
    
    Format:
    Port,<filename>
    1,<profileID>
    2,<profileID>
    ...
    33,<profileID>
    """
    # Extract interfaces
    interfaces = {}
    for pim in topology_json.get('pimInfo', []):
        interfaces.update(pim.get('interfaces', {}))
    
    # Create a mapping of port number to profileID
    # We'll use the first occurrence of each port number we find
    port_profiles = {}
    for port_name, port_info in interfaces.items():
        port_num = extract_port_number(port_name)
        if port_num is not None:
            # Store first profileID found for this port number
            if port_num not in port_profiles:
                port_profiles[port_num] = port_info.get('profileID', '')
    
    # Write CSV file
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header row
        writer.writerow(['Port', source_filename])
        
        # Data rows for ports 1-33
        for port_num in range(1, 34):
            profile_id = port_profiles.get(port_num, '')
            writer.writerow([port_num, profile_id])
    
    print(f"CSV report generated: {output_csv}")
    print(f"  Contains ProfileID mapping for 33 ports")

def print_validation_report(config_issues: List[Dict], topology_issues: List[Dict]):
    """Print a formatted validation report."""
    print("\n" + "="*80)
    print("PORT PAIR VALIDATION REPORT")
    print("="*80)
    
    if config_issues:
        print(f"\n⚠️  Found {len(config_issues)} issue(s) in input configuration:\n")
        for i, issue in enumerate(config_issues, 1):
            print(f"{i}. Port: {issue['port']}", end='')
            if 'logicalID' in issue:
                print(f" (logicalID: {issue['logicalID']})", end='')
            print()
            if 'neighbor' in issue:
                print(f"   Neighbor: {issue['neighbor']}")
            print(f"   Issue: {issue['issue']}")
    else:
        print("\n✅ Input configuration validation PASSED")
        print("   All port pairs have matching names, profileIDs, and speeds")
    
    if topology_issues:
        print(f"\n⚠️  Found {len(topology_issues)} issue(s) in generated topology:\n")
        for i, issue in enumerate(topology_issues, 1):
            print(f"{i}. Port: {issue['port']}")
            if 'neighbor' in issue:
                print(f"   Neighbor: {issue['neighbor']}")
            print(f"   Issue: {issue['issue']}")
    else:
        print("\n✅ Generated topology validation PASSED")
        print("   All interface pairs have matching names and profileIDs")
    
    print("\n" + "="*80)
    
    return len(config_issues) + len(topology_issues)

def main():
    parser = argparse.ArgumentParser(
        description="Convert FBOSS link_test_configs JSON to link_test_topology JSON (supports automatic platform detection)"
    )
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="link_test_configs JSON source (URL or local file path). If not specified, will auto-select based on platform"
    )
    parser.add_argument(
        "-p", "--platform",
        choices=['MINIPACK3BA', 'MINIPACK3N', 'WEDGE800BACT', 'WEDGE800CACT'],
        help="Platform name. If not specified, will auto-detect from /var/facebook/fboss/fruid.json"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output topology JSON filename. If not specified, will auto-name based on platform"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip port pair validation"
    )
    parser.add_argument(
        "--csv",
        help="Output CSV report filename (contains port ProfileID mapping)"
    )
    
    args = parser.parse_args()
    
    try:
        # Determine config source
        if args.config:
            # User specified config path/URL
            config_source = args.config
            platform = args.platform or 'UNKNOWN'
            print(f"Using specified config source: {config_source}")
        else:
            # Auto-detect platform and get appropriate config source
            config_source, platform = get_config_source(args.platform)
            print(f"Detected platform: {platform}")
        
        # Set default output filename based on platform if not specified
        if args.output:
            output_file = args.output
        else:
            if platform in PLATFORM_CONFIG:
                filename = PLATFORM_CONFIG[platform]['filename']
                base_name = filename.replace('.materialized_JSON', '')
                output_file = f"{base_name}_link_test_topology.json"
            else:
                output_file = "link_test_topology.json"
            print(f"Output file: {output_file}")
        
        config_json = load_json(config_source)
        print("Config loaded successfully, generating topology...")
        
        # Check format and validate accordingly
        is_topology_format = 'pimInfo' in config_json
        
        # Validate input configuration
        config_issues = []
        if not args.skip_validation:
            if is_topology_format:
                print("\nValidating port pairs in input topology...")
                config_issues = validate_topology(config_json)
            else:
                print("\nValidating port pairs in input configuration...")
                config_issues = validate_port_pairs(config_json)
        
        topology_json = generate_topology(config_json)
        
        # Validate generated topology (skip if input was already topology)
        topology_issues = []
        if not args.skip_validation and not is_topology_format:
            print("Validating generated topology...")
            topology_issues = validate_topology(topology_json)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(topology_json, f, indent=2, ensure_ascii=False)
        
        interface_count = len(topology_json["pimInfo"][0]["interfaces"])
        pair_count = interface_count // 2  # Because bidirectional
        print(f"\nConversion complete! Output file: {output_file}")
        print(f"Total {interface_count} interface entries (approximately {pair_count} connections)")
        
        # Print validation report
        if not args.skip_validation:
            if is_topology_format:
                # For topology format, only show one validation
                if config_issues:
                    print("\n" + "="*80)
                    print("PORT PAIR VALIDATION REPORT")
                    print("="*80)
                    print(f"\n⚠️  Found {len(config_issues)} issue(s) in topology:\n")
                    for i, issue in enumerate(config_issues, 1):
                        print(f"{i}. Port: {issue['port']}")
                        if 'neighbor' in issue:
                            print(f"   Neighbor: {issue['neighbor']}")
                        print(f"   Issue: {issue['issue']}")
                    print("\n" + "="*80)
                    print(f"\n⚠️  Warning: Found {len(config_issues)} validation issue(s), please check configuration")
                    # Still generate CSV even if validation fails
                    if args.csv:
                        source_name = Path(config_source).name if config_source else 'unknown'
                        generate_csv_report(topology_json, source_name, args.csv)
                    return 1
                else:
                    print("\n" + "="*80)
                    print("PORT PAIR VALIDATION REPORT")
                    print("="*80)
                    print("\n✅ Topology validation PASSED")
                    print("   All interface pairs have matching names and profileIDs")
                    print("\n" + "="*80)
            else:
                total_issues = print_validation_report(config_issues, topology_issues)
                if total_issues > 0:
                    print(f"\n⚠️  Warning: Found {total_issues} validation issue(s), please check configuration")
                    # Still generate CSV even if validation fails
                    if args.csv:
                        source_name = Path(config_source).name if config_source else 'unknown'
                        generate_csv_report(topology_json, source_name, args.csv)
                    return 1
        
        # Generate CSV report if requested and validation passed
        if args.csv:
            source_name = Path(config_source).name if config_source else 'unknown'
            print()  # Add blank line
            generate_csv_report(topology_json, source_name, args.csv)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
