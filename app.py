import json
import os
import sys
import subprocess
import shutil
import threading
import time
import re
import requests
import tempfile
import logging
from datetime import datetime
from flask import Flask, render_template, request, send_file, jsonify, send_from_directory, abort
from io import BytesIO

# Import new Phase 1 infrastructure
from config import get_config, setup_logging
from middleware import setup_rate_limiting, setup_request_logging, setup_request_id_tracing
from utils import validate_platform, sanitize_path, validate_test_items
from utils.thread_safe_state import get_service_status_manager, get_test_execution_manager
from routes.error_handlers import register_error_handlers

import dashboard  # Import the new dashboard module
import lldp_discovery  # Import LLDP discovery module
import lab_monitor  # Import lab monitor module

# Import helper functions from dashboard routes
from routes.dashboard import find_test_archive, extract_test_log_from_archive

# Initialize Flask app
app = Flask(__name__, static_folder='.', static_url_path='')
app.template_folder = 'templates'  # Ensure Flask looks in the right place

# Load configuration
config = get_config()

# Configure Flask app
app.config['SECRET_KEY'] = config.SECRET_KEY

# Setup logging
logger = setup_logging(app)
logger.info('='*70)
logger.info('NUI Application Starting')
logger.info(f'Environment: {os.getenv("FLASK_ENV", "development")}')
logger.info(f'Host: {config.HOST}:{config.PORT}')
logger.info(f'Debug Mode: {config.DEBUG}')
logger.info('='*70)

# Setup rate limiting
limiter = setup_rate_limiting(app, config)

# Setup request ID tracing
setup_request_id_tracing(app)

# Setup request/response logging
setup_request_logging(app)

# Register error handlers
register_error_handlers(app)

# Register blueprints with API versioning
# Each blueprint is registered twice: once for /api/v1/... and once for /api/...
from routes import dashboard_bp, test_bp, topology_bp, lab_monitor_bp, port_bp, health_bp

# Helper to register blueprint for both v1 and legacy paths
def register_versioned_blueprint(blueprint, original_prefix):
    """Register blueprint for both /api/v1 and /api paths"""
    # Register v1 version
    v1_prefix = original_prefix.replace('/api/', '/api/v1/', 1) if '/api/' in original_prefix else f'/api/v1{original_prefix}'
    blueprint.url_prefix = v1_prefix
    app.register_blueprint(blueprint, name=f'{blueprint.name}_v1')
    
    # Register legacy version (reset to original prefix)
    blueprint.url_prefix = original_prefix
    app.register_blueprint(blueprint)

# Register all blueprints with versioning
register_versioned_blueprint(dashboard_bp, '/api/dashboard')
register_versioned_blueprint(test_bp, '/api/test')
register_versioned_blueprint(topology_bp, '/api')  # topology routes are at /api/topology_*
register_versioned_blueprint(lab_monitor_bp, '/api/lab_monitor')
register_versioned_blueprint(port_bp, '/api')  # port routes are at /api/port_*, /api/absent_*, etc.
# Health blueprint already has v1 and legacy routes defined
app.register_blueprint(health_bp)

logger.info("All blueprints registered with API versioning (v1 + legacy): Dashboard, Test, Topology, Lab Monitor, Port, Health")

# Test report base directory (now from config)
TEST_REPORT_BASE = config.TEST_REPORT_BASE

# Helper function to safely create temp directories
def safe_mkdtemp(prefix='tmp_'):
    """Create a temporary directory with fallback if /tmp doesn't exist."""
    temp_base = tempfile.gettempdir()
    
    # Check if temp directory exists, create if needed
    if not os.path.exists(temp_base):
        try:
            os.makedirs(temp_base, mode=0o700)
            print(f"[TEMP] Created temp directory: {temp_base}")
        except Exception as e:
            print(f"[TEMP] Failed to create {temp_base}: {e}")
            # Fallback to workspace .temp directory
            temp_base = os.path.join(os.getcwd(), '.temp')
            if not os.path.exists(temp_base):
                os.makedirs(temp_base, mode=0o700)
            print(f"[TEMP] Using fallback temp directory: {temp_base}")
    
    return tempfile.mkdtemp(prefix=prefix, dir=temp_base)


# Profile ID mapping from switch_config.thrift
PROFILE_ID_MAP = {
    0: "PROFILE_DEFAULT",
    1: "PROFILE_10G_1_NRZ_NOFEC",
    2: "PROFILE_20G_2_NRZ_NOFEC",
    3: "PROFILE_25G_1_NRZ_NOFEC",
    4: "PROFILE_40G_4_NRZ_NOFEC",
    5: "PROFILE_50G_2_NRZ_NOFEC",
    6: "PROFILE_100G_4_NRZ_NOFEC",
    7: "PROFILE_100G_4_NRZ_CL91",
    8: "PROFILE_100G_4_NRZ_RS528",
    9: "PROFILE_200G_4_PAM4_RS544X2N",
    10: "PROFILE_400G_8_PAM4_RS544X2N",
    11: "PROFILE_10G_1_NRZ_NOFEC_COPPER",
    12: "PROFILE_10G_1_NRZ_NOFEC_OPTICAL",
    13: "PROFILE_20G_2_NRZ_NOFEC_COPPER",
    14: "PROFILE_25G_1_NRZ_NOFEC_COPPER",
    15: "PROFILE_25G_1_NRZ_CL74_COPPER",
    16: "PROFILE_25G_1_NRZ_RS528_COPPER",
    17: "PROFILE_40G_4_NRZ_NOFEC_COPPER",
    18: "PROFILE_40G_4_NRZ_NOFEC_OPTICAL",
    19: "PROFILE_50G_2_NRZ_NOFEC_COPPER",
    20: "PROFILE_50G_2_NRZ_CL74_COPPER",
    21: "PROFILE_50G_2_NRZ_RS528_COPPER",
    22: "PROFILE_100G_4_NRZ_RS528_COPPER",
    23: "PROFILE_100G_4_NRZ_RS528_OPTICAL",
    24: "PROFILE_200G_4_PAM4_RS544X2N_COPPER",
    25: "PROFILE_200G_4_PAM4_RS544X2N_OPTICAL",
    26: "PROFILE_400G_8_PAM4_RS544X2N_OPTICAL",
    27: "PROFILE_100G_4_NRZ_CL91_COPPER",
    28: "PROFILE_100G_4_NRZ_CL91_OPTICAL",
    29: "PROFILE_20G_2_NRZ_NOFEC_OPTICAL",
    30: "PROFILE_25G_1_NRZ_NOFEC_OPTICAL",
    31: "PROFILE_50G_2_NRZ_NOFEC_OPTICAL",
    32: "PROFILE_100G_4_NRZ_NOFEC_COPPER",
    33: "PROFILE_100G_4_NRZ_CL91_COPPER_RACK_YV3_T1",
    34: "PROFILE_25G_1_NRZ_NOFEC_COPPER_RACK_YV3_T1",
    35: "PROFILE_400G_8_PAM4_RS544X2N_COPPER",
    36: "PROFILE_53POINT125G_1_PAM4_RS545_COPPER",
    37: "PROFILE_53POINT125G_1_PAM4_RS545_OPTICAL",
    38: "PROFILE_400G_4_PAM4_RS544X2N_OPTICAL",
    39: "PROFILE_800G_8_PAM4_RS544X2N_OPTICAL",
    40: "PROFILE_100G_2_PAM4_RS544X2N_OPTICAL",
    41: "PROFILE_106POINT25G_1_PAM4_RS544_COPPER",
    42: "PROFILE_106POINT25G_1_PAM4_RS544_OPTICAL",
    43: "PROFILE_50G_1_PAM4_RS544_COPPER",
    44: "PROFILE_50G_1_PAM4_RS544_OPTICAL",
    45: "PROFILE_400G_4_PAM4_RS544X2N_COPPER",
    46: "PROFILE_100G_2_PAM4_RS544X2N_COPPER",
    47: "PROFILE_100G_1_PAM4_RS544_OPTICAL",
    48: "PROFILE_50G_2_NRZ_RS528_OPTICAL",
    49: "PROFILE_100G_1_PAM4_NOFEC_COPPER",
    50: "PROFILE_800G_8_PAM4_RS544X2N_COPPER",
    51: "PROFILE_400G_2_PAM4_RS544X2N_OPTICAL",
    52: "PROFILE_800G_4_PAM4_RS544X2N_OPTICAL",
    53: "PROFILE_200G_1_PAM4_RS544X2N_OPTICAL",
    54: "PROFILE_200G_2_PAM4_RS544_COPPER",
    55: "PROFILE_100G_2_PAM4_RS544_COPPER",
    56: "PROFILE_100G_1_PAM4_RS544_COPPER",
    57: "PROFILE_800G_4_PAM4_RS544X2N_COPPER",
    58: "PROFILE_400G_2_PAM4_RS544X2N_COPPER",
    59: "PROFILE_200G_1_PAM4_RS544X2N_COPPER",
    60: "PROFILE_100G_1_PAM4_RS544X2N_COPPER",
}

# Mapping platform -> (filename, fallback raw URL)
PLATFORMS = {
    'MINIPACK3N': ('minipack3n.materialized_JSON',
                   'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/minipack3n.materialized_JSON'),
    'MINIPACK3BA': ('montblanc.materialized_JSON',
                    'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/montblanc.materialized_JSON'),
    'WEDGE800BACT': ('wedge800bact.materialized_JSON',
                     'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/wedge800bact.materialized_JSON'),
    # wedge800cact materialized JSON not present in upstream repo; fall back to wedge800bact
    'WEDGE800CACT': ('wedge800bact.materialized_JSON',
                     'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/wedge800bact.materialized_JSON')
}


PLATFORM_CACHE_FILE = '.platform_cache'


import json

def detect_and_cache_current_platform():
    """Detect current platform from FRUID JSON and cache it."""
    detected_platform = None
    cwd = os.getcwd()
    fruid_path = '/var/facebook/fboss/fruid.json'

    # Try to read platform from FRUID JSON first
    try:
        with open(fruid_path, 'r') as f:
            fruid_data = json.load(f)
            product_name = fruid_data.get('Information', {}).get('Product Name', '').strip()

            if product_name:
                logger.info(f"[STARTUP] Detected platform from FRUID: {product_name}")
                
                # Handle MINIPACK3 - need to determine if it's BA or N variant
                if product_name == 'MINIPACK3':
                    # Check which variant has test data
                    import dashboard
                    minipack3ba_dates = dashboard.list_dashboard_dates('MINIPACK3BA')
                    minipack3n_dates = dashboard.list_dashboard_dates('MINIPACK3N')
                    
                    if minipack3ba_dates:
                        detected_platform = 'MINIPACK3BA'
                        logger.info(f"[STARTUP] MINIPACK3 mapped to MINIPACK3BA (has test data)")
                    elif minipack3n_dates:
                        detected_platform = 'MINIPACK3N'
                        logger.info(f"[STARTUP] MINIPACK3 mapped to MINIPACK3N (has test data)")
                    else:
                        # Default to BA if no test data exists for either
                        detected_platform = 'MINIPACK3BA'
                        logger.info(f"[STARTUP] MINIPACK3 mapped to MINIPACK3BA (default)")
                elif product_name in PLATFORMS:
                    detected_platform = product_name
                else:
                    logger.warning(f"[STARTUP] Warning: Unknown product name '{product_name}' from FRUID")
            else:
                logger.warning(f"[STARTUP] Warning: 'Product Name' not found in FRUID JSON")
    except FileNotFoundError:
        logger.warning(f"[STARTUP] FRUID file not found: {fruid_path}")
    except json.JSONDecodeError as e:
        logger.error(f"[STARTUP] Error parsing FRUID JSON: {e}")
    except Exception as e:
        logger.error(f"[STARTUP] Error reading FRUID file: {e}")

    # Fallback: detect from working directory path if FRUID read failed
    if not detected_platform:
        logger.info(f"[STARTUP] Falling back to path-based detection")
        cwd_upper = cwd.upper()

        if 'MP3N' in cwd_upper or 'MINIPACK3N' in cwd_upper:
            detected_platform = 'MINIPACK3N'
        elif 'MP3BA' in cwd_upper or 'MINIPACK3BA' in cwd_upper or 'MONTBLANC' in cwd_upper:
            detected_platform = 'MINIPACK3BA'
        elif 'WEDGE800BA' in cwd_upper or 'W800BA' in cwd_upper:
            detected_platform = 'WEDGE800BACT'
        elif 'WEDGE800CA' in cwd_upper or 'W800CA' in cwd_upper:
            detected_platform = 'WEDGE800CACT'
        else:
            # Default to MINIPACK3N if can't detect
            detected_platform = 'MINIPACK3N'
            logger.warning(f"[STARTUP] Warning: Could not detect platform from path, using default")

        logger.info(f"[STARTUP] Detected platform from path: {detected_platform}")

    logger.info(f"[STARTUP] Working directory: {cwd}")

    # Write to cache file
    try:
        cache_path = os.path.join(cwd, PLATFORM_CACHE_FILE)
        with open(cache_path, 'w') as f:
            f.write(detected_platform)
        logger.info(f"[STARTUP] Cached platform to: {cache_path}")
    except PermissionError:
        logger.error(f"[STARTUP] Error: No write permission for cache file: {cache_path}")
    except Exception as e:
        logger.error(f"[STARTUP] Error writing platform cache: {e}")

    return detected_platform

def get_cached_platform():
    """Read platform from cache file."""
    try:
        cache_path = os.path.join(os.getcwd(), PLATFORM_CACHE_FILE)
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                platform = f.read().strip()
                
                # Handle legacy MINIPACK3 - map to correct variant
                if platform == 'MINIPACK3':
                    logger.info(f"[API] Found legacy platform 'MINIPACK3' in cache, re-detecting...")
                    # Re-detect and update cache
                    detected_platform = detect_and_cache_current_platform()
                    return detected_platform
                
                if platform in PLATFORMS:
                    return platform
                else:
                    logger.warning(f"[API] Warning: Invalid platform '{platform}' in cache file")
    except Exception as e:
        logger.error(f"[API] Error reading platform cache: {e}")
    return None


def is_lab_monitor_mode():
    """
    Determine if application is running in Lab Monitor mode.
    Lab Monitor mode is enabled when FRUID file is not found (not on a supported platform).
    """
    fruid_path = '/var/facebook/fboss/fruid.json'
    
    # If FRUID file doesn't exist, we're in Lab Monitor mode
    if not os.path.exists(fruid_path):
        return True
    
    try:
        # Try to read and validate FRUID
        with open(fruid_path, 'r') as f:
            fruid_data = json.load(f)
            product_name = fruid_data.get('Information', {}).get('Product Name', '').strip()
            
            # If product name is empty or not in supported platforms, use Lab Monitor mode
            if not product_name or (product_name not in PLATFORMS and product_name != 'MINIPACK3'):
                return True
    except Exception as e:
        logger.info(f"[LAB_MONITOR] Error reading FRUID, enabling Lab Monitor mode: {e}")
        return True
    
    return False


def ensure_switch_config_thrift():
    """Ensure switch_config.thrift exists in fboss_src/, download if not present."""
    thrift_dir = os.path.join(os.getcwd(), 'fboss_src')
    os.makedirs(thrift_dir, exist_ok=True)
    thrift_path = os.path.join(thrift_dir, 'switch_config.thrift')
    
    if not os.path.isfile(thrift_path):
        try:
            url = 'https://raw.githubusercontent.com/facebook/fboss/main/fboss/agent/switch_config.thrift'
            curl = shutil.which('curl')
            if curl:
                proc = subprocess.run([curl, '-fsSL', '-o', thrift_path, url], 
                                    capture_output=True, check=False, text=True, timeout=30)
                if proc.returncode != 0:
                    raise RuntimeError(f'curl failed: {proc.returncode} {proc.stderr}')
            else:
                wget = shutil.which('wget')
                if wget:
                    proc = subprocess.run([wget, '-q', '-O', thrift_path, url], 
                                        capture_output=True, check=False, text=True, timeout=30)
                    if proc.returncode != 0:
                        raise RuntimeError(f'wget failed: {proc.returncode} {proc.stderr}')
                else:
                    raise RuntimeError('neither curl nor wget found')
        except Exception as e:
            logger.warning(f'Warning: Could not download switch_config.thrift: {e}')
    
    return thrift_path if os.path.isfile(thrift_path) else None


def calculate_profile_stats(connections):
    """Calculate statistics by profile ID.
    
    Returns dict with:
      - profile_stats: {profile_id: {name: str, count: int, short_name: str}}
      - total_optical: int
      - total_copper: int
      - total_unknown: int
    """
    profile_counts = {}
    total_optical = 0
    total_copper = 0
    total_unknown = 0
    
    for conn in connections:
        profile_id = conn.get('profileID')
        
        # Count by profile ID
        if profile_id is not None:
            if profile_id not in profile_counts:
                profile_counts[profile_id] = 0
            profile_counts[profile_id] += 1
            
            # Count optical vs copper
            profile_name = PROFILE_ID_MAP.get(profile_id, f"UNKNOWN_{profile_id}")
            if '_OPTICAL' in profile_name:
                total_optical += 1
            elif '_COPPER' in profile_name:
                total_copper += 1
            else:
                total_unknown += 1
        else:
            total_unknown += 1
    
    # Build profile stats with names
    profile_stats = {}
    for profile_id, count in profile_counts.items():
        profile_name = PROFILE_ID_MAP.get(profile_id, f"UNKNOWN_{profile_id}")
        # Create short name like P39, P23, etc
        short_name = f"P{profile_id}"
        profile_stats[profile_id] = {
            'name': profile_name,
            'count': count,
            'short_name': short_name
        }
    
    return {
        'profile_stats': profile_stats,
        'total_optical': total_optical,
        'total_copper': total_copper,
        'total_unknown': total_unknown
    }


# Mapping platform -> (filename, fallback raw URL)
PLATFORMS = {
    'MINIPACK3N': ('minipack3n.materialized_JSON',
                   'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/minipack3n.materialized_JSON'),
    'MINIPACK3BA': ('montblanc.materialized_JSON',
                    'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/montblanc.materialized_JSON'),
    'WEDGE800BACT': ('wedge800bact.materialized_JSON',
                     'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/wedge800bact.materialized_JSON'),
    # wedge800cact materialized JSON not present in upstream repo; fall back to wedge800bact
    'WEDGE800CACT': ('wedge800bact.materialized_JSON',
                     'https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/wedge800bact.materialized_JSON')
}


def get_platform_name():
    """Detect platform name from fruid.json file."""
    fruid_path = '/var/facebook/fboss/fruid.json'
    if not os.path.isfile(fruid_path):
        logger.warning(f'[get_platform_name] fruid.json not found at {fruid_path}')
        return None
    
    try:
        with open(fruid_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        info = data.get('Information') or {}
        prod = info.get('Product Name') or info.get('Product') or info.get('ProductName')
        
        if isinstance(prod, str):
            product = prod.strip().upper()
            
            # Map product names to platform names
            if product in ('MINIPACK3', 'MINIPACK3BA'):
                return 'MINIPACK3BA'
            elif product == 'MINIPACK3N':
                return 'MINIPACK3N'
            elif product == 'WEDGE800BACT':
                return 'WEDGE800BACT'
            elif product == 'WEDGE800CACT':
                return 'WEDGE800CACT'
        
        logger.warning(f'[get_platform_name] Unknown product name: {prod}')
        return None
    except Exception as e:
        logger.error(f'[get_platform_name] Error reading fruid: {e}')
        return None


def ensure_topology_file(platform):
    """Ensure the materialized_JSON file exists under Topology/<platform>/; if not, fetch fallback."""
    platform = platform.upper()
    if platform not in PLATFORMS:
        raise FileNotFoundError(f'Unknown platform: {platform}')

    filename, fallback_url = PLATFORMS[platform]
    base_dir = os.path.join(os.getcwd(), 'Topology', platform)
    os.makedirs(base_dir, exist_ok=True)
    file_path = os.path.join(base_dir, filename)

    if not os.path.isfile(file_path):
        # Try to fetch fallback using system tools (no external 'requests' package)
        try:
            def fetch_url_text(url):
                # Prefer curl, then wget. Return text on success or raise.
                curl = shutil.which('curl')
                if curl:
                    proc = subprocess.run([curl, '-fsSL', url], capture_output=True, check=False, text=True, timeout=30)
                    if proc.returncode == 0:
                        return proc.stdout
                    raise RuntimeError(f'curl failed: {proc.returncode} {proc.stderr}')

                wget = shutil.which('wget')
                if wget:
                    proc = subprocess.run([wget, '-qO-', url], capture_output=True, check=False, text=True, timeout=30)
                    if proc.returncode == 0:
                        return proc.stdout
                    raise RuntimeError(f'wget failed: {proc.returncode} {proc.stderr}')

                raise RuntimeError('neither curl nor wget found; please install one to fetch fallback topology')

            content = fetch_url_text(fallback_url)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise FileNotFoundError(f'Could not obtain topology for {platform}: {e}')

    return file_path


def parse_materialized_json(path):
    """Parse materialized_JSON and extract connections.

    Returns list of dicts: {src: 'eth1/x/x', dst: 'eth1/y/y', profileID: <value or null>}
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    conns = []
    seen = set()

    # Support different schemas. Some files put interfaces at top-level
    # under 'interfaces'/'ifaces', others nest them under 'pimInfo' entries.
    interfaces = {}

    # Prefer pimInfo -> interfaces when present
    pim_info = data.get('pimInfo') or data.get('pims')
    if isinstance(pim_info, list):
        for pim in pim_info:
            if not isinstance(pim, dict):
                continue
            ifaces = pim.get('interfaces') or pim.get('ifaces') or {}
            # convert list form to dict if needed
            if isinstance(ifaces, list):
                tmp = {}
                for item in ifaces:
                    if isinstance(item, dict):
                        k = item.get('ifname') or item.get('name')
                        if k:
                            tmp[k] = item
                ifaces = tmp
            if isinstance(ifaces, dict):
                interfaces.update(ifaces)

    # Fallback to top-level interfaces
    if not interfaces:
        interfaces = data.get('interfaces') or data.get('ifaces') or {}
        # interfaces might be a list or dict
        if isinstance(interfaces, list):
            tmp = {}
            for item in interfaces:
                if isinstance(item, dict):
                    k = item.get('ifname') or item.get('name')
                    if k:
                        tmp[k] = item
            interfaces = tmp

    if not isinstance(interfaces, dict):
        interfaces = {}

    for ifname, info in interfaces.items():
        try:
            src = ifname
            # info may be a dict or string
            profile = None
            neighbor_if = None

            if isinstance(info, dict):
                # try common keys
                profile = info.get('profileID') or info.get('profile_id') or info.get('profile') or info.get('profileId')

                # neighbor could live under 'neighbor' or 'remote' etc.
                nbr = info.get('neighbor') or info.get('remote') or info.get('peer') or info.get('linkPeer')
                if isinstance(nbr, str):
                    neighbor_if = nbr
                elif isinstance(nbr, dict):
                    neighbor_if = nbr.get('ifname') or nbr.get('interface') or nbr.get('if_name') or nbr.get('port')

                # some schemas put 'neighbors' as dict mapping to objects
                if not neighbor_if:
                    # search for any key named like eth1/... in nested dicts
                    def find_if(d):
                        if isinstance(d, dict):
                            for k, v in d.items():
                                if isinstance(k, str) and k.startswith('eth'):
                                    return k
                                res = find_if(v)
                                if res:
                                    return res
                        return None
                    neighbor_if = neighbor_if or find_if(info)

            # skip if no neighbor
            if not neighbor_if:
                continue

            # normalize src and dst as strings
            src = str(src)
            dst = str(neighbor_if)

            key = '-'.join(sorted([src, dst]))
            if key in seen:
                continue
            seen.add(key)
            conns.append({'src': src, 'dst': dst, 'profileID': profile})
        except Exception:
            continue

    return conns


@app.route('/')
def index():
    # Check for manual mode override via query parameter
    force_mode = request.args.get('mode', None)
    
    if force_mode == 'normal':
        # Force normal mode (NUI)
        if os.path.isfile('NUI.html'):
            response = send_from_directory(os.getcwd(), 'NUI.html')
            # Add aggressive cache-busting headers
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        return '<h3>NUI not found. Place NUI.html in the server root.</h3>'
    
    elif force_mode == 'monitor':
        # Force Lab Monitor mode
        if os.path.isfile('templates/lab_monitor.html'):
            response = app.make_response(render_template('lab_monitor.html'))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            return '<h3>Lab Monitor dashboard not found.</h3>'
    
    # Auto-detect mode based on FRUID
    if is_lab_monitor_mode():
        # Redirect to Lab Monitor dashboard
        if os.path.isfile('templates/lab_monitor.html'):
            response = app.make_response(render_template('lab_monitor.html'))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            return '<h3>Lab Monitor mode detected. Dashboard not yet configured.</h3>'
    
    # serve existing NUI.html in workspace root for normal mode
    if os.path.isfile('NUI.html'):
        response = send_from_directory(os.getcwd(), 'NUI.html')
        # Add aggressive cache-busting headers
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return '<h3>NUI not found. Place NUI.html in the server root.</h3>'


@app.route('/lab_monitor')
def lab_monitor_page():
    """Serve the Lab Monitor Dashboard."""
    if not os.path.exists('templates'):
        os.makedirs('templates', exist_ok=True)
    if not os.path.isfile('templates/lab_monitor.html'):
        return "<h3>lab_monitor.html not found.</h3>"
    response = app.make_response(render_template('lab_monitor.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/dashboard')
def dashboard_page():
    """Serve the Test Report Dashboard."""
    # Ensure templates folder exists and dashboard.html is in it
    if not os.path.exists('templates'):
        os.makedirs('templates', exist_ok=True)
    if not os.path.isfile('templates/dashboard.html'):
        return "<h3>dashboard.html not found.</h3>"
    response = app.make_response(render_template('dashboard.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/lldp_dashboard')
def lldp_dashboard_page():
    """Serve the LLDP Discovery Dashboard."""
    if not os.path.exists('templates'):
        os.makedirs('templates', exist_ok=True)
    if not os.path.isfile('templates/lldp_dashboard.html'):
        return "<h3>lldp_dashboard.html not found.</h3>"
    response = app.make_response(render_template('lldp_dashboard.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/api/lldp/interfaces')
def api_lldp_interfaces():
    """Get list of available network interfaces."""
    try:
        interfaces = lldp_discovery.get_network_interfaces()
        return jsonify({'interfaces': interfaces})
    except Exception as e:
        return jsonify({'error': str(e), 'interfaces': ['eth0']}), 500


@app.route('/api/lldp/topology')
def api_lldp_topology():
    """Get LLDP topology information."""
    interface = request.args.get('interface', None)
    try:
        topology = lldp_discovery.get_lldp_neighbors(interface)
        local_info = lldp_discovery.get_local_system_info()
        topology['local_info'] = local_info
        return jsonify(topology)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lldp/debug')
def api_lldp_debug():
    """Get LLDP debug information."""
    interface = request.args.get('interface', None)
    try:
        debug_info = lldp_discovery.get_lldp_debug_info(interface)
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lldp/configure', methods=['POST'])
def api_lldp_configure():
    """Configure LLDP transmission settings."""
    try:
        data = request.get_json()
        interface = data.get('interface', 'eth0')
        enable_tx = data.get('enable_tx', True)
        
        result = lldp_discovery.configure_lldp_tx(interface, enable_tx)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lldp/status')
def api_lldp_status():
    """Get LLDP status and statistics."""
    interface = request.args.get('interface', None)
    try:
        status = lldp_discovery.get_lldp_status(interface)
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Lab Monitor API Routes
# =============================================================================

@app.route('/api/lab_monitor/mode')
def api_lab_monitor_mode():
    """Check if running in Lab Monitor mode."""
    return jsonify({'lab_monitor_mode': is_lab_monitor_mode()})


@app.route('/api/lab_monitor/config')
def api_lab_monitor_config():
    """Get complete lab configuration."""
    config = lab_monitor.load_lab_config()
    return jsonify(config)


@app.route('/api/lab_monitor/status')
def api_lab_monitor_status():
    """Get all DUT statuses."""
    status = lab_monitor.get_all_dut_statuses()
    return jsonify(status)


@app.route('/api/lab_monitor/lab', methods=['POST'])
def api_lab_monitor_add_lab():
    """Add a new lab group."""
    data = request.get_json()
    lab_name = data.get('name', '')
    description = data.get('description', '')
    
    if not lab_name:
        return jsonify({'success': False, 'error': 'Lab name is required'}), 400
    
    result = lab_monitor.add_lab(lab_name, description)
    return jsonify(result)


@app.route('/api/lab_monitor/lab/<lab_id>', methods=['PUT'])
def api_lab_monitor_update_lab(lab_id):
    """Update an existing lab group."""
    data = request.get_json()
    result = lab_monitor.update_lab(
        lab_id,
        data.get('name'),
        data.get('description')
    )
    return jsonify(result)


@app.route('/api/lab_monitor/lab/<lab_id>', methods=['DELETE'])
def api_lab_monitor_delete_lab(lab_id):
    """Delete a lab group."""
    result = lab_monitor.delete_lab(lab_id)
    return jsonify(result)


@app.route('/api/lab_monitor/platform', methods=['POST'])
def api_lab_monitor_add_platform():
    """Add a platform to a lab."""
    data = request.get_json()
    lab_id = data.get('lab_id', '')
    platform_name = data.get('name', '')
    description = data.get('description', '')
    
    if not lab_id or not platform_name:
        return jsonify({'success': False, 'error': 'Lab ID and platform name are required'}), 400
    
    result = lab_monitor.add_platform(lab_id, platform_name, description)
    return jsonify(result)


@app.route('/api/lab_monitor/platform/<lab_id>/<platform_id>', methods=['PUT'])
def api_lab_monitor_update_platform(lab_id, platform_id):
    """Update an existing platform."""
    data = request.get_json()
    result = lab_monitor.update_platform(
        lab_id,
        platform_id,
        data.get('name'),
        data.get('description')
    )
    return jsonify(result)


@app.route('/api/lab_monitor/platform/<lab_id>/<platform_id>', methods=['DELETE'])
def api_lab_monitor_delete_platform(lab_id, platform_id):
    """Delete a platform from a lab."""
    result = lab_monitor.delete_platform(lab_id, platform_id)
    return jsonify(result)


@app.route('/api/lab_monitor/platform/move', methods=['POST'])
def api_lab_monitor_move_platform():
    """Move a platform from one lab to another."""
    data = request.get_json()
    source_lab_id = data.get('source_lab_id', '')
    target_lab_id = data.get('target_lab_id', '')
    platform_id = data.get('platform_id', '')
    
    if not source_lab_id or not target_lab_id or not platform_id:
        return jsonify({'success': False, 'error': 'Source lab, target lab, and platform ID are required'}), 400
    
    result = lab_monitor.move_platform(source_lab_id, target_lab_id, platform_id)
    return jsonify(result)


@app.route('/api/lab_monitor/platform/copy', methods=['POST'])
def api_lab_monitor_copy_platform():
    """Copy a platform from one lab to another."""
    data = request.get_json()
    source_lab_id = data.get('source_lab_id', '')
    target_lab_id = data.get('target_lab_id', '')
    platform_id = data.get('platform_id', '')
    
    if not source_lab_id or not target_lab_id or not platform_id:
        return jsonify({'success': False, 'error': 'Source lab, target lab, and platform ID are required'}), 400
    
    result = lab_monitor.copy_platform(source_lab_id, target_lab_id, platform_id)
    return jsonify(result)


@app.route('/api/lab_monitor/dut', methods=['POST'])
def api_lab_monitor_add_dut():
    """Add a DUT to a platform."""
    data = request.get_json()
    lab_id = str(data.get('lab_id', '')).strip()
    platform_id = str(data.get('platform_id', '')).strip()
    
    # Safely extract and validate name - handle objects, None, empty strings
    name_raw = data.get('name')
    if isinstance(name_raw, dict) or name_raw is None or str(name_raw).strip() == '':
        dut_name = ''
    else:
        dut_name = str(name_raw).strip()
    
    # Safely extract other fields
    ip_raw = data.get('ip_address')
    ip_address = '' if (isinstance(ip_raw, dict) or ip_raw is None) else str(ip_raw).strip()
    
    config_raw = data.get('config_type', 'Config A')
    config_type = 'Config A' if (isinstance(config_raw, dict) or config_raw is None) else str(config_raw).strip()
    
    desc_raw = data.get('description')
    description = '' if (isinstance(desc_raw, dict) or desc_raw is None) else str(desc_raw).strip()
    
    pass_raw = data.get('password')
    password = '' if (isinstance(pass_raw, dict) or pass_raw is None) else str(pass_raw).strip()
    
    if not lab_id or not platform_id or not dut_name:
        return jsonify({'success': False, 'error': 'Lab ID, platform ID, and DUT name are required'}), 400
    
    result = lab_monitor.add_dut(lab_id, platform_id, dut_name, ip_address, config_type, description, password)
    return jsonify(result)


@app.route('/api/lab_monitor/dut/<lab_id>/<platform_id>/<dut_id>', methods=['PUT'])
def api_lab_monitor_update_dut(lab_id, platform_id, dut_id):
    """Update an existing DUT."""
    data = request.get_json()
    # Safely convert all string fields, handling None and objects
    name = str(data.get('name')).strip() if data.get('name') else None
    ip_address = str(data.get('ip_address')).strip() if data.get('ip_address') else None
    config_type = str(data.get('config_type')).strip() if data.get('config_type') else None
    description = str(data.get('description')).strip() if data.get('description') else None
    password = str(data.get('password', '')).strip() if data.get('password') else ''
    
    result = lab_monitor.update_dut(
        lab_id,
        platform_id,
        dut_id,
        name,
        ip_address,
        config_type,
        description,
        password
    )
    return jsonify(result)


@app.route('/api/lab_monitor/dut/<lab_id>/<platform_id>/<dut_id>', methods=['DELETE'])
def api_lab_monitor_delete_dut(lab_id, platform_id, dut_id):
    """Delete a DUT from a platform."""
    result = lab_monitor.delete_dut(lab_id, platform_id, dut_id)
    return jsonify(result)


@app.route('/api/lab_monitor/dut/move', methods=['POST'])
def api_lab_monitor_move_dut():
    """Move a DUT from one platform to another."""
    data = request.get_json()
    source_platform_id = data.get('source_platform_id', '')
    target_platform_id = data.get('target_platform_id', '')
    dut_id = data.get('dut_id', '')
    
    if not source_platform_id or not target_platform_id or not dut_id:
        return jsonify({'success': False, 'error': 'Source platform, target platform, and DUT ID are required'}), 400
    
    result = lab_monitor.move_dut(source_platform_id, target_platform_id, dut_id)
    return jsonify(result)


@app.route('/api/lab_monitor/dut/copy', methods=['POST'])
def api_lab_monitor_copy_dut():
    """Copy a DUT from one platform to another."""
    data = request.get_json()
    source_platform_id = data.get('source_platform_id', '')
    target_platform_id = data.get('target_platform_id', '')
    dut_id = data.get('dut_id', '')
    
    if not source_platform_id or not target_platform_id or not dut_id:
        return jsonify({'success': False, 'error': 'Source platform, target platform, and DUT ID are required'}), 400
    
    result = lab_monitor.copy_dut(source_platform_id, target_platform_id, dut_id)
    return jsonify(result)


@app.route('/api/lab_monitor/dut/<dut_id>/status', methods=['POST'])
def api_lab_monitor_update_dut_status(dut_id):
    """Update DUT status."""
    data = request.get_json()
    status = data.get('status', 'unknown')
    last_seen = data.get('last_seen')
    
    result = lab_monitor.update_dut_status(dut_id, status, last_seen)
    return jsonify(result)


@app.route('/api/lab_monitor/dut/<dut_id>/status', methods=['GET'])
def api_lab_monitor_get_dut_status(dut_id):
    """Get DUT status."""
    status = lab_monitor.get_dut_status(dut_id)
    return jsonify(status)


@app.route('/api/lab_monitor/dut/<dut_id>/testing', methods=['GET'])
def api_lab_monitor_check_testing(dut_id):
    """Check if DUT is currently running tests by calling DUT's local API."""
    try:
        config = lab_monitor.load_lab_config()
        dut_info = None
        
        for lab in config.get('labs', []):
            for platform in lab.get('platforms', []):
                for dut in platform.get('duts', []):
                    if dut.get('id') == dut_id:
                        dut_info = dut
                        break
                if dut_info:
                    break
            if dut_info:
                break
        
        if not dut_info:
            return jsonify({'success': False, 'testing': False, 'error': 'DUT not found'}), 404
        
        ip_address = dut_info.get('ip_address', '').strip()
        if not ip_address:
            return jsonify({'success': True, 'testing': False, 'error': 'No IP address'})
        
        # Call DUT's local API to check testing status
        dut_api_url = f"http://{ip_address}:5000/api/dut/testing/status"
        
        try:
            response = requests.get(dut_api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return jsonify({
                    'success': True,
                    'testing': data.get('testing', False),
                    'processes': data.get('processes', []),
                    'process_count': data.get('process_count', 0),
                    'dut_id': dut_id,
                    'timestamp': data.get('timestamp')
                })
            else:
                return jsonify({
                    'success': False,
                    'testing': False,
                    'error': f'DUT API returned status {response.status_code}',
                    'dut_id': dut_id
                })
        except requests.exceptions.Timeout:
            return jsonify({
                'success': False,
                'testing': False,
                'error': 'DUT API timeout',
                'dut_id': dut_id
            })
        except requests.exceptions.ConnectionError:
            return jsonify({
                'success': False,
                'testing': False,
                'error': 'Cannot connect to DUT API',
                'dut_id': dut_id
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'testing': False,
                'error': f'DUT API error: {str(e)}',
                'dut_id': dut_id
            })
            
    except Exception as e:
        return jsonify({'success': False, 'testing': False, 'error': str(e)})


@app.route('/api/lab_monitor/testing/check', methods=['POST'])
def api_lab_monitor_check_testing_by_ip():
    """Check if a device is testing by IP address or DUT ID using DUT's local API.
    
    Request body:
    {
        "ip_address": "172.16.2.76",  // Optional
        "dut_id": "AP29047232"         // Optional
    }
    
    Response:
    {
        "success": true,
        "testing": true,
        "processes": ["/opt/fboss/bin/wedge_agent"],
        "process_count": 1,
        "dut_id": "AP29047232",
        "ip_address": "172.16.2.76"
    }
    """
    try:
        data = request.get_json() or {}
        ip_address = data.get('ip_address', '').strip()
        dut_id = data.get('dut_id', '').strip()
        
        # If DUT ID provided, get IP from config
        if dut_id and not ip_address:
            config = lab_monitor.load_lab_config()
            for lab in config.get('labs', []):
                for platform in lab.get('platforms', []):
                    for dut in platform.get('duts', []):
                        if dut.get('id') == dut_id:
                            ip_address = dut.get('ip_address', '').strip()
                            break
        
        if not ip_address:
            return jsonify({'success': False, 'error': 'IP address or DUT ID required'}), 400
        
        # Call DUT's local API
        dut_api_url = f"http://{ip_address}:5000/api/dut/testing/status"
        
        try:
            response = requests.get(dut_api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return jsonify({
                    'success': True,
                    'testing': data.get('testing', False),
                    'processes': data.get('processes', []),
                    'process_count': data.get('process_count', 0),
                    'dut_id': dut_id if dut_id else None,
                    'ip_address': ip_address,
                    'timestamp': data.get('timestamp')
                })
            else:
                return jsonify({
                    'success': False,
                    'testing': False,
                    'error': f'DUT API returned status {response.status_code}',
                    'ip_address': ip_address
                }), response.status_code
        except requests.exceptions.Timeout:
            return jsonify({
                'success': False,
                'testing': False,
                'error': 'DUT API timeout',
                'ip_address': ip_address
            }), 504
        except requests.exceptions.ConnectionError:
            return jsonify({
                'success': False,
                'testing': False,
                'error': 'Cannot connect to DUT API',
                'ip_address': ip_address
            }), 503
        except Exception as e:
            return jsonify({
                'success': False,
                'testing': False,
                'error': f'DUT API error: {str(e)}',
                'ip_address': ip_address
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/testing/check_all', methods=['GET'])
def api_lab_monitor_check_all_testing():
    """Check testing status for all DUTs using their local APIs.
    
    Response:
    {
        "success": true,
        "total": 5,
        "testing_count": 2,
        "duts": [
            {
                "dut_id": "AP29047232",
                "name": "Device 1",
                "ip_address": "172.16.2.76",
                "testing": true,
                "platform": "MINIPACK3BA",
                "processes": ["/opt/fboss/bin/wedge_agent"],
                "process_count": 1
            },
            ...
        ]
    }
    """
    try:
        config = lab_monitor.load_lab_config()
        results = []
        testing_count = 0
        
        for lab in config.get('labs', []):
            for platform in lab.get('platforms', []):
                platform_name = platform.get('name', 'Unknown')
                for dut in platform.get('duts', []):
                    dut_id = dut.get('id', '')
                    dut_name = dut.get('name', '')
                    ip_address = dut.get('ip_address', '').strip()
                    
                    if not ip_address:
                        results.append({
                            'dut_id': dut_id,
                            'name': dut_name,
                            'ip_address': None,
                            'testing': False,
                            'platform': platform_name,
                            'error': 'No IP address'
                        })
                        continue
                    
                    # Call DUT's local API
                    dut_api_url = f"http://{ip_address}:5000/api/dut/testing/status"
                    
                    try:
                        response = requests.get(dut_api_url, timeout=3)
                        if response.status_code == 200:
                            data = response.json()
                            is_testing = data.get('testing', False)
                            if is_testing:
                                testing_count += 1
                            
                            results.append({
                                'dut_id': dut_id,
                                'name': dut_name,
                                'ip_address': ip_address,
                                'testing': is_testing,
                                'platform': platform_name,
                                'processes': data.get('processes', []),
                                'process_count': data.get('process_count', 0)
                            })
                        else:
                            results.append({
                                'dut_id': dut_id,
                                'name': dut_name,
                                'ip_address': ip_address,
                                'testing': False,
                                'platform': platform_name,
                                'error': f'API returned status {response.status_code}'
                            })
                    except requests.exceptions.Timeout:
                        results.append({
                            'dut_id': dut_id,
                            'name': dut_name,
                            'ip_address': ip_address,
                            'testing': False,
                            'platform': platform_name,
                            'error': 'API timeout'
                        })
                    except requests.exceptions.ConnectionError:
                        results.append({
                            'dut_id': dut_id,
                            'name': dut_name,
                            'ip_address': ip_address,
                            'testing': False,
                            'platform': platform_name,
                            'error': 'Cannot connect to API'
                        })
                    except Exception as e:
                        results.append({
                            'dut_id': dut_id,
                            'name': dut_name,
                            'ip_address': ip_address,
                            'testing': False,
                            'platform': platform_name,
                            'error': str(e)
                        })
        
        return jsonify({
            'success': True,
            'total': len(results),
            'testing_count': testing_count,
            'duts': results
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/status/check_all', methods=['POST'])
def api_lab_monitor_check_all_status():
    """Manually trigger status check for all DUTs."""
    try:
        result = lab_monitor.update_all_dut_statuses()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/dut/<dut_id>/check', methods=['POST'])
def api_lab_monitor_check_dut(dut_id):
    """Manually trigger status check for a single DUT."""
    try:
        result = lab_monitor.check_single_dut(dut_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/status/checker', methods=['GET'])
def api_lab_monitor_checker_info():
    """Get background status checker information."""
    info = lab_monitor.get_status_checker_info()
    return jsonify(info)


@app.route('/api/lab_monitor/status/checker/interval', methods=['PUT'])
def api_lab_monitor_update_status_interval():
    """Update the status checker interval."""
    try:
        data = request.get_json()
        if not data or 'interval' not in data:
            return jsonify({'success': False, 'error': 'Missing interval parameter'}), 400
        
        interval = int(data['interval'])
        result = lab_monitor.update_status_checker_interval(interval)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid interval value'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/report/checker', methods=['GET'])
def api_lab_monitor_report_checker_info():
    """Get background report checker information."""
    info = lab_monitor.get_report_checker_info()
    return jsonify(info)


@app.route('/api/lab_monitor/report/checker/interval', methods=['PUT'])
def api_lab_monitor_update_report_interval():
    """Update the report checker interval."""
    try:
        data = request.get_json()
        if not data or 'interval' not in data:
            return jsonify({'success': False, 'error': 'Missing interval parameter'}), 400
        
        interval = int(data['interval'])
        result = lab_monitor.update_report_checker_interval(interval)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid interval value'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/version', methods=['GET'])
def api_get_version():
    """Get current NUI version."""
    try:
        with open('VERSION', 'r') as f:
            version = f.read().strip()
        return jsonify({'version': version})
    except Exception as e:
        return jsonify({'version': 'unknown', 'error': str(e)})


@app.route('/api/lab_monitor/dut/<dut_id>/version', methods=['GET'])
def api_lab_monitor_get_dut_version(dut_id):
    """Get version from a specific DUT."""
    try:
        # Find DUT's IP address
        config = lab_monitor.load_lab_config()
        ip_address = None
        
        for lab in config.get('labs', []):
            for platform in lab.get('platforms', []):
                for dut in platform.get('duts', []):
                    if dut.get('id') == dut_id:
                        ip_address = dut.get('ip_address', '').strip()
                        break
                if ip_address:
                    break
            if ip_address:
                break
        
        if not ip_address:
            return jsonify({'success': False, 'error': 'DUT not found or no IP address', 'version': 'unknown'})
        
        result = lab_monitor.update_dut_version(dut_id, ip_address)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'version': 'unknown'}), 500


@app.route('/api/lab_monitor/versions/check_all', methods=['POST'])
def api_lab_monitor_check_all_versions():
    """Check versions for all DUTs."""
    try:
        result = lab_monitor.get_all_dut_versions()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/reports/check_all', methods=['POST'])
def api_lab_monitor_check_all_reports():
    """Check all DUTs for new reports."""
    try:
        result = lab_monitor.check_all_dut_reports()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/dut/<dut_id>/reports/check', methods=['POST'])
def api_lab_monitor_check_dut_reports(dut_id):
    """Check a specific DUT for new reports."""
    try:
        # Find DUT info from config
        config = lab_monitor.load_lab_config()
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
        
        if not dut_info:
            return jsonify({'success': False, 'error': 'DUT not found'}), 404
        
        result = lab_monitor.check_dut_reports(
            dut_id,
            dut_info.get('ip_address', ''),
            platform_name,
            lab_name,
            dut_info.get('name', ''),
            dut_info.get('password', '')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/dut/<dut_id>/reports/sync', methods=['POST'])
def api_lab_monitor_sync_dut_report(dut_id):
    """Sync a specific report from a DUT."""
    try:
        data = request.get_json()
        date = data.get('date')
        
        if not date:
            return jsonify({'success': False, 'error': 'Date is required'}), 400
        
        # Find DUT info from config
        config = lab_monitor.load_lab_config()
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
        
        if not dut_info:
            return jsonify({'success': False, 'error': 'DUT not found'}), 404
        
        # Start sync as background task (default to directory mode, not tarball)
        sync_task_id = lab_monitor.start_sync_task(
            dut_id,
            dut_info.get('ip_address', ''),
            platform_name,
            date,
            lab_name,
            dut_info.get('name', ''),
            dut_info.get('password', ''),  # Pass password for SCP authentication
            is_tarball=False  # Support directory syncing by default
        )
        
        return jsonify({'success': True, 'task_id': sync_task_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/sync/status/<task_id>', methods=['GET'])
def api_lab_monitor_sync_status(task_id):
    """Get the status of a sync task."""
    try:
        status = lab_monitor.get_sync_task_status(task_id)
        return jsonify(status)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/dut/<dut_id>/dashboard/dates', methods=['GET'])
def api_lab_monitor_dut_dashboard_dates(dut_id):
    """Get available dashboard dates for a specific DUT."""
    try:
        # Find DUT information from lab_monitor config
        config = lab_monitor.load_lab_config()
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
            return jsonify({'success': False, 'error': 'DUT not found'}), 404
        
        # Get dates from ALL_DB directory structure
        dut_name = dut_info.get('name', '')
        all_db_path = os.path.join(TEST_REPORT_BASE, 'ALL_DB', lab_name, platform_name, dut_name)
        
        if not os.path.exists(all_db_path):
            return jsonify({'success': True, 'dates': []})
        
        dates = []
        for item in os.listdir(all_db_path):
            if item.startswith("all_test_") and os.path.isdir(os.path.join(all_db_path, item)):
                date_str = item.replace("all_test_", "")
                dates.append(date_str)
        
        dates.sort(reverse=True)  # Most recent first
        return jsonify({'success': True, 'dates': dates})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/dut/<dut_id>/dashboard/summary/<date>', methods=['GET'])
def api_lab_monitor_dut_dashboard_summary(dut_id, date):
    """Get dashboard summary for a specific DUT and date."""
    try:
        # Find DUT information from lab_monitor config
        config = lab_monitor.load_lab_config()
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
            return jsonify({'success': False, 'error': 'DUT not found'}), 404
        
        # Get dashboard summary from ALL_DB directory
        dut_name = dut_info.get('name', '')
        target_dir = os.path.join(TEST_REPORT_BASE, 'ALL_DB', lab_name, platform_name, dut_name, f"all_test_{date}")
        
        if not os.path.exists(target_dir):
            return jsonify({'success': False, 'error': 'Report not found'}), 404
        
        # Temporarily modify TEST_REPORT_BASE to point to the DUT-specific path
        import dashboard
        original_base = dashboard.TEST_REPORT_BASE
        try:
            # Set TEST_REPORT_BASE to the parent directory structure
            dashboard.TEST_REPORT_BASE = os.path.join(TEST_REPORT_BASE, 'ALL_DB', lab_name, platform_name, dut_name)
            
            # Now call get_dashboard_summary with an empty platform (since path already includes it)
            summary = dashboard.get_dashboard_summary('', date)
            
            if summary:
                summary['lab_name'] = lab_name
                summary['platform_name'] = platform_name
                summary['dut_name'] = dut_name
                return jsonify({'success': True, 'summary': summary})
            else:
                return jsonify({'success': False, 'error': 'Failed to generate summary'}), 500
        finally:
            dashboard.TEST_REPORT_BASE = original_base
        
    except Exception as e:
        logger.error(f"[ERROR] Failed to get DUT dashboard summary: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab_monitor/dut/<dut_id>/trend/<end_date>')
def api_lab_monitor_dut_all_trend(dut_id, end_date):
    """Get all tests trend data for a specific DUT."""
    try:
        # Load lab configuration
        lab_config = lab_monitor.load_lab_config()
        
        # Find DUT info
        dut_info = None
        lab_name = None
        platform_name = None
        
        for lab in lab_config.get('labs', []):
            for platform in lab.get('platforms', []):
                for dut in platform.get('duts', []):
                    if dut.get('id') == dut_id:
                        dut_info = dut
                        lab_name = lab.get('name')
                        platform_name = platform.get('name')
                        break
                if dut_info:
                    break
            if dut_info:
                break
        
        if not dut_info:
            return jsonify({'error': 'DUT not found'}), 404
        
        # Get DUT details
        dut_name = dut_info.get('name')
        
        # Get range type from query parameter
        range_type = request.args.get('range', 'week')  # week, month, or year
        
        # Temporarily modify dashboard.TEST_REPORT_BASE to point to this DUT's reports
        import dashboard
        original_base = dashboard.TEST_REPORT_BASE
        try:
            # Set base path to DUT's test_report directory
            dashboard.TEST_REPORT_BASE = os.path.join(TEST_REPORT_BASE, 'ALL_DB', lab_name, platform_name, dut_name)
            
            # Use dashboard's get_7day_trend function with empty platform and None for category/level (all tests)
            trend_data = dashboard.get_7day_trend('', end_date, None, None, range_type)
            
            return jsonify(trend_data)
        finally:
            # Restore original base path
            dashboard.TEST_REPORT_BASE = original_base
            
    except Exception as e:
        app.logger.error(f"Error getting all tests trend data for DUT {dut_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/lab_monitor/dut/<dut_id>/trend/<category>/<level>')
@app.route('/api/lab_monitor/dut/<dut_id>/trend/<category>/<level>/<end_date>')
def api_lab_monitor_dut_trend(dut_id, category, level, end_date=None):
    """Get test trend data for a specific DUT's test category and level."""
    try:
        # Load lab configuration
        lab_config = lab_monitor.load_lab_config()
        
        # Find DUT info
        dut_info = None
        lab_name = None
        platform_name = None
        
        for lab in lab_config.get('labs', []):
            for platform in lab.get('platforms', []):
                for dut in platform.get('duts', []):
                    if dut.get('id') == dut_id:
                        dut_info = dut
                        lab_name = lab.get('name')
                        platform_name = platform.get('name')
                        break
                if dut_info:
                    break
            if dut_info:
                break
        
        if not dut_info:
            return jsonify({'error': 'DUT not found'}), 404
        
        # Get DUT details
        dut_name = dut_info.get('name')
        
        # Get range type from query parameter
        range_type = request.args.get('range', 'week')  # week, month, or year
        
        # Temporarily modify dashboard.TEST_REPORT_BASE to point to this DUT's reports
        import dashboard
        original_base = dashboard.TEST_REPORT_BASE
        try:
            # Set base path to DUT's test_report directory
            dashboard.TEST_REPORT_BASE = os.path.join(TEST_REPORT_BASE, 'ALL_DB', lab_name, platform_name, dut_name)
            
            # Use dashboard's get_7day_trend function with empty platform (since we're already in DUT's directory)
            trend_data = dashboard.get_7day_trend('', end_date, category, level, range_type)
            
            return jsonify(trend_data)
        finally:
            # Restore original base path
            dashboard.TEST_REPORT_BASE = original_base
            
    except Exception as e:
        app.logger.error(f"Error getting trend data for DUT {dut_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Lab Monitor Test Log Detail API (similar to dashboard)

@app.route('/api/lab_monitor/test_log_detail/<lab_name>/<platform>/<dut_name>/<date>/<category>/<level>/<path:test_name>')
def api_lab_monitor_test_log_detail(lab_name, platform, dut_name, date, category, level, test_name):
    """Return full log content for a specific test in lab_monitor view, using dashboard logic and split_and_report.py extraction."""
    import dashboard
    # Compose target dir for ALL_DB
    target_dir = os.path.join(TEST_REPORT_BASE, 'ALL_DB', lab_name, platform, dut_name, f"all_test_{date}")
    if not os.path.isdir(target_dir):
        return jsonify({'error': 'Test report directory not found'}), 404
    try:
        # Use dashboard's archive finding logic for category/level mapping
        archive_file = find_test_archive(target_dir, category, level)
        if not archive_file:
            return jsonify({'error': f'Test archive not found for {category}/{level}'}), 404
        # Use dashboard's log extraction logic (split_and_report.py style)
        test_log_content = extract_test_log_from_archive(archive_file, test_name)
        if not test_log_content:
            return jsonify({'error': f'Test log not found: {test_name}'}), 404
        # Determine test status
        status = "UNKNOWN"
        if ("[ FAILED ]" in test_log_content or "[  FAILED  ]" in test_log_content or "FAILED TEST" in test_log_content or "Test FAILED" in test_log_content or "TESTS FAILED" in test_log_content):
            status = "FAIL"
        elif ("[ PASSED ]" in test_log_content or "[  PASSED  ]" in test_log_content or "Test PASSED" in test_log_content or "ALL TESTS PASSED" in test_log_content):
            status = "PASS"
        return jsonify({
            'status': status,
            'log_content': test_log_content,
            'log_size': len(test_log_content)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/lab_monitor/download_organized/<lab_name>/<platform>/<dut_name>/<date>')
@limiter.limit("10 per hour")
def api_lab_monitor_download_organized(lab_name, platform, dut_name, date):
    """Generate organized test report for lab_monitor using organize_test_reports.py and download as tar.gz."""
    from utils.validators import validate_platform, validate_date, is_safe_filename
    
    # Validate inputs
    if not validate_platform(platform):
        logger.warning(f"[API] Invalid platform in download request: {platform}")
        return jsonify({'error': 'Invalid platform'}), 400
    
    if not validate_date(date):
        logger.warning(f"[API] Invalid date in download request: {date}")
        return jsonify({'error': 'Invalid date format'}), 400
    
    if not is_safe_filename(lab_name) or not is_safe_filename(dut_name):
        logger.warning(f"[API] Invalid lab_name or dut_name in download request")
        return jsonify({'error': 'Invalid lab or DUT name'}), 400
    
    import tarfile
    import subprocess
    from io import BytesIO
    
    target_dir = os.path.join(TEST_REPORT_BASE, 'ALL_DB', lab_name, platform, dut_name, f"all_test_{date}")
    
    if not os.path.isdir(target_dir):
        return jsonify({'error': 'Test report directory not found'}), 404
    
    try:
        # Create a temporary directory for organized output
        temp_output_dir = safe_mkdtemp(prefix='organized_report_')
        
        try:
            # Run organize_test_reports.py - it will create the directory structure
            script_path = os.path.join(os.path.dirname(__file__), 'organize_test_reports.py')
            
            logger.info(f'[ORGANIZE LAB_MONITOR] Source: {target_dir}')
            logger.info(f'[ORGANIZE LAB_MONITOR] Output: {temp_output_dir}')
            
            # Check if source directory has .tar.gz files
            tar_gz_files = [f for f in os.listdir(target_dir) if f.endswith('.tar.gz')]
            logger.info(f'[ORGANIZE LAB_MONITOR] Found {len(tar_gz_files)} .tar.gz files in source')
            if tar_gz_files:
                logger.info(f'[ORGANIZE LAB_MONITOR] Files: {tar_gz_files[:5]}')  # Show first 5
            
            result = subprocess.run(
                ['python3', script_path, target_dir, temp_output_dir],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            logger.info(f'[ORGANIZE LAB_MONITOR] Script stdout:\n{result.stdout}')
            if result.stderr:
                logger.warning(f'[ORGANIZE LAB_MONITOR] Script stderr:\n{result.stderr}')
            
            if result.returncode != 0:
                # Check if error message indicates files are being written
                error_msg = result.stderr + result.stdout
                if 'being written' in error_msg or 'modified recently' in error_msg:
                    return jsonify({
                        'error': 'Some test archives are still being created. Please wait until tests complete, then try again.',
                        'details': result.stderr,
                        'is_test_running': True
                    }), 409  # 409 Conflict
                else:
                    return jsonify({
                        'error': 'Failed to organize reports',
                        'details': result.stderr,
                        'stdout': result.stdout
                    }), 500
            
            # Verify files were created - use list to force evaluation
            all_files = []
            for root, dirs, files in os.walk(temp_output_dir):
                for f in files:
                    all_files.append(os.path.join(root, f))
            
            file_count = len(all_files)
            logger.info(f'[ORGANIZE LAB_MONITOR] Generated {file_count} files in output')
            if file_count > 0:
                logger.info(f'[ORGANIZE LAB_MONITOR] Sample files: {all_files[:5]}')
            
            if file_count == 0:
                # Debug: check if directory exists and what's in it
                logger.warning(f'[ORGANIZE LAB_MONITOR] Checking temp_output_dir: {temp_output_dir}')
                logger.warning(f'[ORGANIZE LAB_MONITOR] Directory exists: {os.path.exists(temp_output_dir)}')
                if os.path.exists(temp_output_dir):
                    try:
                        all_items = os.listdir(temp_output_dir)
                        logger.warning(f'[ORGANIZE LAB_MONITOR] Items in directory: {all_items}')
                    except Exception as e:
                        logger.error(f'[ORGANIZE LAB_MONITOR] Error listing directory: {e}')
                
                # Get list of source files for debugging
                source_files = os.listdir(target_dir) if os.path.isdir(target_dir) else []
                return jsonify({
                    'error': 'No files were generated in organized report',
                    'source_files': source_files[:10],  # First 10 files
                    'source_dir': target_dir,
                    'script_output': result.stdout
                }), 500
            
            # Create tar.gz in memory
            memory_file = BytesIO()
            
            with tarfile.open(fileobj=memory_file, mode='w:gz') as tar:
                # Add all files in the temp directory (with organized structure)
                for root, dirs, files in os.walk(temp_output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_output_dir)
                        tar.add(file_path, arcname=arcname)
            
            memory_file.seek(0)
            
            return send_file(
                memory_file,
                mimetype='application/gzip',
                as_attachment=True,
                download_name=f'Organized_Report_{lab_name}_{platform}_{dut_name}_{date}.tar.gz'
            )
        
        finally:
            # Clean up temp directory
            if os.path.exists(temp_output_dir):
                shutil.rmtree(temp_output_dir, ignore_errors=True)
    
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Report organization timed out'}), 500
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in lab_monitor download_organized: {error_details}")
        return jsonify({
            'error': f'Failed to generate organized report: {str(e)}',
            'details': error_details
        }), 500

# End Lab Monitor API Routes
# =============================================================================


@app.route('/api/dashboard/dates/<platform>')
def api_dashboard_dates(platform):
    """Get list of available test dates for a platform."""
    dates = dashboard.list_dashboard_dates(platform)
    return jsonify(dates)


@app.route('/api/dashboard/current_platform')
def api_dashboard_current_platform():
    """Get the current platform from cache file or detect it."""
    
    # First, try to read from cache file
    cached_platform = get_cached_platform()
    if cached_platform:
        logger.info(f"[API] Using cached platform: {cached_platform}")
        return jsonify({'platform': cached_platform, 'has_data': True, 'source': 'cache_file'})
    
    # If cache doesn't exist, try to infer from working directory
    cwd = os.getcwd()
    inferred_platform = None
    
    if 'MP3N' in cwd or 'MINIPACK3N' in cwd.upper():
        inferred_platform = 'MINIPACK3N'
    elif 'MP3BA' in cwd or 'MINIPACK3BA' in cwd.upper() or 'MONTBLANC' in cwd.upper():
        inferred_platform = 'MINIPACK3BA'
    elif 'WEDGE800BA' in cwd.upper() or 'W800BA' in cwd:
        inferred_platform = 'WEDGE800BACT'
    elif 'WEDGE800CA' in cwd.upper() or 'W800CA' in cwd:
        inferred_platform = 'WEDGE800CACT'
    
    if inferred_platform:
        logger.info(f"[API] Inferred platform from working directory: {inferred_platform}")
        return jsonify({'platform': inferred_platform, 'has_data': True, 'source': 'working_directory'})
    
    # If can't infer from path, find the platform with the most recent test data
    platforms = ['MINIPACK3N', 'MINIPACK3BA', 'WEDGE800BACT', 'WEDGE800CACT']
    latest_platform = None
    latest_date = None
    
    for platform in platforms:
        dates = dashboard.list_dashboard_dates(platform)
        if dates:
            # dates are sorted in reverse order (most recent first)
            if latest_date is None or dates[0] > latest_date:
                latest_date = dates[0]
                latest_platform = platform
    
    # If no platform has data, return MINIPACK3N as it's the default in NUI.html
    if latest_platform is None:
        latest_platform = 'MINIPACK3N'
    
    logger.info(f"[API] Selected platform from test data: {latest_platform}")
    return jsonify({'platform': latest_platform, 'has_data': latest_date is not None, 'source': 'test_data'})


@app.route('/api/dashboard/summary/<platform>/<date>')
def api_dashboard_summary(platform, date):
    """Get summarized test results for a specific platform and date."""
    summary = dashboard.get_dashboard_summary(platform, date)
    if summary:
        return jsonify(summary)
    return jsonify({'error': 'Report not found'}), 404


@app.route('/api/dashboard/trend/<platform>')
@app.route('/api/dashboard/trend/<platform>/<end_date>')
@app.route('/api/dashboard/trend/<platform>/<end_date>/<category>/<level>')
def api_dashboard_trend(platform, end_date=None, category=None, level=None):
    """Get test trend data for a platform or specific test case."""
    range_type = request.args.get('range', 'week')  # week, month, or year
    trend_data = dashboard.get_7day_trend(platform, end_date, category, level, range_type)
    return jsonify(trend_data)


@app.route('/api/dashboard/download_log/<platform>/<date>/<category>/<level>')
def api_dashboard_download_log(platform, date, category, level):
    """Download log file for a specific test category and level."""
    target_dir = os.path.join(dashboard.TEST_REPORT_BASE, platform, f"all_test_{date}")
    
    if not os.path.isdir(target_dir):
        return jsonify({'error': 'Test report directory not found'}), 404
    
    # Handle ExitEVT special cases with topology
    if category == 'link' and level.startswith('ev_'):
        pattern = 'ExitEVT_'
        topology_map = {
            'ev_default': 'default',
            'ev_400g': '400g',
            'ev_optics_one': 'optics_one',
            'ev_optics_two': 'optics_two',
            'ev_copper': 'copper'
        }
        topology = topology_map.get(level, 'default')
        
        # Find matching file with topology in name
        files = os.listdir(target_dir)
        for filename in files:
            if filename.upper().startswith(pattern.upper()) and filename.endswith('.tar.gz'):
                if topology.lower() in filename.lower():
                    return send_from_directory(target_dir, filename, as_attachment=True)
                # Handle default case (no specific topology in name)
                elif topology == 'default' and 'optics' not in filename.lower() and 'copper' not in filename.lower() and '400g' not in filename.lower():
                    return send_from_directory(target_dir, filename, as_attachment=True)
        
        return jsonify({'error': f'ExitEVT log file not found for topology: {topology}'}), 404
    
    # Handle link_test special case
    if category == 'link_test' and level == 'default':
        pattern = 'LINKTEST_LOG_'
        files = os.listdir(target_dir)
        for filename in files:
            if filename.upper().startswith(pattern.upper()) and (filename.endswith('.tar.gz') or filename.endswith('.tgz')):
                return send_from_directory(target_dir, filename, as_attachment=True)
        
        return jsonify({'error': 'LINKTEST log file not found'}), 404
    
    # Map category and level to filename pattern
    filename_patterns = {
        ('sai', 't0'): 'SAI_t0_',
        ('sai', 't1'): 'SAI_t1_',
        ('sai', 't2'): 'SAI_t2_',
        ('agent_hw', 't0'): 'AGENT_HW_t0_',
        ('agent_hw', 't1'): 'AGENT_HW_t1_',
        ('agent_hw', 't2'): 'AGENT_HW_t2_',
        ('link', 't0'): 'LINK_T0_',
    }
    
    pattern = filename_patterns.get((category, level))
    if not pattern:
        return jsonify({'error': 'Invalid category or level'}), 400
    
    # Find the matching file
    files = os.listdir(target_dir)
    matching_file = None
    for filename in files:
        if filename.upper().startswith(pattern.upper()) and filename.endswith('.tar.gz'):
            matching_file = filename
            break
    
    if not matching_file:
        return jsonify({'error': 'Log file not found'}), 404
    
    # Send the file
    return send_from_directory(target_dir, matching_file, as_attachment=True)


@app.route('/api/dashboard/download_all/<platform>/<date>')
def api_dashboard_download_all(platform, date):
    """Download entire test report directory as tar.gz."""
    import tarfile
    from io import BytesIO
    
    target_dir = os.path.join(dashboard.TEST_REPORT_BASE, platform, f"all_test_{date}")
    
    if not os.path.isdir(target_dir):
        return jsonify({'error': 'Test report directory not found'}), 404
    
    # Create tar.gz in memory
    memory_file = BytesIO()
    
    with tarfile.open(fileobj=memory_file, mode='w:gz') as tar:
        # Add all files in the directory
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, target_dir)
                tar.add(file_path, arcname=arcname)
    
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/gzip',
        as_attachment=True,
        download_name=f'all_test_{platform}_{date}.tar.gz'
    )


@app.route('/api/dashboard/download_organized/<platform>/<date>')
@limiter.limit("10 per hour")
def api_dashboard_download_organized(platform, date):
    """Generate organized test report using organize_test_reports.py and download as tar.gz."""
    from utils.validators import validate_platform, validate_date
    
    # Validate inputs
    if not validate_platform(platform):
        logger.warning(f"[API] Invalid platform in download request: {platform}")
        return jsonify({'error': 'Invalid platform'}), 400
    
    if not validate_date(date):
        logger.warning(f"[API] Invalid date in download request: {date}")
        return jsonify({'error': 'Invalid date format'}), 400
    
    import tarfile
    import subprocess
    from io import BytesIO
    
    target_dir = os.path.join(dashboard.TEST_REPORT_BASE, platform, f"all_test_{date}")
    
    if not os.path.isdir(target_dir):
        return jsonify({'error': 'Test report directory not found'}), 404
    
    try:
        # Create a temporary directory for organized output
        temp_output_dir = safe_mkdtemp(prefix='organized_report_')
        
        try:
            # Run organize_test_reports.py - it will create the directory structure
            script_path = os.path.join(os.path.dirname(__file__), 'organize_test_reports.py')
            
            logger.info(f'[ORGANIZE] Source: {target_dir}')
            logger.info(f'[ORGANIZE] Output: {temp_output_dir}')
            
            # Check if source directory has .tar.gz files
            tar_gz_files = [f for f in os.listdir(target_dir) if f.endswith('.tar.gz')]
            logger.info(f'[ORGANIZE] Found {len(tar_gz_files)} .tar.gz files in source')
            if tar_gz_files:
                logger.info(f'[ORGANIZE] Files: {tar_gz_files[:5]}')  # Show first 5
            
            result = subprocess.run(
                ['python3', script_path, target_dir, temp_output_dir],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            logger.info(f'[ORGANIZE] Script stdout:\n{result.stdout}')
            if result.stderr:
                logger.warning(f'[ORGANIZE] Script stderr:\n{result.stderr}')
            
            if result.returncode != 0:
                # Check if error message indicates files are being written
                error_msg = result.stderr + result.stdout
                if 'being written' in error_msg or 'modified recently' in error_msg:
                    return jsonify({
                        'error': 'Some test archives are still being created. Please wait until tests complete, then try again.',
                        'details': result.stderr,
                        'is_test_running': True
                    }), 409  # 409 Conflict
                else:
                    return jsonify({
                        'error': 'Failed to organize reports',
                        'details': result.stderr,
                        'stdout': result.stdout
                    }), 500
            
            # Verify files were created - use list to force evaluation
            all_files = []
            for root, dirs, files in os.walk(temp_output_dir):
                for f in files:
                    all_files.append(os.path.join(root, f))
            
            file_count = len(all_files)
            logger.info(f'[ORGANIZE] Generated {file_count} files in output')
            if file_count > 0:
                logger.info(f'[ORGANIZE] Sample files: {all_files[:5]}')
            
            if file_count == 0:
                # Debug: check if directory exists and what's in it
                logger.warning(f'[ORGANIZE] Checking temp_output_dir: {temp_output_dir}')
                logger.warning(f'[ORGANIZE] Directory exists: {os.path.exists(temp_output_dir)}')
                if os.path.exists(temp_output_dir):
                    try:
                        all_items = os.listdir(temp_output_dir)
                        logger.warning(f'[ORGANIZE] Items in directory: {all_items}')
                    except Exception as e:
                        logger.error(f'[ORGANIZE] Error listing directory: {e}')
                
                # Get list of source files for debugging
                source_files = os.listdir(target_dir) if os.path.isdir(target_dir) else []
                return jsonify({
                    'error': 'No files were generated in organized report',
                    'source_files': source_files[:10],  # First 10 files
                    'source_dir': target_dir,
                    'script_output': result.stdout
                }), 500
            
            # Create tar.gz in memory
            memory_file = BytesIO()
            
            with tarfile.open(fileobj=memory_file, mode='w:gz') as tar:
                # Add all files in the temp directory (with organized structure)
                for root, dirs, files in os.walk(temp_output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_output_dir)
                        tar.add(file_path, arcname=arcname)
            
            memory_file.seek(0)
            
            return send_file(
                memory_file,
                mimetype='application/gzip',
                as_attachment=True,
                download_name=f'Organized_Report_{platform}_{date}.tar.gz'
            )
        
        finally:
            # Clean up temp directory
            if os.path.exists(temp_output_dir):
                shutil.rmtree(temp_output_dir, ignore_errors=True)
    
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Report organization timed out'}), 500
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in download_organized: {error_details}")
        return jsonify({
            'error': f'Failed to generate organized report: {str(e)}',
            'details': error_details
        }), 500


@app.route('/test_absent')
def test_absent():
    """Serve test page for absent ports"""
    if os.path.isfile('test_absent.html'):
        return send_from_directory(os.getcwd(), 'test_absent.html')
    return '<h3>test_absent.html not found</h3>'


@app.route('/api/dashboard/test_log_detail/<platform>/<date>/<category>/<level>/<path:test_name>')
@app.route('/api/dashboard/notes/<platform>/<date>', methods=['GET'])
def api_dashboard_get_notes(platform, date):
    """Get all notes from _dashboard_notes.json in test report directory"""
    notes_file = os.path.join(dashboard.TEST_REPORT_BASE, platform, f'all_test_{date}', '_dashboard_notes.json')
    
    if os.path.exists(notes_file):
        try:
            with open(notes_file, 'r', encoding='utf-8') as f:
                notes = json.load(f)
                return jsonify(notes)
        except Exception as e:
            print(f"Error reading notes from {notes_file}: {e}")
            return jsonify({})
    
    return jsonify({})


@app.route('/api/dashboard/notes/<platform>/<date>', methods=['POST'])
def api_dashboard_save_note(platform, date):
    """Save a note to _dashboard_notes.json in test report directory"""
    notes_file = os.path.join(dashboard.TEST_REPORT_BASE, platform, f'all_test_{date}', '_dashboard_notes.json')
    
    try:
        note_data = request.get_json()
        note_key = note_data.get('key')
        note_value = note_data.get('value')
        
        if not note_key:
            return jsonify({'error': 'Note key is required'}), 400
        
        # Check if directory exists
        notes_dir = os.path.dirname(notes_file)
        if not os.path.exists(notes_dir):
            return jsonify({'error': f'Test report directory not found: {notes_dir}'}), 404
        
        # Load existing notes
        notes = {}
        if os.path.exists(notes_file):
            try:
                with open(notes_file, 'r', encoding='utf-8') as f:
                    notes = json.load(f)
            except Exception as e:
                print(f"Error reading existing notes: {e}")
                notes = {}
        
        # Update note
        notes[note_key] = note_value
        
        # Save notes with atomic write
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(dir=notes_dir, suffix='.json')
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(notes, f, ensure_ascii=False, indent=2)
            # Atomic replace
            os.replace(temp_path, notes_file)
            print(f"Note saved to {notes_file}: {note_key}")
            return jsonify({'success': True, 'key': note_key})
        except Exception as write_error:
            # Clean up temp file if write failed
            try:
                os.unlink(temp_path)
            except (OSError, FileNotFoundError):
                pass  # Temp file cleanup failed, but continue with error
            raise write_error
    
    except Exception as e:
        print(f"Error saving note: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/platforms')
def list_platforms():
    return jsonify(list(PLATFORMS.keys()))


@app.route('/api/detect_initial')
def api_detect_initial():
    """Detect target platform and preferred initial topology file from FRUID file."""
    fruid_path = '/var/facebook/fboss/fruid.json'
    if not os.path.isfile(fruid_path):
        return jsonify({'platform': None, 'preferred_file': None, 'product': None})
    try:
        with open(fruid_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        product = None
        info = data.get('Information') or {}
        prod = info.get('Product Name') or info.get('Product') or info.get('ProductName')
        if isinstance(prod, str):
            product = prod.strip()
        if not product:
            return jsonify({'platform': None, 'preferred_file': None, 'product': None})

        pnorm = product.strip().upper()
        # Mapping rules requested by user
        if pnorm in ('MINIPACK3', 'MINIPACK3BA'):
            return jsonify({'platform': 'MINIPACK3BA', 'preferred_file': 'montblanc.materialized_JSON', 'product': product})
        if pnorm == 'MINIPACK3N':
            return jsonify({'platform': 'MINIPACK3N', 'preferred_file': 'minipack3n.materialized_JSON', 'product': product})
        if pnorm == 'WEDGE800BACT':
            return jsonify({'platform': 'WEDGE800BACT', 'preferred_file': 'wedge800bact.materialized_JSON', 'product': product})
        if pnorm == 'WEDGE800CACT':
            return jsonify({'platform': 'WEDGE800CACT', 'preferred_file': 'wedge800bact.materialized_JSON', 'product': product})

        return jsonify({'platform': None, 'preferred_file': None, 'product': product})
    except Exception as e:
        return jsonify({'platform': None, 'preferred_file': None, 'product': None, 'error': str(e)})


@app.route('/api/topology_files/<platform>')
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
        return jsonify({'platform': platform, 'files': [], 'error': str(e)})


@app.route('/api/topology/<platform>')
def api_topology(platform):
    from utils.validators import validate_platform, is_safe_filename
    
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
        abort(500, f'Error parsing topology: {e}')


@app.route('/api/save_topology', methods=['POST'])
@limiter.limit("20 per hour")
def api_save_topology():
    """Save current topology to a materialized_JSON file."""
    from utils.validators import validate_platform, is_safe_filename
    
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
        
        return jsonify({
            'success': True,
            'file': filename,
            'path': file_path,
            'connections': len(connections)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/apply_topology', methods=['POST'])
@limiter.limit("30 per hour")
def api_apply_topology():
    """Execute reconvert.py to apply the current topology configuration."""
    from utils.validators import validate_platform, is_safe_filename
    
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
        
        # Build command arguments
        cmd_args = [sys.executable, convert_script, platform.lower()]
        
        # Add config filename if provided
        if config_filename:
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
                return jsonify({
                    'success': True,
                    'message': f'reconvert.py executed successfully (platform: {platform}, config: {config_filename or "default"})',
                    'output': output,
                    'returncode': result.returncode
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'reconvert.py failed with return code {result.returncode}',
                    'output': output,
                    'stderr': error,
                    'returncode': result.returncode
                }), 500
                
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'reconvert.py execution timed out (60s)'}), 504
        except Exception as e:
            return jsonify({'error': f'Failed to execute reconvert.py: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Thread-safe service status manager
service_status = get_service_status_manager()


def is_process_running(name: str) -> bool:
    """Return True if a process matching `name` is running (uses pgrep -f)."""
    try:
        # Use pgrep -f to match the full command line; returncode 0 means match found
        proc = subprocess.run(['pgrep', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc.returncode == 0
    except Exception:
        return False


def monitor_services(poll_interval=1.0):
    """Background loop to update service status periodically."""
    while True:
        try:
            service_status.set_status('qsfp_service', is_process_running('qsfp_service'))

            sai_running = is_process_running('sai_mono_link_test-sai_impl')
            service_status.set_status('sai_mono_link_test-sai_impl', sai_running)

            # default details
            service_status.update_status({
                'sai_mono_link_test-sai_impl_cmd': None,
                'sai_mono_link_test-sai_impl_filter': None,
                'sai_mono_link_test-sai_impl_message': None
            })

            if sai_running:
                try:
                    # get first pid + full command line
                    proc = subprocess.run(['pgrep', '-fa', 'sai_mono_link_test-sai_impl'], capture_output=True, text=True)
                    cmd = None
                    print(f'[monitor] pgrep returncode={proc.returncode}', flush=True)
                    if proc.returncode == 0:
                        print(f'[monitor] pgrep output lines: {len(proc.stdout.splitlines())}', flush=True)
                        for line in proc.stdout.splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            print(f'[monitor] pgrep line: {line[:150]}', flush=True)
                            # format: "<pid> <full command>"
                            parts = line.split(' ', 1)
                            if len(parts) == 2 and 'sai_mono_link_test-sai_impl' in parts[1]:
                                cmd = parts[1]
                                print(f'[monitor] Found cmd: {cmd[:150]}', flush=True)
                                break
                    if cmd:
                        service_status.set_status('sai_mono_link_test-sai_impl_cmd', cmd)
                        m = re.search(r"--gtest_filter=([^\s]+)", cmd)
                        if m:
                            filter_val = m.group(1)
                            service_status.update_status({
                                'sai_mono_link_test-sai_impl_filter': filter_val,
                                'sai_mono_link_test-sai_impl_message': f"sai_mono_link_test-sai_impl --gtest_filter={filter_val}\nCurrently testing {filter_val}"
                            })
                            print(f'[monitor] Extracted filter: {filter_val}', flush=True)
                        else:
                            service_status.set_status('sai_mono_link_test-sai_impl_message', cmd)
                            print(f'[monitor] No gtest_filter found in cmd', flush=True)
                    else:
                        print('[monitor] No cmd found', flush=True)
                except Exception as e:
                    # ignore detail errors; keep basic running state
                    print(f'[monitor] Exception getting sai details: {e}', flush=True)
                    pass
        except Exception:
            # swallow errors and keep running
            pass
        time.sleep(poll_interval)


def monitor_transceivers(poll_interval=30.0):
    """Background loop to run switch commands and save output.
    
    Runs 3 times then stops. captures:
    - fboss2 show port
    - fboss2 show transceiver
    """
    iteration = 1
    max_iterations = 3
    
    logger.info(f"[monitor] Starting switch monitoring (Limit: {max_iterations} iterations, Interval: {poll_interval}s)")
    
    while iteration <= max_iterations:
        try:
            # Check if both services are running before attempting to query
            qsfp_running = is_process_running('qsfp_service')
            sai_running = is_process_running('sai_mono_link_test-sai_impl')
            
            if not (qsfp_running and sai_running):
                print(f'[monitor] Services not running: qsfp={qsfp_running}, sai={sai_running}, skipping...', flush=True)
                time.sleep(poll_interval)
                continue
            
            print(f'[monitor] Iteration {iteration}/{max_iterations} starting...', flush=True)
            
            # ---------------------------------------------------------
            # 1. Capture Port Status
            # ---------------------------------------------------------
            try:
                proc_port = subprocess.run(['fboss2', 'show', 'port'], 
                                    capture_output=True, text=True, timeout=30)
                
                if proc_port.returncode == 0 and len(proc_port.stdout.strip()) > 0:
                    # Save versioned file
                    file_ver = f'/opt/fboss/fboss2_show_port_{iteration}.txt'
                    # Save standard file (for API/UI)
                    file_std = '/opt/fboss/fboss2_show_port.txt'
                    
                    os.makedirs('/opt/fboss', exist_ok=True)
                    
                    # Write versioned file
                    with open(file_ver, 'w', encoding='utf-8') as f:
                        f.write(proc_port.stdout)
                    
                    # Update standard file
                    with open(file_std, 'w', encoding='utf-8') as f:
                        f.write(proc_port.stdout)
                        
                    print(f'[monitor] Saved ports to {file_ver}', flush=True)
                else:
                    print(f'[monitor] Port command failed or empty: {proc_port.stderr[:100]}', flush=True)
            except Exception as e:
                print(f'[monitor] Error capturing ports: {e}', flush=True)

            # ---------------------------------------------------------
            # 2. Capture Transceiver Status
            # ---------------------------------------------------------
            try:
                proc_trans = subprocess.run(['fboss2', 'show', 'transceiver'], 
                                    capture_output=True, text=True, timeout=30)
                
                if proc_trans.returncode == 0 and len(proc_trans.stdout.strip()) > 0:
                    # Save versioned file
                    file_ver = f'/opt/fboss/fboss2_show_transceivers_{iteration}.txt'
                    # Save standard file (for API/UI)
                    file_std = '/opt/fboss/fboss2_show_transceivers.txt'
                    
                    # Write versioned file
                    with open(file_ver, 'w', encoding='utf-8') as f:
                        f.write(proc_trans.stdout)
                    
                    # Update standard file
                    with open(file_std, 'w', encoding='utf-8') as f:
                        f.write(proc_trans.stdout)
                        
                    print(f'[monitor] Saved transceivers to {file_ver}', flush=True)
                else:
                    print(f'[monitor] Transceiver command failed or empty: {proc_trans.stderr[:100]}', flush=True)
            except Exception as e:
                print(f'[monitor] Error capturing transceivers: {e}', flush=True)
            
            iteration += 1
            if iteration <= max_iterations:
                time.sleep(poll_interval)
                
        except Exception as e:
            print(f'[monitor] Unexpected error: {e}', flush=True)
            time.sleep(poll_interval)
            
    print(f'[monitor] Completed {max_iterations} iterations. Stopping thread.', flush=True)


@app.route('/api/service_status')
def api_service_status():
    return jsonify(service_status.get_all_status())


# Port-related endpoints moved to routes/ports.py blueprint
# This includes: /api/port_status, /api/absent_ports, /api/present_transceivers, /api/transceiver_info
# All helper functions (parse_fboss2_port_output, parse_transceiver_output, etc.) are in routes/ports.py

# Legacy helper function kept for backward compatibility in case other code references it
def parse_fboss2_port_output(output: str):
    """Parse 'fboss2 show port' output and extract port status.
    Returns a dict mapping port name (e.g. 'eth1/1/1') to an object:
      { 'link': 'Up'|'Down'|..., 'mismatchedNeighbor': bool, 'transceiverPresent': bool }
    """
    port_status = {}
    lines = output.strip().split('\n')

    for i, line in enumerate(lines):
        # Skip header and separator lines
        if not line.strip():
            continue
        if line.lstrip().startswith('ID') or '---' in line:
            continue

        cols = line.split()
        if len(cols) < 4:
            continue

        try:
            name = cols[1]
            if not name.startswith('eth1/'):
                continue

            link_state = cols[3]
            mismatched = 'MISMATCHED_NEIGHBOR' in line
            
            # Check for Transceiver Present/Absent status
            # Typical line format includes 'Present' or 'Absent' keyword
            transceiver_present = True  # Default to present
            if 'Absent' in line:
                transceiver_present = False
            elif 'Present' in line:
                transceiver_present = True
            
            port_status[name] = {
                'link': link_state,
                'mismatchedNeighbor': bool(mismatched),
                'transceiverPresent': transceiver_present,
            }

            if len(port_status) <= 3:
                print(f"[parse] Line {i}: name={name}, link={link_state}, mismatch={mismatched}, present={transceiver_present}", flush=True)
        except Exception as e:
            if i < 10:
                print(f'[parse error] Line {i}: {e}', flush=True)
            continue

    print(f'[parse] Parsed {len(port_status)} ports', flush=True)
    return port_status


# @app.route('/api/port_status')  # REMOVED - Now handled by routes/ports.py blueprint
def api_port_status_LEGACY():
    """Run fboss2 show port and return port LinkState mapping."""
    try:
        # Check if both services are running
        qsfp_running = is_process_running('qsfp_service')
        sai_running = is_process_running('sai_mono_link_test-sai_impl')
        
        if not (qsfp_running and sai_running):
            print(f'[api] Services not running: qsfp={qsfp_running}, sai={sai_running}', flush=True)
            return jsonify({'error': 'Services not running', 'ports': {}}), 503
        
        print('[api] Running fboss2 show port...', flush=True)
        # Run fboss2 show port
        proc = subprocess.run(['fboss2', 'show', 'port'], capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            print(f'[api] fboss2 failed: {proc.stderr[:200]}', flush=True)
            return jsonify({'error': f'fboss2 failed: {proc.stderr}', 'ports': {}}), 500
        
        print(f'[api] fboss2 output length: {len(proc.stdout)}', flush=True)
        port_status = parse_fboss2_port_output(proc.stdout)
        
        # Only save to file if output contains valid port data
        output_file = '/opt/fboss/fboss2_show_port.txt'
        if len(port_status) > 0 and len(proc.stdout.strip()) > 0:
            try:
                os.makedirs('/opt/fboss', exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(proc.stdout)
                print(f'[api] Saved output to {output_file} ({len(port_status)} ports)', flush=True)
            except Exception as e:
                print(f'[api] Warning: Could not save to {output_file}: {e}', flush=True)
        else:
            print(f'[api] Skipping save: output empty or no valid ports found', flush=True)
        
        print(f'[api] Returning {len(port_status)} ports', flush=True)
        return jsonify({'ports': port_status})
    except FileNotFoundError:
        print('[api] fboss2 not found', flush=True)
        return jsonify({'error': 'fboss2 not found', 'ports': {}}), 404
    except subprocess.TimeoutExpired:
        print('[api] fboss2 timeout', flush=True)
        return jsonify({'error': 'fboss2 timeout', 'ports': {}}), 504
    except Exception as e:
        print(f'[api] Exception: {e}', flush=True)
        return jsonify({'error': str(e), 'ports': {}}), 500


# @app.route('/api/absent_ports')  # REMOVED - Now handled by routes/ports.py blueprint
def api_absent_ports_LEGACY():
    """Read fboss2 show transceivers output and return list of absent ports."""
    # Try multiple possible locations for the transceivers file
    possible_paths = [
        '/opt/fboss/fboss2_show_transceivers.txt',  # Production path on device
        'fboss2_show_transceivers.txt',  # Current directory
        '../fboss2_show_transceivers.txt',  # Parent directory
        'test_report/fboss2_show_transceivers.txt'  # Test directory
    ]
    
    output_file = None
    for path in possible_paths:
        if os.path.exists(path):
            output_file = path
            print(f'[api] Found transceivers file at: {path}', flush=True)
            break
    
    try:
        # If file doesn't exist, return empty absent ports list (all ports are present)
        if not output_file:
            print(f'[api] Transceivers file not found - treating all ports as present', flush=True)
            return jsonify({'absentPorts': [], 'totalPorts': 0, 'info': 'No transceiver file found, all ports treated as present'})
        
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if not content or len(content) < 10:
            print(f'[api] Transceivers file is empty - treating all ports as present', flush=True)
            return jsonify({'absentPorts': [], 'totalPorts': 0, 'info': 'Transceiver file is empty'})
        
        # Parse the transceiver output to find absent ports
        absent_ports = []
        lines = content.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines, headers, and separator lines
            if not line_stripped or line_stripped.startswith('-') or 'Interface' in line_stripped:
                continue
            
            # Check for port line (starts with ethX/Y/Z)
            if re.match(r'^\s*eth\d+/\d+/\d+', line):
                try:
                    # Split by multiple spaces to parse columns
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) < 3:
                        continue
                    
                    port_name = parts[0].strip()
                    status = parts[1].strip() if len(parts) > 1 else 'Unknown'
                    transceiver_type = parts[2].strip() if len(parts) > 2 else 'Unknown'
                    
                    # Only include ports where transceiver is Absent
                    if transceiver_type == 'Absent' or status == 'Absent':
                        absent_ports.append(port_name)
                
                except Exception as e:
                    print(f'[parse] Error parsing line: {line[:50]}... Error: {e}', flush=True)
                    continue
        
        print(f'[api] Found {len(absent_ports)} absent ports from transceivers file', flush=True)
        return jsonify({'absentPorts': absent_ports, 'totalPorts': len(absent_ports)})
        
    except Exception as e:
        print(f'[api] Error reading absent ports: {e}', flush=True)
        import traceback
        traceback.print_exc()
        # On error, return empty list (treat all ports as present)
        return jsonify({'absentPorts': [], 'error': str(e)}), 200


# @app.route('/api/present_transceivers')  # REMOVED - Now handled by routes/ports.py blueprint
def api_present_transceivers_LEGACY():
    """Read fboss2 show transceivers output and return list of present transceiver ports."""
    possible_paths = [
        '/opt/fboss/fboss2_show_transceivers.txt',  # Production path on device
        'fboss2_show_transceivers.txt',  # Current directory
        '../fboss2_show_transceivers.txt',  # Parent directory
        'test_report/fboss2_show_transceivers.txt'  # Test directory
    ]
    
    output_file = None
    for path in possible_paths:
        if os.path.exists(path):
            output_file = path
            print(f'[api] Found transceiver file at: {path}', flush=True)
            break
    
    try:
        if not output_file:
            error_msg = f'Transceiver file not found in any location'
            print(f'[api] {error_msg}', flush=True)
            return jsonify({'presentPorts': [], 'error': error_msg}), 200
        
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if not content or len(content) < 10:
            print(f'[api] Transceiver file is empty or too small', flush=True)
            return jsonify({'presentPorts': [], 'error': 'File is empty'}), 200
        
        # Parse the transceiver output to find present ports
        present_ports = []
        lines = content.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines, headers, and separator lines
            if not line_stripped or line_stripped.startswith('-') or 'Interface' in line_stripped:
                continue
            
            # Check for port line (starts with ethX/Y/Z)
            if re.match(r'^\s*eth\d+/\d+/\d+', line):
                try:
                    # Split by multiple spaces to parse columns
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) < 3:
                        continue
                    
                    port_name = parts[0].strip()
                    status = parts[1].strip() if len(parts) > 1 else 'Unknown'
                    transceiver_type = parts[2].strip() if len(parts) > 2 else 'Unknown'
                    
                    # Only include ports where transceiver is present (not Absent)
                    if transceiver_type != 'Absent' and status != 'Absent':
                        present_ports.append(port_name)
                
                except Exception as e:
                    print(f'[parse] Error parsing line: {line[:50]}... Error: {e}', flush=True)
                    continue
        
        print(f'[api] Found {len(present_ports)} present transceivers', flush=True)
        return jsonify({'presentPorts': present_ports, 'totalPorts': len(present_ports)})
        
    except Exception as e:
        print(f'[api] Error reading present transceivers: {e}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'presentPorts': [], 'error': str(e)}), 500


# @app.route('/api/transceiver_info')  # REMOVED - Now handled by routes/ports.py blueprint
def api_transceiver_info_LEGACY():
    """Parse fboss2 show transceiver output and analyze TX/RX power levels."""
    # Try multiple possible locations for the file
    possible_paths = [
        '/opt/fboss/fboss2_show_transceivers.txt',  # Production path on device
        'fboss2_show_transceivers.txt',  # Current directory
        '../fboss2_show_transceivers.txt',  # Parent directory
        'test_report/fboss2_show_transceivers.txt'  # Test directory
    ]
    
    output_file = None
    for path in possible_paths:
        if os.path.exists(path):
            output_file = path
            print(f'[api] Found transceiver file at: {path}', flush=True)
            break
    
    try:
        if not output_file:
            error_msg = f'File not found in any of these locations: {", ".join(possible_paths)}'
            print(f'[api] {error_msg}', flush=True)
            return jsonify({'ports': [], 'summary': {'good': 0, 'warning': 0, 'critical': 0}, 'error': error_msg}), 200
        
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if not content or len(content) < 10:
            print(f'[api] File is empty or too small', flush=True)
            return jsonify({'ports': [], 'summary': {'good': 0, 'warning': 0, 'critical': 0}, 'error': 'File is empty'}), 200
        
        print(f'[api] Read {len(content)} bytes from {output_file}', flush=True)
        
        # Parse the transceiver data
        transceiver_data = parse_transceiver_output(content)
        
        print(f'[api] Parsed {len(transceiver_data.get("ports", []))} transceivers', flush=True)
        if transceiver_data.get("ports"):
            print(f'[api] Sample port data: {transceiver_data["ports"][0]}', flush=True)
        return jsonify(transceiver_data)
        
    except Exception as e:
        print(f'[api] Error reading transceiver info: {e}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'ports': [], 'summary': {'good': 0, 'warning': 0, 'critical': 0}, 'error': str(e)}), 500


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
                    # Split by multiple spaces to parse columns
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) < 6:
                        continue
                    
                    # Parse columns based on table format
                    # Interface  Status  Transceiver  CfgValidated  Reason  Vendor  Serial  Part Number  FW App Version  FW DSP Version  Temperature (C)  Voltage (V)  Current (mA)  Tx Power (dBm)  Rx Power (dBm)  Rx SNR
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
                    
                    temperature = None
                    if len(parts) > 10:
                        try:
                            temperature = float(parts[10].strip())
                        except ValueError:
                            pass
                    
                    # Extract power values (comma-separated lists)
                    tx_powers = []
                    rx_powers = []
                    
                    if len(parts) > 13:  # Tx Power column
                        tx_str = parts[13].strip()
                        try:
                            tx_powers = [float(x) for x in tx_str.split(',') if x.strip()]
                        except ValueError:
                            pass
                    
                    if len(parts) > 14:  # Rx Power column
                        rx_str = parts[14].strip()
                        try:
                            rx_powers = [float(x) for x in rx_str.split(',') if x.strip()]
                        except ValueError:
                            pass
                    
                    # Process port data
                    port_details = {
                        'status': status,
                        'type': transceiver_type,
                        'vendor': vendor,
                        'serial': serial,
                        'part_number': part_number,
                        'temperature': temperature,
                        'fw_app_version': fw_app_version,
                        'fw_dsp_version': fw_dsp_version
                    }
                    
                    if tx_powers and rx_powers:
                        port_data = analyze_port_power(port_name, port_details, tx_powers, rx_powers,
                                                       TX_MIN_SAFE, TX_MAX_SAFE, RX_MIN_SAFE, RX_MAX_SAFE)
                        ports.append(port_data)
                    else:
                        # Add port with basic info even without power data
                        port_data = {
                            'name': port_name,
                            'vendor': vendor,
                            'serial': serial,
                            'part_number': part_number,
                            'temperature': temperature,
                            'fw_app_version': fw_app_version,
                            'fw_dsp_version': fw_dsp_version,
                            'status': 'good',
                            'tx_avg': None,
                            'rx_avg': None,
                            'tx_range': None,
                            'rx_range': None,
                            'issues': 0,
                            'warnings': []
                        }
                        ports.append(port_data)
                
                except Exception as e:
                    print(f'[parse] Error parsing line: {line[:50]}... Error: {e}', flush=True)
                    continue
        
        print(f'[parse] Successfully parsed {len(ports)} ports with transceiver data', flush=True)
        
    except Exception as e:
        print(f'[parse] Error parsing transceiver data: {e}', flush=True)
        import traceback
        traceback.print_exc()
    
    # Generate summary
    summary = generate_summary(ports)
    
    return {'ports': ports, 'summary': summary}


def analyze_port_power(port_name, details, tx_powers, rx_powers, 
                       tx_min, tx_max, rx_min, rx_max):
    """Analyze power levels for a single port."""
    issues = 0
    warnings = []
    
    # Calculate averages
    tx_avg = sum(tx_powers) / len(tx_powers) if tx_powers else 0
    rx_avg = sum(rx_powers) / len(rx_powers) if rx_powers else 0
    
    # Calculate ranges
    tx_range = max(tx_powers) - min(tx_powers) if len(tx_powers) > 1 else 0
    rx_range = max(rx_powers) - min(rx_powers) if len(rx_powers) > 1 else 0
    
    # Check TX power issues
    for tx in tx_powers:
        if tx < tx_min or tx > tx_max:
            issues += 1
            warnings.append(f'TX power out of safe range: {tx:.2f} dBm')
    
    # Check RX power issues
    for rx in rx_powers:
        if rx < rx_min or rx > rx_max:
            issues += 1
            warnings.append(f'RX power out of safe range: {rx:.2f} dBm')
    
    # Check power imbalance (range > 1.5 dB)
    if tx_range > 1.5:
        warnings.append(f'TX power imbalance: {tx_range:.2f} dB')
    if rx_range > 1.5:
        warnings.append(f'RX power imbalance: {rx_range:.2f} dB')
    
    # Determine status
    if issues >= 3:
        status = 'critical'
    elif issues > 0 or tx_range > 1.5 or rx_range > 1.5:
        status = 'warning'
    else:
        status = 'good'
    
    return {
        'name': port_name,
        'vendor': details.get('vendor', 'Unknown'),
        'serial': details.get('serial'),
        'part_number': details.get('part_number'),
        'temperature': details.get('temperature'),
        'fw_app_version': details.get('fw_app_version'),
        'fw_dsp_version': details.get('fw_dsp_version'),
        'status': status,
        'tx_avg': tx_avg,
        'rx_avg': rx_avg,
        'tx_range': tx_range,
        'rx_range': rx_range,
        'issues': issues,
        'warnings': warnings
    }


def generate_summary(ports):
    """Generate summary text for critical issues."""
    if not ports:
        return 'No Data'
    
    critical_ports = [p for p in ports if p['status'] == 'critical']
    warning_ports = [p for p in ports if p['status'] == 'warning']
    
    summary = f"<strong>Critical Issue Summary ({datetime.now().strftime('%Y-%m-%d')})</strong>\n\n"
    
    if critical_ports:
        summary += "• Critical Ports:\n"
        for port in critical_ports[:5]:  # Show top 5
            summary += f"  → {port['name']} ({port['vendor']}): {port['issues']} issues\n"
            for warning in port['warnings'][:2]:  # Show first 2 warnings
                summary += f"    - {warning}\n"
        summary += "\n"
    
    if warning_ports:
        summary += f"• Warning Ports: {len(warning_ports)}\n"
        summary += "  Recommend enhanced monitoring, check optical attenuators and peer devices\n\n"
    
    good_count = len([p for p in ports if p['status'] == 'good'])
    health_pct = round(good_count / len(ports) * 100) if ports else 0
    
    summary += f"Overall Health: {health_pct}% Normal ({good_count}/{len(ports)} ports)"
    
    return summary


@app.route('/api/test_info')
def api_test_info():
    """Get test status and results."""
    result = {
        'csv_files': [],
        'test_running': False,
        'test_type': None,
        'current_test': None,
        'passed_tests': [],
        'failed_tests': [],
        'test_list': [],
        'log_file': None,
        'test_results': None,
        'start_time': None
    }
    
    # Check for CSV result files first (completed tests)
    csv_pattern = '/opt/fboss/hwtest_results_*.csv'
    try:
        proc = subprocess.run(
            ['bash', '-c', f'ls {csv_pattern} 2>/dev/null || true'],
            capture_output=True, text=True, timeout=5
        )
        if proc.returncode == 0 and proc.stdout.strip():
            result['csv_files'] = proc.stdout.strip().split('\n')
    except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
        pass  # CSV file listing failed, continue without it
    
    # If CSV files exist, parse the latest one
    if result['csv_files']:
        latest_csv = sorted(result['csv_files'])[-1]
        try:
            with open(latest_csv, 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    result['test_results'] = {
                        'file': latest_csv,
                        'total': len(lines) - 1,
                        'passed': sum(1 for line in lines[1:] if ',OK' in line or ',PASS' in line),
                        'failed': sum(1 for line in lines[1:] if ',FAIL' in line or ',ERROR' in line),
                        'tests': []
                    }
                    for line in lines[1:]:
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            result['test_results']['tests'].append({
                                'name': parts[0],
                                'result': parts[1]
                            })
        except Exception as e:
            print(f'Error reading CSV: {e}', flush=True)
        
        # Check TEST_STATUS for timestamp to find the actual archive file
        test_status_file = '/opt/fboss/TEST_STATUS'
        if os.path.exists(test_status_file):
            try:
                with open(test_status_file, 'r') as f:
                    status_content = f.read()
                    # Extract start time to use as search key
                    start_match = re.search(r'(?:Sart|Start) Time:(.+?)(?:\n|$)', status_content)
                    if start_match:
                        timestamp = start_match.group(1).strip()
                        print(f'[test_info] Looking for archive with timestamp: {timestamp}', flush=True)
                        
                        # Get platform for test_report directory
                        platform = get_platform_name()
                        
                        # Search for archive files with this timestamp in multiple locations
                        import glob
                        search_patterns = [
                            f'/opt/fboss/*{timestamp}*.tar.gz',
                            f'/opt/fboss/*{timestamp}*.log.tar.gz',
                        ]
                        
                        # Add test_report directory if platform detected
                        if platform:
                            test_report_dir = os.path.join(os.getcwd(), 'test_report', platform)
                            search_patterns.extend([
                                f'{test_report_dir}/*{timestamp}*.tar.gz',
                                f'{test_report_dir}/*{timestamp}*.log.tar.gz',
                            ])
                        
                        archive_files = []
                        for pattern in search_patterns:
                            matches = glob.glob(pattern)
                            archive_files.extend(matches)
                        
                        # Prefer files ending with .tar.gz (not .log.tar.gz)
                        tar_gz_files = [f for f in archive_files if f.endswith('.tar.gz') and not f.endswith('.log.tar.gz')]
                        log_tar_gz_files = [f for f in archive_files if f.endswith('.log.tar.gz')]
                        
                        if tar_gz_files:
                            result['archive_file'] = tar_gz_files[0]
                            print(f'[test_info] Found archive file: {tar_gz_files[0]}', flush=True)
                        elif log_tar_gz_files:
                            result['archive_file'] = log_tar_gz_files[0]
                            print(f'[test_info] Found log archive file: {log_tar_gz_files[0]}', flush=True)
                        
                        # Additionally check for log.tar.gz files specifically
                        if log_tar_gz_files:
                            result['log_tar_gz'] = os.path.basename(log_tar_gz_files[0])
                            result['log_tar_gz_size'] = os.path.getsize(log_tar_gz_files[0])
                            result['log_tar_gz_time'] = os.path.getmtime(log_tar_gz_files[0])
                            print(f'[test_info] Found log.tar.gz: {result["log_tar_gz"]}', flush=True)
            except Exception as e:
                print(f'[test_info] Error finding archive: {e}', flush=True)
        
        # Fallback: If no log.tar.gz found via TEST_STATUS, search directly in /opt/fboss/
        if 'log_tar_gz' not in result:
            try:
                import glob
                log_tar_pattern = '/opt/fboss/*_BASIC.log.tar.gz'
                log_tar_files = sorted(glob.glob(log_tar_pattern), key=os.path.getmtime, reverse=True)
                if log_tar_files:
                    result['log_tar_gz'] = os.path.basename(log_tar_files[0])
                    result['log_tar_gz_size'] = os.path.getsize(log_tar_files[0])
                    result['log_tar_gz_time'] = os.path.getmtime(log_tar_files[0])
                    print(f'[test_info] Found log.tar.gz via fallback search: {result["log_tar_gz"]}', flush=True)
            except Exception as e:
                print(f'[test_info] Error in fallback log.tar.gz search: {e}', flush=True)
        
        return jsonify(result)
    
    # No CSV files, check TEST_STATUS file to determine if test is running
    test_status_file = '/opt/fboss/TEST_STATUS'
    test_status_info = {}
    
    if os.path.exists(test_status_file):
        try:
            with open(test_status_file, 'r') as f:
                status_content = f.read()
                # Parse TEST_STATUS file
                # Format:
                # Sart Time:2026-01-03-AM09-10
                # log:ExitEVT_PLATFORM_VERSION_DATE.tar.gz
                # End Time:2026-01-03-AM09-11
                
                start_match = re.search(r'(?:Sart|Start) Time:(.+?)(?:\n|$)', status_content)
                log_match = re.search(r'log:(.+?)(?:\n|$)', status_content)
                end_match = re.search(r'(?:End|Finsih) Time:(.+?)(?:\n|$)', status_content)
                
                if start_match:
                    test_status_info['start_time'] = start_match.group(1).strip()
                if log_match:
                    test_status_info['log_archive'] = log_match.group(1).strip()
                if end_match:
                    end_time = end_match.group(1).strip()
                    # Only set if not empty
                    if end_time:
                        test_status_info['end_time'] = end_time
                
                # Test is running if we have start time but no end time
                if 'start_time' in test_status_info and 'end_time' not in test_status_info:
                    result['test_running'] = True
                    result['start_time'] = test_status_info['start_time']
                    print(f'[test_info] Test running based on TEST_STATUS (started: {test_status_info["start_time"]})', flush=True)
                elif 'start_time' in test_status_info and 'end_time' in test_status_info:
                    result['test_running'] = False
                    result['test_completed'] = True
                    result['start_time'] = test_status_info['start_time']
                    result['end_time'] = test_status_info['end_time']
                    # Include log archive for download
                    if 'log_archive' in test_status_info:
                        result['log_archive'] = test_status_info['log_archive']
                    
                    # Also check for log.tar.gz file in /opt/fboss/
                    try:
                        import glob
                        log_tar_pattern = '/opt/fboss/*_BASIC.log.tar.gz'
                        log_tar_files = sorted(glob.glob(log_tar_pattern), key=os.path.getmtime, reverse=True)
                        if log_tar_files:
                            result['log_tar_gz'] = os.path.basename(log_tar_files[0])
                            result['log_tar_gz_size'] = os.path.getsize(log_tar_files[0])
                            result['log_tar_gz_time'] = os.path.getmtime(log_tar_files[0])
                            print(f'[test_info] Found log.tar.gz for completed test: {result["log_tar_gz"]}', flush=True)
                    except Exception as log_err:
                        print(f'[test_info] Error finding log.tar.gz: {log_err}', flush=True)
                    
                    print(f'[test_info] Test completed based on TEST_STATUS', flush=True)
                    
        except Exception as e:
            print(f'[test_info] Error reading TEST_STATUS: {e}', flush=True)
    
    # If we have log info from TEST_STATUS, try to find and parse the log file
    # This applies to both running tests and completed tests
    if 'log_archive' in test_status_info:
        log_archive = test_status_info['log_archive']
        
        # The log in TEST_STATUS is: ExitEVT_PLATFORM_VERSION_DATE.tar.gz
        # The actual log file is: link_test_VERSION_DATE_BASIC.log
        # Extract VERSION and DATE from the archive name
        
        # Pattern: ExitEVT_PLATFORM_VERSION_DATE.tar.gz
        # Example: ExitEVT_WEDGE800BACT_fboss_bins_bcm_JC_20251222_15_54_08_b43cb9b8f5_varFBOSSsai_SAI_13_3_0_GA_20251210_tar_gz.tar.zst_2024-10-18-AM02-50.tar.gz
        archive_match = re.match(r'ExitEVT_([^_]+)_(.+)_(\d{4}-\d{2}-\d{2}-[AP]M\d{2}-\d{2})\.tar\.gz$', log_archive)
        
        if archive_match:
            platform = archive_match.group(1)
            version = archive_match.group(2)
            date = archive_match.group(3)
            
            # Construct the actual log filename
            log_filename = f"link_test_{version}_{date}_BASIC.log"
            
            # Check if file exists in /opt/fboss/
            opt_fboss_log = os.path.join('/opt/fboss', log_filename)
            if os.path.isfile(opt_fboss_log):
                result['log_file'] = opt_fboss_log
                print(f'[test_info] Found log file from TEST_STATUS: {result["log_file"]}', flush=True)
            else:
                print(f'[test_info] Log file not found: {opt_fboss_log}', flush=True)
                
                # Try with .tar.gz extension (archived log)
                log_tar = f"{log_filename}.tar.gz"
                opt_fboss_log_tar = os.path.join('/opt/fboss', log_tar)
                if os.path.isfile(opt_fboss_log_tar):
                    result['log_file'] = opt_fboss_log_tar
                    print(f'[test_info] Found archived log file: {result["log_file"]}', flush=True)
        else:
            print(f'[test_info] Could not parse archive name: {log_archive}', flush=True)
    
    # Fallback: Check for running processes if TEST_STATUS doesn't exist or couldn't be parsed
    if not result.get('test_running') and not test_status_info.get('end_time'):
        try:
            # Try to get test list from run_test.py process
            run_test_proc = subprocess.run(
                ['bash', '-c', 'ps auxww | grep run_test.py | grep -v grep'],
                capture_output=True, text=True, timeout=5
            )
            
            if run_test_proc.returncode == 0 and run_test_proc.stdout.strip():
                result['test_running'] = True
                
                # Detect test type from run_test.py command
                if 'run_test.py sai' in run_test_proc.stdout and 'run_test.py sai_agent' not in run_test_proc.stdout:
                    result['test_type'] = 'sai'
                elif 'run_test.py link' in run_test_proc.stdout:
                    result['test_type'] = 'link'
                elif 'run_test.py sai_agent' in run_test_proc.stdout:
                    result['test_type'] = 'agent_hw'
                
                # Extract test list from --filter parameter
                filter_match = re.search(r'--filter=([^\s]+)', run_test_proc.stdout)
                if filter_match:
                    # Split by colon to get individual tests
                    test_filter = filter_match.group(1)
                    result['test_list'] = test_filter.split(':')
                    print(f'[test_info] Found {len(result["test_list"])} tests from run_test.py, type: {result["test_type"]}', flush=True)
            
            # Try to get full command line from sai_mono_link_test process
            ps_proc = subprocess.run(
                ['bash', '-c', 'ps auxww | grep sai_mono_link_test-sai_impl | grep -v grep'],
                capture_output=True, text=True, timeout=5
            )
            
            if ps_proc.returncode == 0 and ps_proc.stdout.strip():
                result['test_running'] = True
                
                # Extract current test from --gtest_filter parameter
                gtest_match = re.search(r'--gtest_filter=([^\s]+)', ps_proc.stdout)
                if gtest_match:
                    result['current_test'] = gtest_match.group(1)
                    print(f'[test_info] Found current test from process: {result["current_test"]}', flush=True)
        except Exception as e:
            print(f'[test_info] Error checking processes: {e}', flush=True)
    
    # Now handle the case where test is running (either from TEST_STATUS or processes)
    if result.get('test_running') and not result.get('log_file'):
        try:
            # Find the log file being written from tee process
            tee_proc = subprocess.run(
                ['bash', '-c', 'ps auxww | grep tee | grep -v grep'],
                capture_output=True, text=True, timeout=5
            )
            if tee_proc.returncode == 0 and tee_proc.stdout.strip():
                # Extract log filename from tee command
                match = re.search(r'tee\s+([^\s]+\.log)', tee_proc.stdout)
                if match:
                    log_file = match.group(1)
                    # If it's just a filename, check in /opt/fboss/ directory
                    if not os.path.isabs(log_file):
                        opt_fboss_log = os.path.join('/opt/fboss', log_file)
                        if os.path.isfile(opt_fboss_log):
                            result['log_file'] = opt_fboss_log
                        else:
                            result['log_file'] = log_file
                    else:
                        result['log_file'] = log_file
                    
                    print(f'[test_info] Found log file from tee: {result["log_file"]}', flush=True)
        except Exception as e:
            print(f'[test_info] Error finding log file: {e}', flush=True)
    
    # Parse log file if found (to get passed/failed tests history)
    # This applies to both running and completed tests
    if result.get('log_file') and os.path.isfile(result['log_file']):
        try:
            with open(result['log_file'], 'r', encoding='utf-8', errors='ignore') as f:
                # Read entire file to get test sequence from beginning
                log_content = f.read()
                
                # Debug: Log what patterns we're looking for
                print(f'[test_info] Parsing log file: {result["log_file"]}', flush=True)
                print(f'[test_info] Log content length: {len(log_content)} chars', flush=True)
                
                # Store last 500 chars for debugging
                result['log_tail'] = log_content[-500:] if len(log_content) > 500 else log_content
                
                # Extract test list from the formatted test plan at the top of log
                # Pattern: ClassName. followed by indented method names
                # Also handles parameterized tests like "HwRouteNeighborTest/0.  # TypeParam..."
                test_list_from_log = []
                lines = log_content.split('\n')
                current_class = None
                
                for line in lines[:2000]:  # Check first 2000 lines for test plan
                    # Match class name lines like "AgentEnsembleLinkTest." or "HwRouteNeighborTest/0.  # TypeParam..."
                    # The comment may be on the same line
                    class_match = re.match(r'^([A-Z][a-zA-Z0-9_/]+)\.\s*(?:#.*)?$', line.strip())
                    if class_match:
                        current_class = class_match.group(1)
                        continue
                    
                    # Skip pure comment lines
                    if line.strip().startswith('#') or (line.strip() and 'TypeParam' in line and not line.strip()[0].isalpha()):
                        continue
                    
                    # Match method names (may or may not be indented)
                    if current_class:
                        # Match method names - can start with uppercase or lowercase
                        method_match = re.match(r'^\s*([a-zA-Z][a-zA-Z0-9_]+)$', line)
                        if method_match:
                            method_name = method_match.group(1)
                            test_list_from_log.append(f"{current_class}.{method_name}")
                            # Don't reset current_class - keep reading methods for this class
                        elif line.strip() and not line.strip().startswith(('The ', 'Note:', 'Setting ', 'GTEST_')):
                            # Non-empty line that's not a test name or special line, end of this class
                            current_class = None
                
                if test_list_from_log:
                    result['test_list'] = test_list_from_log
                    print(f'[test_info] Found {len(test_list_from_log)} tests from log test plan', flush=True)
                
                # Also extract from [RUN] entries to supplement any missing tests
                # Preserve the original order from test plan, only add missing tests at the end
                run_matches = re.findall(r'\[\s*RUN\s*\]\s+(\S+)', log_content)
                if run_matches:
                    if test_list_from_log:
                        # Preserve test plan order, add any missing tests from RUN entries
                        seen = set(test_list_from_log)
                        for test in run_matches:
                            if test not in seen:
                                test_list_from_log.append(test)
                                seen.add(test)
                        result['test_list'] = test_list_from_log
                        print(f'[test_info] Final test list: {len(test_list_from_log)} tests (preserving log order)', flush=True)
                    else:
                        # No test plan found, use RUN entries in their order
                        seen = set()
                        test_list_from_run = []
                        for test in run_matches:
                            if test not in seen:
                                seen.add(test)
                                test_list_from_run.append(test)
                        result['test_list'] = test_list_from_run
                        print(f'[test_info] Found {len(test_list_from_run)} tests from [RUN] entries', flush=True)
                
                # Only try to find current test from log if we didn't get it from process
                if not result.get('current_test'):
                    current_test_match = re.findall(r'\[\s*RUN\s*\]\s+(\S+)', log_content)
                    if not current_test_match:
                        # Try alternative pattern
                        current_test_match = re.findall(r'Running.*?test[:\s]+(\S+)', log_content, re.IGNORECASE)
                    
                    print(f'[test_info] Current test matches from log: {current_test_match}', flush=True)
                    
                    if current_test_match:
                        result['current_test'] = current_test_match[-1]
                
                # Find passed tests - look for [OK] or [PASSED] pattern
                # Pattern: [       OK ] warm_boot.AgentCoppTest/0.testName (123 ms)
                # Exclude header lines like: ########## Coldboot test results...
                # We want to capture: AgentCoppTest/0.testName (without warm_boot/cold_boot prefix)
                passed_lines = []
                for line in log_content.split('\n'):
                    # Skip header lines with ##########
                    if line.strip().startswith('#'):
                        continue
                    # Match actual test results - now includes /0, /1 etc in test names
                    match = re.search(r'\[\s*(?:OK|PASSED)\s*\]\s+(?:(?:warm_boot|cold_boot)\.)?([A-Za-z0-9_/]+\.[A-Za-z0-9_]+)\s+\(\d+\s+ms\)', line)
                    if match:
                        passed_lines.append(match.group(1))
                
                # Remove duplicates while preserving order
                seen = set()
                passed_unique = []
                for test in passed_lines:
                    if test not in seen:
                        seen.add(test)
                        passed_unique.append(test)
                
                print(f'[test_info] Passed test count: {len(passed_unique)}', flush=True)
                result['passed_tests'] = passed_unique
                
                # Find failed tests - exclude header lines with ##########
                # Match multiple formats:
                # 1. [  FAILED  ] TestName (123 ms)
                # 2. [  FAILED  ] TestName, where TypeParam = ...
                # 3. Header lines: ########## ... [   FAILED ] cold_boot.TestName (0 ms)
                failed_lines = []
                for line in log_content.split('\n'):
                    # Match format 1: [  FAILED  ] TestName (123 ms)
                    match = re.search(r'\[\s*(?:FAILED|FAIL)\s*\]\s+(?:(?:warm_boot|cold_boot)\.)?([A-Za-z0-9_/]+\.[A-Za-z0-9_]+)\s+\(\d+\s+ms\)', line)
                    if match:
                        failed_lines.append(match.group(1))
                        continue
                    
                    # Match format 2: [  FAILED  ] TestName, where TypeParam = ...
                    match = re.search(r'\[\s*(?:FAILED|FAIL)\s*\]\s+([A-Za-z0-9_/]+\.[A-Za-z0-9_]+),\s*where\s+TypeParam', line)
                    if match:
                        failed_lines.append(match.group(1))
                
                if failed_lines:
                    # Remove duplicates while preserving order
                    seen = set()
                    failed_unique = []
                    for test in failed_lines:
                        if test not in seen:
                            seen.add(test)
                            failed_unique.append(test)
                    result['failed_tests'] = failed_unique
                    print(f'[test_info] Failed test count: {len(failed_unique)}', flush=True)
                    
        except Exception as e:
            print(f'Error parsing log file: {e}', flush=True)
    
    return jsonify(result)


@app.route('/api/test_log_tail')
def api_test_log_tail():
    """Get the last N lines of the current test log file."""
    lines = int(request.args.get('lines', 50))
    
    # Find the log file
    log_file = None
    
    # First, try to read from TEST_STATUS file
    test_status_file = '/opt/fboss/TEST_STATUS'
    if os.path.exists(test_status_file):
        try:
            with open(test_status_file, 'r') as f:
                status_content = f.read()
                # Look for log: line in TEST_STATUS
                log_match = re.search(r'log:(.+?)(?:\n|$)', status_content)
                if log_match:
                    log_filename = log_match.group(1).strip()
                    # The log in TEST_STATUS is the .tar.gz, we need the .log file
                    # Extract base name without .tar.gz
                    if log_filename.endswith('.log.tar.gz'):
                        log_filename = log_filename[:-7]  # Remove .tar.gz, keep .log
                    
                    # Check if file exists in /opt/fboss/
                    opt_fboss_log = os.path.join('/opt/fboss', log_filename)
                    if os.path.isfile(opt_fboss_log):
                        log_file = opt_fboss_log
        except Exception as e:
            print(f'[test_log_tail] Error reading TEST_STATUS: {e}', flush=True)
    
    # Fallback: Find the log file from tee process
    if not log_file:
        try:
            tee_proc = subprocess.run(
                ['bash', '-c', 'ps aux | grep tee | grep -v grep'],
                capture_output=True, text=True, timeout=5
            )
            if tee_proc.returncode == 0 and tee_proc.stdout.strip():
                match = re.search(r'tee\s+([^\s]+\.log)', tee_proc.stdout)
                if match:
                    log_file = match.group(1)
                    if not os.path.isabs(log_file):
                        opt_fboss_log = os.path.join('/opt/fboss', log_file)
                        if os.path.isfile(opt_fboss_log):
                            log_file = opt_fboss_log
        except Exception as e:
            print(f'[test_log_tail] Error finding tee process: {e}', flush=True)
    
    if not log_file or not os.path.isfile(log_file):
        return jsonify({'error': 'Log file not found', 'log_file': log_file})
    
    try:
        # Use tail command to get last N lines
        tail_proc = subprocess.run(
            ['tail', '-n', str(lines), log_file],
            capture_output=True, text=True, timeout=5
        )
        if tail_proc.returncode == 0:
            return jsonify({
                'log_file': log_file,
                'content': tail_proc.stdout,
                'lines': tail_proc.stdout.count('\n')
            })
    except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
        pass  # Tail command failed, fall back to manual read
    
    # Fallback: read manually
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return jsonify({
                'log_file': log_file,
                'content': ''.join(last_lines),
                'lines': len(last_lines)
            })
    except Exception as e:
        return jsonify({'error': str(e), 'log_file': log_file})


@app.route('/api/test_reports')
def api_test_reports():
    """Get list of available test reports for current platform."""
    try:
        # Get current platform
        platform = get_platform_name()
        if not platform:
            return jsonify({'error': 'Platform not detected'})
        
        # Check test_report directory
        report_dir = os.path.join('/home/NUI/test_report', platform)
        
        if not os.path.exists(report_dir):
            return jsonify({'reports': [], 'platform': platform})
        
        # List all .tar.gz files
        reports = []
        for filename in os.listdir(report_dir):
            if filename.endswith('.tar.gz'):
                filepath = os.path.join(report_dir, filename)
                stat = os.stat(filepath)
                reports.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'path': filepath
                })
        
        # Sort by modification time, newest first
        reports.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'reports': reports,
            'platform': platform,
            'report_dir': report_dir
        })
    except Exception as e:
        return jsonify({'error': str(e), 'reports': []})


@app.route('/api/download_log/<filename>')
def api_download_log(filename):
    """Download a log.tar.gz file from /opt/fboss/ directory."""
    try:
        # Validate filename for security
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Ensure file is .log.tar.gz format
        if not filename.endswith('.log.tar.gz'):
            return jsonify({'error': 'Invalid file format. Only .log.tar.gz files are allowed.'}), 400
        
        log_dir = '/opt/fboss'
        file_path = os.path.join(log_dir, filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'error': f'File not found: {filename}'}), 404
        
        # Send file
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/gzip'
        )
    except Exception as e:
        print(f'Error downloading log file: {str(e)}', flush=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/download_report/<path:filename>')
def api_download_report(filename):
    """Download a test report file."""
    try:
        # Get current platform
        platform = get_platform_name()
        if not platform:
            return jsonify({'error': 'Platform not detected'}), 404
        
        report_dir = os.path.join('/home/NUI/test_report', platform)
        filepath = os.path.join(report_dir, filename)
        
        # Security check: ensure file is in the correct directory
        if not os.path.abspath(filepath).startswith(os.path.abspath(report_dir)):
            return jsonify({'error': 'Invalid file path'}), 403
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download_report')
def download_report():
    """Download a test report file by full path."""
    try:
        file_path = request.args.get('file')
        if not file_path:
            return jsonify({'error': 'No file specified'}), 400
        
        # Security check: ensure file exists and is accessible
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Get just the filename for download
        filename = os.path.basename(file_path)
        
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500




# ============================================================================
# Run Test Tab API Endpoints
# ============================================================================

# Thread-safe test execution manager
test_execution = get_test_execution_manager()

# Share with test blueprint
import routes.test as test_routes
test_routes.test_execution = test_execution

@app.route('/api/test/scripts')
def api_test_scripts():
    """List all test scripts from /home/NUI/test_script/"""
    try:
        script_dir = '/home/NUI/test_script'
        
        if not os.path.exists(script_dir):
            return jsonify({'error': f'Script directory not found: {script_dir}', 'scripts': []})
        
        # List all .sh files
        scripts = []
        for filename in os.listdir(script_dir):
            if filename.endswith('.sh'):
                filepath = os.path.join(script_dir, filename)
                if os.path.isfile(filepath):
                    scripts.append(filename)
        
        # Sort alphabetically
        scripts.sort()
        
        return jsonify({'scripts': scripts, 'script_dir': script_dir})
    except Exception as e:
        return jsonify({'error': str(e), 'scripts': []})


@app.route('/api/test/bins')
def api_test_bins():
    """List all .zst files from /home/"""
    try:
        bin_dir = '/home'
        
        if not os.path.exists(bin_dir):
            return jsonify({'error': f'Bin directory not found: {bin_dir}', 'bins': []})
        
        # List all .zst files
        bins = []
        for filename in os.listdir(bin_dir):
            if filename.endswith('.zst'):
                filepath = os.path.join(bin_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    bins.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })
        
        # Sort by modification time, newest first
        bins.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({'bins': bins, 'bin_dir': bin_dir})
    except Exception as e:
        return jsonify({'error': str(e), 'bins': []})


@app.route('/api/test/topology-types')
def api_test_topology_types():
    """Return available topology types"""
    topology_types = ['copper', 'optics_one', 'optics_two', 'default', '400g', 'aec']
    return jsonify({'types': topology_types})


@app.route('/api/test/topology-files/<platform>')
def api_test_topology_files_for_platform(platform):
    """List topology JSON files for a specific platform"""
    try:
        platform_upper = platform.upper()
        # Use absolute path from the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        topology_dir = os.path.join(script_dir, 'Topology', platform_upper)
        
        if not os.path.exists(topology_dir):
            return jsonify({'error': f'Topology directory not found for platform: {platform}', 'files': []})
        
        # List all JSON files
        files = []
        for filename in os.listdir(topology_dir):
            if filename.endswith('.json') or filename.endswith('_JSON') or filename.endswith('.materialized_JSON'):
                filepath = os.path.join(topology_dir, filename)
                if os.path.isfile(filepath):
                    files.append(filename)
        
        # Sort alphabetically
        files.sort()
        
        return jsonify({'files': files, 'platform': platform_upper, 'topology_dir': topology_dir})
    except Exception as e:
        return jsonify({'error': str(e), 'files': []})


@app.route('/api/test/upload-bin', methods=['POST'])
def api_test_upload_bin():
    """Upload a custom .zst file to /home/"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.zst'):
            return jsonify({'success': False, 'error': 'Only .zst files are allowed'}), 400
        
        # Save file to /home/
        bin_dir = '/home'
        filepath = os.path.join(bin_dir, file.filename)
        
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'path': filepath,
            'message': f'File uploaded successfully: {file.filename}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/test/kill-processes', methods=['POST'])
def api_test_kill_processes():
    """Kill all test-related processes and their child processes"""
    global CURRENT_TEST_EXECUTION
    
    try:
        killed_processes = []
        errors = []
        
        # List of process patterns to kill
        process_patterns = [
            'run_all_test.sh',
            'Agent_HW_TX_test.sh',
            'ExitEVT.sh',
            'Link_T0_test.sh',
            'Prbs_test.sh',
            'SAI_TX_test.sh',
            'sai_mono_link_test',
            'fboss2',
            'wedge_agent'
        ]
        
        print(f'[STOP TEST] Attempting to kill test processes and their children...', flush=True)
        
        # Method 1: Find parent PIDs and kill entire process tree
        for pattern in process_patterns:
            try:
                # Find processes matching pattern
                result = subprocess.run(
                    ['bash', '-c', f'pgrep -f "{pattern}"'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    print(f'[STOP TEST] Found {len(pids)} processes for pattern "{pattern}"', flush=True)
                    
                    for pid in pids:
                        try:
                            # First, find all child processes
                            children_result = subprocess.run(
                                ['bash', '-c', f'pgrep -P {pid}'],
                                capture_output=True,
                                text=True,
                                timeout=3
                            )
                            
                            # Kill children first
                            if children_result.returncode == 0 and children_result.stdout.strip():
                                child_pids = children_result.stdout.strip().split('\n')
                                print(f'[STOP TEST] Found {len(child_pids)} child processes for PID {pid}', flush=True)
                                for child_pid in child_pids:
                                    try:
                                        subprocess.run(['kill', '-9', child_pid], timeout=2, check=True)
                                        killed_processes.append(f'{pattern} child (PID: {child_pid})')
                                        print(f'[STOP TEST] Killed child process (PID: {child_pid})', flush=True)
                                    except Exception as e:
                                        print(f'[STOP TEST] Failed to kill child {child_pid}: {e}', flush=True)
                            
                            # Then kill parent process
                            subprocess.run(['kill', '-9', pid], timeout=2, check=True)
                            killed_processes.append(f'{pattern} (PID: {pid})')
                            print(f'[STOP TEST] Killed {pattern} (PID: {pid})', flush=True)
                        except Exception as e:
                            error_msg = f'Failed to kill {pattern} (PID: {pid}): {e}'
                            errors.append(error_msg)
                            print(f'[STOP TEST] {error_msg}', flush=True)
            except Exception as e:
                print(f'[STOP TEST] Error searching for {pattern}: {e}', flush=True)
        
        # Method 2: Use pkill with -9 to kill entire process groups (more aggressive)
        print(f'[STOP TEST] Using pkill as fallback to kill any remaining processes...', flush=True)
        for pattern in process_patterns:
            try:
                # pkill -9 will kill the process and send SIGKILL to children
                result = subprocess.run(
                    ['pkill', '-9', '-f', pattern],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    print(f'[STOP TEST] pkill succeeded for pattern "{pattern}"', flush=True)
            except Exception as e:
                print(f'[STOP TEST] pkill failed for {pattern}: {e}', flush=True)
        
        # Method 3: Use killall as additional fallback
        print(f'[STOP TEST] Using killall as final fallback...', flush=True)
        killall_patterns = ['sai_mono_link_test', 'fboss2', 'wedge_agent']
        for pattern in killall_patterns:
            try:
                subprocess.run(['killall', '-9', pattern], capture_output=True, timeout=3)
                print(f'[STOP TEST] killall executed for {pattern}', flush=True)
            except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
                pass  # killall failed, process may not exist
        
        # Reset global test execution state
        CURRENT_TEST_EXECUTION = {
            'running': False,
            'script': None,
            'bin': None,
            'test_level': None,
            'topology': None,
            'topology_file': None,
            'pid': None,
            'start_time': None
        }
        
        message = f'Killed {len(killed_processes)} processes'
        if errors:
            message += f' (with {len(errors)} errors)'
        
        print(f'[STOP TEST] {message}', flush=True)
        
        return jsonify({
            'success': True,
            'killed': killed_processes,
            'errors': errors,
            'message': message
        })
    except Exception as e:
        error_msg = f'Exception in kill-processes: {str(e)}'
        print(f'[STOP TEST] {error_msg}', flush=True)
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/api/test/start', methods=['POST'])
@limiter.limit(config.RATE_LIMIT_TEST_START)
def api_test_start():
    """Start test execution with topology apply"""
    from utils.validators import is_safe_filename, sanitize_command_arg, validate_test_items
    
    global CURRENT_TEST_EXECUTION
    
    try:
        data = request.get_json()
        script = data.get('script')
        bin_file = data.get('bin')
        test_level = data.get('test_level')  # For SAI_TX_test.sh and Agent_HW_T0_test.sh
        topology = data.get('topology')  # For Link_T0_test.sh, ExitEVT.sh, run_all_test.sh (can be comma-separated)
        topology_file = data.get('topology_file')  # For run_all_test.sh
        test_items = data.get('test_items')  # New: For run_all_test.sh test item selection
        new_bin_uploaded = data.get('new_bin_uploaded', False)
        clean_fboss = data.get('clean_fboss', False)  # New option to clean /opt/fboss
        
        if not script:
            return jsonify({'success': False, 'error': 'Script is required'}), 400
        
        # Validate script filename
        if not is_safe_filename(script):
            logger.warning(f"[API] Invalid script filename rejected: {script}")
            return jsonify({'success': False, 'error': 'Invalid script filename'}), 400
        
        if not bin_file:
            return jsonify({'success': False, 'error': 'Bin file is required'}), 400
        
        # Validate bin filename
        if not is_safe_filename(bin_file):
            logger.warning(f"[API] Invalid bin filename rejected: {bin_file}")
            return jsonify({'success': False, 'error': 'Invalid bin filename'}), 400
        
        # Validate test_items if provided
        if test_items and not validate_test_items(test_items):
            logger.warning(f"[API] Invalid test items rejected")
            return jsonify({'success': False, 'error': 'Invalid test items'}), 400
        
        # Validate topology filename if provided
        if topology_file and not is_safe_filename(topology_file):
            logger.warning(f"[API] Invalid topology filename rejected: {topology_file}")
            return jsonify({'success': False, 'error': 'Invalid topology filename'}), 400
        
        # Get current platform
        platform = get_cached_platform() or get_platform_name()
        if not platform:
            return jsonify({'success': False, 'error': 'Platform not detected'}), 400
        
        # Get DUT IP (try to detect from request or use localhost)
        dut_ip = request.host.split(':')[0] if request.host else 'localhost'
        
        curl_commands = []
        
        # Note: Topology application is handled by frontend BEFORE calling this endpoint
        # The frontend calls /api/apply_topology first, then calls /api/test/start
        # So we don't need to (and shouldn't) apply topology here - it creates a deadlock
        
        # Generate curl command for topology apply if topology_file was provided
        if topology_file and script == 'run_all_test.sh':
            curl_cmd = f'''# Step 1: Apply Topology (already done by frontend)
curl -X POST http://{dut_ip}:5000/api/apply_topology \\
  -H "Content-Type: application/json" \\
  -d '{{"platform": "{platform.lower()}", "config_filename": "{topology_file}"}}'
'''
            curl_commands.append(curl_cmd)
        
        # Step 2: Kill previous test processes
        try:
            with app.test_client() as client:
                client.post('/api/test/kill-processes')
        except Exception as e:
            print(f'[TEST_START] Warning: Failed to kill previous processes: {e}', flush=True)
            pass  # Continue even if process cleanup fails
        
        # Step 3: Remove /opt/fboss if user selected clean_fboss option or new bin uploaded
        if clean_fboss or new_bin_uploaded:
            try:
                fboss_dir = '/opt/fboss'
                if os.path.exists(fboss_dir):
                    print(f'[TEST_START] Cleaning /opt/fboss directory (clean_fboss={clean_fboss}, new_bin_uploaded={new_bin_uploaded})', flush=True)
                    subprocess.run(['rm', '-rf', fboss_dir], timeout=10)
                    print(f'[TEST_START] /opt/fboss directory removed successfully', flush=True)
            except Exception as e:
                print(f'Warning: Failed to remove /opt/fboss: {e}', flush=True)
        
        # Step 4: Execute test script with appropriate parameters
        script_dir = '/home/NUI/test_script'
        script_path = os.path.join(script_dir, script)
        
        if not os.path.exists(script_path):
            return jsonify({
                'success': False,
                'error': f'Script not found: {script_path}'
            }), 404
        
        # Build command based on script type
        if script in ['SAI_TX_test.sh', 'Agent_HW_T0_test.sh']:
            # Usage: ./SAI_TX_test.sh <zst_version> [test_level]
            # Usage: ./Agent_HW_T0_test.sh <zst_version> [test_level]
            if not test_level:
                return jsonify({'success': False, 'error': f'Test level (t0 or t1) is required for {script}'}), 400
            cmd = f'cd {script_dir} && ./{script} {bin_file} {test_level}'
        elif script in ['Link_T0_test.sh', 'Link_T1_test.sh', 'ExitEVT.sh']:
            # Usage: ./Link_T0_test.sh <zst_version> <topology_name> [test_cases]
            # Usage: ./Link_T1_test.sh <zst_version> <topology_name> [test_cases]
            # Usage: ./ExitEVT.sh <zst_version> <topology_name> [test_cases]
            if topology:
                cmd = f'cd {script_dir} && ./{script} {bin_file} {topology}'
            else:
                return jsonify({'success': False, 'error': 'Topology name is required for this script'}), 400
        elif script == 'run_all_test.sh':
            # Usage: ./run_all_test.sh <zst_version> <topology_name> [test_items]
            if topology:
                # Build test_items string if provided
                test_items_str = ''
                if test_items and isinstance(test_items, dict):
                    print(f'[TEST_START] Received test_items: {test_items}', flush=True)
                    # Convert test_items dict to comma-separated string
                    # Support two formats:
                    # Format 1 (array): {sai: ['t0', 't1'], agenthw: ['t0', 't2'], link: true, evt: true}
                    # Format 2 (flat): {sai_t0: true, sai_t1: false, agent_t0: true, agent_t1: false, link: true, evt: true}
                    selected_items = []
                    
                    # Check if using flat format (sai_t0, agent_t0, link_t0, etc.)
                    # Look for any key that matches flat format pattern
                    flat_format_keys = ['sai_t0', 'sai_t1', 'sai_t2', 'agent_t0', 'agent_t1', 'agent_t2', 
                                       'link_t0', 'link', 'evt', 'evt_exit']
                    has_flat_format = any(key in flat_format_keys for key in test_items.keys())
                    
                    print(f'[TEST_START] Using flat format: {has_flat_format}', flush=True)
                    
                    if has_flat_format:
                        # Process flat format
                        # SAI tests: sai_t0, sai_t1, sai_t2
                        for level in ['t0', 't1', 't2']:
                            if test_items.get(f'sai_{level}'):
                                selected_items.append(f'SAI_{level.upper()}')
                        
                        # Agent HW tests: agent_t0, agent_t1, agent_t2
                        for level in ['t0', 't1', 't2']:
                            if test_items.get(f'agent_{level}'):
                                selected_items.append(f'AGENT_{level.upper()}')
                        
                        # Link tests: link_t0, link_t1, link_t2 (accept both 'link' and individual levels)
                        if test_items.get('link') or test_items.get('link_test'):
                            # If parent checkbox is checked, check individual levels
                            for level in ['t0', 't1', 't2']:
                                if test_items.get(f'link_{level}'):
                                    selected_items.append(f'LINK_{level.upper()}')
                        else:
                            # Check individual link levels even if parent not checked
                            for level in ['t0', 't1', 't2']:
                                if test_items.get(f'link_{level}'):
                                    selected_items.append(f'LINK_{level.upper()}')
                        
                        # EVT Exit test
                        if test_items.get('evt') or test_items.get('evt_exit'):
                            selected_items.append('EVT_EXIT')
                    else:
                        # Process array format (original)
                        # Process SAI test levels
                        if 'sai' in test_items and isinstance(test_items['sai'], list):
                            for level in test_items['sai']:
                                selected_items.append(f'SAI_{level.upper()}')
                        
                        # Process Agent HW test levels
                        if 'agenthw' in test_items and isinstance(test_items['agenthw'], list):
                            for level in test_items['agenthw']:
                                selected_items.append(f'AGENT_{level.upper()}')
                        
                        # Process Link test
                        if 'link' in test_items and test_items['link']:
                            selected_items.append('LINK_T0')
                        
                        # Process EVT Exit test (accept both 'evt' and 'evt_exit')
                        if ('evt' in test_items and test_items['evt']) or ('evt_exit' in test_items and test_items['evt_exit']):
                            selected_items.append('EVT_EXIT')
                    
                    if selected_items:
                        test_items_str = ','.join(selected_items)
                        print(f'[TEST_START] Generated test_items_str: "{test_items_str}"', flush=True)
                        print(f'[TEST_START] Selected items: {selected_items}', flush=True)
                    else:
                        print(f'[TEST_START] WARNING: No test items selected! test_items was: {test_items}', flush=True)
                else:
                    print(f'[TEST_START] No test_items provided or invalid format. Running all default tests.', flush=True)
                
                if test_items_str:
                    cmd = f"cd {script_dir} && ./{script} {bin_file} {topology} '{test_items_str}'"
                    print(f'[TEST_START] Command: {cmd}', flush=True)
                else:
                    cmd = f'cd {script_dir} && ./{script} {bin_file} {topology}'
                    print(f'[TEST_START] Command (no test items): {cmd}', flush=True)
            else:
                return jsonify({'success': False, 'error': 'Topology type is required for this script'}), 400
        elif script == 'Prbs_test.sh':
            # Usage: ./Prbs_test.sh <zst_version>
            cmd = f'cd {script_dir} && ./{script} {bin_file}'
        else:
            # Default: script + bin
            cmd = f'cd {script_dir} && ./{script} {bin_file}'
        
        # Start test in background
        try:
            print(f'[TEST_START] ============================================', flush=True)
            print(f'[TEST_START] About to execute command: {cmd}', flush=True)
            print(f'[TEST_START] Working directory: {script_dir}', flush=True)
            print(f'[TEST_START] Script path exists: {os.path.exists(script_path)}', flush=True)
            print(f'[TEST_START] ============================================', flush=True)
            
            # Don't redirect stdout/stderr to allow test script to write logs normally
            # The test scripts use 'tee' to write to log files, which won't work if we capture output
            process = subprocess.Popen(
                ['bash', '-c', cmd],
                cwd=script_dir,
                start_new_session=True  # Detach from parent process
            )
            
            print(f'[TEST_START] Process started successfully with PID: {process.pid}', flush=True)
            print(f'[TEST_START] Checking if process is running...', flush=True)
            
            # Wait a moment and check if process is still running
            time.sleep(0.5)
            poll_result = process.poll()
            if poll_result is not None:
                print(f'[TEST_START] WARNING: Process exited immediately with code {poll_result}', flush=True)
            else:
                print(f'[TEST_START] Process confirmed running (PID {process.pid})', flush=True)
            
            # Update global test execution state
            CURRENT_TEST_EXECUTION = {
                'running': True,
                'script': script,
                'bin': bin_file,
                'test_level': test_level,
                'topology': topology,
                'topology_file': topology_file,
                'pid': process.pid,
                'start_time': datetime.now().isoformat()
            }
            
            # Generate curl command for test start
            request_data_str = f'{{"script": "{script}", "bin": "{bin_file}"'
            if test_level:
                request_data_str += f', "test_level": "{test_level}"'
            if topology:
                request_data_str += f', "topology": "{topology}"'
            if topology_file:
                request_data_str += f', "topology_file": "{topology_file}"'
            if test_items:
                import json
                request_data_str += f', "test_items": {json.dumps(test_items)}'
            request_data_str += f', "new_bin_uploaded": {str(new_bin_uploaded).lower()}}}'
            
            curl_cmd = f'''# Step 2: Start Test
curl -X POST http://{dut_ip}:5000/api/test/start \\
  -H "Content-Type: application/json" \\
  -d '{request_data_str}'
'''
            curl_commands.append(curl_cmd)
            
            return jsonify({
                'success': True,
                'message': f'Test started: {script} with {bin_file}',
                'pid': process.pid,
                'curl_commands': curl_commands,
                'curl_text': '\n'.join(curl_commands)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to start test: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/test/status')
def api_test_status():
    """Check if any test is currently running"""
    global CURRENT_TEST_EXECUTION
    
    try:
        # Check if we have a tracked test
        if CURRENT_TEST_EXECUTION['running'] and CURRENT_TEST_EXECUTION['pid']:
            # Verify process is still running
            try:
                # Check if process exists
                result = subprocess.run(
                    ['ps', '-p', str(CURRENT_TEST_EXECUTION['pid'])],
                    capture_output=True,
                    timeout=2
                )
                
                if result.returncode == 0:
                    # Process is still running
                    return jsonify({
                        'running': True,
                        'script': CURRENT_TEST_EXECUTION['script'],
                        'bin': CURRENT_TEST_EXECUTION['bin'],
                        'topology': CURRENT_TEST_EXECUTION['topology'],
                        'pid': CURRENT_TEST_EXECUTION['pid'],
                        'start_time': CURRENT_TEST_EXECUTION['start_time']
                    })
                else:
                    # Process has finished
                    CURRENT_TEST_EXECUTION['running'] = False
            except (ProcessLookupError, OSError):
                CURRENT_TEST_EXECUTION['running'] = False  # Process no longer exists
        
        # Fallback: Check for any test-related processes
        test_processes = [
            'run_all_test.sh',
            'Agent_HW_TX_test.sh',
            'ExitEVT.sh',
            'Link_T0_test.sh',
            'Prbs_test.sh',
            'SAI_TX_test.sh'
        ]
        
        for process_name in test_processes:
            try:
                result = subprocess.run(
                    ['pgrep', '-f', process_name],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    return jsonify({
                        'running': True,
                        'script': process_name,
                        'pid': int(result.stdout.strip().split('\n')[0])
                    })
            except (subprocess.SubprocessError, subprocess.TimeoutExpired, ValueError, IndexError):
                pass  # Process check failed, try next process
        
        return jsonify({'running': False})
        
    except Exception as e:
        return jsonify({'running': False, 'error': str(e)})


# ============================================================================
# Test Procedure Save/Load API Endpoints
# ============================================================================

TEST_PROCEDURES_DIR = os.path.join(os.getcwd(), 'test_procedures')

# Ensure test procedures directory exists
if not os.path.exists(TEST_PROCEDURES_DIR):
    os.makedirs(TEST_PROCEDURES_DIR)

@app.route('/api/test/procedures', methods=['GET'])
def api_test_procedures_list():
    """Get list of saved test procedures"""
    try:
        if not os.path.exists(TEST_PROCEDURES_DIR):
            return jsonify({'procedures': []})
        
        procedures = []
        for filename in os.listdir(TEST_PROCEDURES_DIR):
            if filename.endswith('.json'):
                procedures.append(filename[:-5])  # Remove .json extension
        
        procedures.sort()
        return jsonify({'procedures': procedures})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/procedures/<procedure_name>', methods=['GET'])
def api_test_procedure_get(procedure_name):
    """Get a specific saved test procedure"""
    try:
        filename = f"{procedure_name}.json"
        filepath = os.path.join(TEST_PROCEDURES_DIR, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Procedure not found'}), 404
        
        with open(filepath, 'r') as f:
            config = json.load(f)
        
        # PROACTIVE FIX: Check if loaded config is nested (contains 'name' and 'config' keys)
        # This handles files that were saved incorrectly (like Evn_Test.json)
        
        # DEBUG TRACE
        try:
            with open('/home/NUI/debug_output.log', 'a') as df:
                df.write(f'[{datetime.now()}] Loading {procedure_name}. Config type: {type(config)}. Keys: {config.keys() if isinstance(config, dict) else "N/A"}\n')
        except:
            pass
            
        if isinstance(config, dict) and 'config' in config and 'name' in config:
            # It's a nested structure, unwrap it
            print(f'[Procedure Load] Detected nested config in {filename}, unwrapping...', flush=True)
            try:
                with open('/home/NUI/debug_output.log', 'a') as df:
                    df.write(f'[{datetime.now()}] Unwrapping config...\n')
            except:
                pass
            config = config['config']
        
        response = jsonify({
            'success': True,
            'name': procedure_name,
            'config': config
        })
        response.headers['X-Debug-Version'] = 'FixedValues'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/procedures', methods=['POST'])
def api_test_procedure_save():
    """Save a test procedure"""
    try:
        data = request.get_json()
        name = data.get('name')
        config = data.get('config')
        
        if not name:
            return jsonify({'error': 'Procedure name is required'}), 400
        
        if not config:
            return jsonify({'error': 'Configuration is required'}), 400
        
        # Sanitize filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        
        filename = f"{safe_name}.json"
        filepath = os.path.join(TEST_PROCEDURES_DIR, filename)
        
        # Fix: Ensure we are saving only the inner config if it was wrapped
        if isinstance(config, dict) and 'config' in config and 'name' in config:
             print(f'[Procedure Save] Detected nested config, unwrapping...', flush=True)
             config = config['config']

        # Save procedure
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Test procedure "{name}" saved successfully',
            'filename': safe_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/procedures/<procedure_name>', methods=['DELETE'])
def api_test_procedure_delete(procedure_name):
    """Delete a saved test procedure"""
    try:
        filename = f"{procedure_name}.json"
        filepath = os.path.join(TEST_PROCEDURES_DIR, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Procedure not found'}), 404
        
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': f'Test procedure "{procedure_name}" deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# DUT Local API - APIs to be called by Monitor to check DUT status
# ============================================================================

@app.route('/api/dut/testing/status', methods=['GET'])
def api_dut_testing_status():
    """DUT Local API: Check if this DUT is currently running tests.
    
    This API runs on the DUT itself and checks local processes.
    Monitor will call this API to determine if DUT is testing.
    
    Response:
    {
        "testing": true,
        "processes": ["/opt/fboss/bin/wedge_agent", "/opt/fboss/bin/hw_test"],
        "process_count": 2,
        "timestamp": "2026-01-22T10:30:00"
    }
    """
    try:
        processes = []
        is_testing = False
        
        # Check for test scripts
        test_scripts = [
            'run_all_test.sh',
            'Agent_HW_TX_test.sh',
            'ExitEVT.sh',
            'Link_T0_test.sh',
            'Link_T1_test.sh',
            'Prbs_test.sh',
            'SAI_TX_test.sh'
        ]
        
        for script in test_scripts:
            result = subprocess.run(
                ['pgrep', '-f', script],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0 and result.stdout.strip():
                is_testing = True
                processes.append(script)
        
        # Also check for any process from /opt/fboss/bin/ directory
        result = subprocess.run(
            "ps aux | grep /opt/fboss/bin/ | grep -v grep",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip() != '':
            is_testing = True
            # Extract process names
            for line in result.stdout.strip().split('\n'):
                # Try to extract the executable path from ps output
                parts = line.split()
                for part in parts:
                    if '/opt/fboss/bin/' in part:
                        if part not in processes:
                            processes.append(part)
                        break
        
        return jsonify({
            'testing': is_testing,
            'processes': processes,
            'process_count': len(processes),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'testing': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/dut/health', methods=['GET'])
def api_dut_health():
    """DUT Local API: Health check endpoint.
    
    Simple health check that Monitor can use to verify DUT is responsive.
    
    Response:
    {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": "2026-01-22T10:30:00"
    }
    """
    version_file = 'VERSION'
    version = 'unknown'
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r') as f:
                version = f.read().strip()
        except (IOError, OSError):
            pass  # Version file exists but cannot be read
    
    return jsonify({
        'status': 'healthy',
        'version': version,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/dut/reports/<platform>', methods=['GET'])
def api_dut_list_reports(platform):
    """DUT Local API: List available test reports for a platform.
    
    Response:
    {
        "success": true,
        "platform": "MINIPACK3BA",
        "reports": [
            {
                "date": "2026-01-21",
                "is_tarball": true,
                "filename": "all_test_2026-01-21.tar.gz"
            },
            {
                "date": "2026-01-20",
                "is_tarball": false,
                "filename": "all_test_2026-01-20"
            }
        ],
        "count": 2
    }
    """
    try:
        report_path = os.path.join('/home/NUI/test_report', platform)
        
        if not os.path.exists(report_path):
            return jsonify({
                'success': True,
                'platform': platform,
                'reports': [],
                'count': 0,
                'note': 'Report directory does not exist'
            })
        
        reports = []
        
        # List all files and directories
        for item in os.listdir(report_path):
            if item.startswith('all_test_'):
                item_path = os.path.join(report_path, item)
                is_tarball = item.endswith('.tar.gz')
                
                # Extract date
                if is_tarball:
                    date_str = item.replace('all_test_', '').replace('.tar.gz', '')
                else:
                    date_str = item.replace('all_test_', '')
                
                # Validate date format
                try:
                    datetime.strptime(date_str, '%Y-%m-%d')
                    reports.append({
                        'date': date_str,
                        'is_tarball': is_tarball,
                        'filename': item
                    })
                except ValueError:
                    # Skip invalid date formats
                    pass
        
        # Sort by date (newest first)
        reports.sort(key=lambda x: x['date'], reverse=True)
        
        return jsonify({
            'success': True,
            'platform': platform,
            'reports': reports,
            'count': len(reports)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'platform': platform
        }), 500


# ============================================================================
# Background monitor will be started from __main__ with a reloader-safe guard


if __name__ == '__main__':
    # Detect and cache current platform on startup
    detect_and_cache_current_platform()
    
    # Use DEBUG from config
    DEBUG = config.DEBUG
    
    # Start monitor thread in the serving process:
    # - When debug with reloader: only when WERKZEUG_RUN_MAIN == 'true'
    # - When not debug: start immediately
    if (os.environ.get('WERKZEUG_RUN_MAIN') == 'true') or (not DEBUG):
        logger.info("Starting background monitoring threads...")
        
        # Pre-generate all dashboard caches to avoid empty trend data
        logger.info("Pre-generating dashboard caches...")
        try:
            dashboard.pregenerate_all_caches()
            logger.info("Dashboard cache pre-generation complete")
        except Exception as e:
            logger.error(f"Error during cache pre-generation: {e}")
        
        # Start service monitoring thread
        t = threading.Thread(
            target=monitor_services, 
            kwargs={'poll_interval': config.MONITOR_INTERVAL}, 
            daemon=True
        )
        t.start()
        logger.info(f"Service monitor started (interval: {config.MONITOR_INTERVAL}s)")
        
        # Start transceiver monitoring thread
        t_transceiver = threading.Thread(
            target=monitor_transceivers, 
            kwargs={'poll_interval': config.TRANSCEIVER_MONITOR_INTERVAL}, 
            daemon=True
        )
        t_transceiver.start()
        logger.info(f"Transceiver monitor started (interval: {config.TRANSCEIVER_MONITOR_INTERVAL}s)")
        
        # Start Lab Monitor background status checker
        lab_monitor.start_background_status_checker(interval=config.LAB_MONITOR_STATUS_INTERVAL)
        logger.info(f"Lab monitor status checker started (interval: {config.LAB_MONITOR_STATUS_INTERVAL}s)")
        
        # Start Lab Monitor background report checker
        lab_monitor.start_background_report_checker(interval=config.LAB_MONITOR_REPORT_INTERVAL)
        logger.info(f"Lab monitor report checker started (interval: {config.LAB_MONITOR_REPORT_INTERVAL}s)")
        
        logger.info("All background threads started successfully")
    
    # Run Flask application
    logger.info(f"Starting Flask server on {config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=DEBUG)
