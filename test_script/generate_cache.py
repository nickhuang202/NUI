#!/usr/bin/env python3
"""
Generate dashboard cache after test completion
Also writes platform cache file for dashboard to read

This script is called at the end of run_all_test.sh to:
1. Write .platform_cache file with detected platform
2. Pre-generate any dashboard caches if needed
"""
import sys
import os
import json
from pathlib import Path

def write_platform_cache(platform):
    """Write platform to .platform_cache file in NUI directory"""
    try:
        # NUI directory is parent of test_script
        nui_dir = Path(__file__).parent.parent
        cache_file = nui_dir / '.platform_cache'
        
        with open(cache_file, 'w') as f:
            f.write(platform)
        
        print(f"✓ Platform cache file written: {cache_file}")
        print(f"  Platform: {platform}")
        return True
    except Exception as e:
        print(f"✗ Error writing platform cache: {e}")
        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: generate_cache.py <platform> <date>")
        sys.exit(1)
    
    platform = sys.argv[1]
    test_date = sys.argv[2]
    
    print(f"Generating cache for platform: {platform}, date: {test_date}")
    
    # Write platform cache file
    write_platform_cache(platform)
    
    # Here you can add more cache generation logic if needed
    # For example, pre-generate dashboard cache from test results
    
    print("Cache generation complete")

if __name__ == '__main__':
    main()
