#!/usr/bin/env python3
"""
Port Pair Validation Script

Validates that port pairs in JSON configuration files have matching:
1. Name (in expectedLLDPValues pointing back to each other)
2. ProfileID
3. Speed
"""

import json
import os
from typing import Dict, List, Tuple

def load_json_file(filepath: str) -> dict:
    """Load and parse a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

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

def check_port_pairs_in_file(filepath: str) -> List[Dict]:
    """Check all port pairs in a single JSON file."""
    print(f"\n{'='*80}")
    print(f"Checking file: {os.path.basename(filepath)}")
    print(f"{'='*80}")
    
    data = load_json_file(filepath)
    issues = []
    
    # Extract ports array
    ports = data.get('sw', {}).get('ports', [])
    
    if not ports:
        print("No ports found in file")
        return issues
    
    # Create a lookup dictionary by port name
    port_by_name = {}
    for port in ports:
        port_name = port.get('name')
        if port_name:
            port_by_name[port_name] = port
    
    print(f"Total ports found: {len(ports)}")
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
        
        print(f"\n--- Checking Port: {port_name} (logicalID: {port_id}) ---")
        print(f"  Speed: {port_speed}")
        print(f"  ProfileID: {port_profile}")
        print(f"  Expected Neighbor: {neighbor_name}")
        
        # Find the neighbor port
        neighbor_port = port_by_name.get(neighbor_name)
        
        if not neighbor_port:
            issue = {
                'file': filepath,
                'port': port_name,
                'logicalID': port_id,
                'issue': f"Neighbor port '{neighbor_name}' not found in file"
            }
            issues.append(issue)
            print(f"  ❌ ERROR: {issue['issue']}")
            continue
        
        neighbor_id = neighbor_port.get('logicalID')
        neighbor_speed = neighbor_port.get('speed')
        neighbor_profile = neighbor_port.get('profileID')
        neighbor_expected = get_expected_neighbor_name(neighbor_port)
        
        print(f"  Found Neighbor: {neighbor_name} (logicalID: {neighbor_id})")
        print(f"    Speed: {neighbor_speed}")
        print(f"    ProfileID: {neighbor_profile}")
        print(f"    Expected Neighbor: {neighbor_expected}")
        
        # Validation checks
        all_passed = True
        
        # Check 1: Neighbor's expectedLLDPValues should point back to original port
        if neighbor_expected != port_name:
            issue = {
                'file': filepath,
                'port': port_name,
                'logicalID': port_id,
                'neighbor': neighbor_name,
                'issue': f"Neighbor's expectedLLDPValues is '{neighbor_expected}', expected '{port_name}'"
            }
            issues.append(issue)
            print(f"  ❌ FAIL: Name mismatch - {issue['issue']}")
            all_passed = False
        else:
            print(f"  ✓ PASS: Name check - neighbor points back correctly")
        
        # Check 2: ProfileID should match
        if port_profile != neighbor_profile:
            issue = {
                'file': filepath,
                'port': port_name,
                'logicalID': port_id,
                'neighbor': neighbor_name,
                'issue': f"ProfileID mismatch: {port_profile} vs {neighbor_profile}"
            }
            issues.append(issue)
            print(f"  ❌ FAIL: ProfileID mismatch - {port_profile} vs {neighbor_profile}")
            all_passed = False
        else:
            print(f"  ✓ PASS: ProfileID match - {port_profile}")
        
        # Check 3: Speed should match
        if port_speed != neighbor_speed:
            issue = {
                'file': filepath,
                'port': port_name,
                'logicalID': port_id,
                'neighbor': neighbor_name,
                'issue': f"Speed mismatch: {port_speed} vs {neighbor_speed}"
            }
            issues.append(issue)
            print(f"  ❌ FAIL: Speed mismatch - {port_speed} vs {neighbor_speed}")
            all_passed = False
        else:
            print(f"  ✓ PASS: Speed match - {port_speed}")
        
        if all_passed:
            print(f"  ✅ All checks passed for pair: {port_name} <-> {neighbor_name}")
    
    return issues

def check_materialized_json(filepath: str) -> List[Dict]:
    """Check port pairs in materialized JSON format."""
    print(f"\n{'='*80}")
    print(f"Checking file: {os.path.basename(filepath)}")
    print(f"{'='*80}")
    
    data = load_json_file(filepath)
    issues = []
    
    # Extract interfaces from pimInfo
    interfaces = {}
    for pim in data.get('pimInfo', []):
        interfaces.update(pim.get('interfaces', {}))
    
    if not interfaces:
        print("No interfaces found in file")
        return issues
    
    print(f"Total interfaces found: {len(interfaces)}")
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
        
        print(f"\n--- Checking Port: {port_name} ---")
        print(f"  ProfileID: {port_profile}")
        print(f"  Expected Neighbor: {neighbor_name}")
        
        # Find the neighbor interface
        neighbor_info = interfaces.get(neighbor_name)
        
        if not neighbor_info:
            issue = {
                'file': filepath,
                'port': port_name,
                'issue': f"Neighbor port '{neighbor_name}' not found in file"
            }
            issues.append(issue)
            print(f"  ❌ ERROR: {issue['issue']}")
            continue
        
        neighbor_profile = neighbor_info.get('profileID')
        neighbor_expected = neighbor_info.get('neighbor')
        
        print(f"  Found Neighbor: {neighbor_name}")
        print(f"    ProfileID: {neighbor_profile}")
        print(f"    Expected Neighbor: {neighbor_expected}")
        
        # Validation checks
        all_passed = True
        
        # Check 1: Neighbor's neighbor should point back to original port
        if neighbor_expected != port_name:
            issue = {
                'file': filepath,
                'port': port_name,
                'neighbor': neighbor_name,
                'issue': f"Neighbor's neighbor is '{neighbor_expected}', expected '{port_name}'"
            }
            issues.append(issue)
            print(f"  ❌ FAIL: Name mismatch - {issue['issue']}")
            all_passed = False
        else:
            print(f"  ✓ PASS: Name check - neighbor points back correctly")
        
        # Check 2: ProfileID should match
        if port_profile != neighbor_profile:
            issue = {
                'file': filepath,
                'port': port_name,
                'neighbor': neighbor_name,
                'issue': f"ProfileID mismatch: {port_profile} vs {neighbor_profile}"
            }
            issues.append(issue)
            print(f"  ❌ FAIL: ProfileID mismatch - {port_profile} vs {neighbor_profile}")
            all_passed = False
        else:
            print(f"  ✓ PASS: ProfileID match - {port_profile}")
        
        if all_passed:
            print(f"  ✅ All checks passed for pair: {port_name} <-> {neighbor_name}")
    
    return issues

def main():
    """Main function to check all files."""
    base_dir = os.path.join('Topology', 'WEDGE800BACT')
    
    files_to_check = [
        ('copper_link.json', check_port_pairs_in_file),
        ('optics_link_one.json', check_port_pairs_in_file),
        ('optics_link_two.json', check_port_pairs_in_file),
        ('wedge800bact.materialized_JSON', check_materialized_json),
    ]
    
    all_issues = []
    
    print("="*80)
    print("PORT PAIR VALIDATION")
    print("="*80)
    
    for filename, check_func in files_to_check:
        filepath = os.path.join(base_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"\n⚠️  File not found: {filepath}")
            continue
        
        try:
            issues = check_func(filepath)
            all_issues.extend(issues)
        except Exception as e:
            print(f"\n❌ Error processing {filename}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    if not all_issues:
        print("\n✅ All port pair checks PASSED!")
        print("All ports have matching:")
        print("  - Names (expectedLLDPValues pointing back)")
        print("  - ProfileIDs")
        print("  - Speeds")
    else:
        print(f"\n❌ Found {len(all_issues)} issue(s):\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. File: {os.path.basename(issue['file'])}")
            print(f"   Port: {issue['port']}", end='')
            if 'logicalID' in issue:
                print(f" (logicalID: {issue['logicalID']})", end='')
            print()
            if 'neighbor' in issue:
                print(f"   Neighbor: {issue['neighbor']}")
            print(f"   Issue: {issue['issue']}")
            print()

if __name__ == '__main__':
    main()
