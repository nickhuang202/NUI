# convert.py and reconvert.py Technical Specification Document

**Version**: v0.0.0.1  
**Last Updated**: 2025-12-25  
**Status**: Production Ready

## Document Overview

This document describes two complementary Python scripts for processing FBOSS (Facebook Open Switching System) switch configuration file conversion and reconstruction.

## Version History

| Version | Date | Changes |
|------|------|---------|
| v0.0.0.1 | 2025-12-25 | Integrated CONVERT_UPDATE.md and convert_reconvert_SPEC.md, added platform auto-detection, intelligent file source selection, FRUID file detection, multi-platform support (reconvert.py) |

---

---

## convert.py

### Purpose
Converts FBOSS `link_test_configs` JSON format to `link_test_topology` JSON format and provides port pair validation functionality. Supports automatic detection and configuration for four platforms.

### ⭐ New Features (v0.0.0.1)

#### 🎯 Platform Auto-Detection

convert.py now supports automatic detection and configuration for four platforms:

| Platform | Product Name | Configuration File |
|------|-------------|----------|
| **MINIPACK3BA** | MINIPACK3 or MINIPACK3BA | montblanc.materialized_JSON |
| **MINIPACK3N** | MINIPACK3N | minipack3n.materialized_JSON |
| **WEDGE800BACT** | WEDGE800BACT | wedge800bact.materialized_JSON |
| **WEDGE800CACT** | WEDGE800CACT | wedge800bact.materialized_JSON |

#### 📂 Intelligent File Source Selection

**Priority Order**:
1. ✅ Local file (relative to script directory)
2. ✅ Local file (absolute path `/home/NUI/...`)
3. 🌐 GitHub URL (automatic download)

**Local Path Format**: `link_test_configs/<PLATFORM>/<filename>.materialized_JSON`

#### 🔍 FRUID File Detection

The script automatically reads `/var/facebook/fboss/fruid.json` to detect the platform:

```json
{
  "Information": {
    "Product Name": "MINIPACK3"
  }
}
```

Refer to the `api_detect_initial` function implementation in `app.py`.

### Supported Platforms

| Platform | Product Name | Configuration File | GitHub URL | Local Path |
|------|-------------|---------|-----------|----------|
| MINIPACK3BA | MINIPACK3 or MINIPACK3BA | montblanc.materialized_JSON | [GitHub](https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/montblanc.materialized_JSON) | `link_test_configs/MINIPACK3BA/montblanc.materialized_JSON` |
| MINIPACK3N | MINIPACK3N | minipack3n.materialized_JSON | [GitHub](https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/minipack3n.materialized_JSON) | `link_test_configs/MINIPACK3N/minipack3n.materialized_JSON` |
| WEDGE800BACT | WEDGE800BACT | wedge800bact.materialized_JSON | [GitHub](https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/wedge800bact.materialized_JSON) | `link_test_configs/WEDGE800BACT/wedge800bact.materialized_JSON` |
| WEDGE800CACT | WEDGE800CACT | wedge800bact.materialized_JSON | [GitHub](https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/wedge800bact.materialized_JSON) | `link_test_configs/WEDGE800CACT/wedge800bact.materialized_JSON` |

### Main Features

#### 0. Platform Auto-Detection
- **Function**: `detect_platform()`
- **Detection Source**: `/var/facebook/fboss/fruid.json`
- **Detection Logic**:
  1. Read FRUID file
  2. Extract `Product Name` from `Information` section
  3. Map product name to platform code:
     - `MINIPACK3` or `MINIPACK3BA` → `MINIPACK3BA`
     - `MINIPACK3N` → `MINIPACK3N`
     - `WEDGE800BACT` → `WEDGE800BACT`
     - `WEDGE800CACT` → `WEDGE800CACT`
- **Returns**: Platform code or None

#### 1. Configuration Source Selection
- **Function**: `get_config_source(platform=None)`
- **Parameters**: 
  - `platform`: Platform name or None (auto-detection)
- **Priority Order**:
  1. **Local file** (relative to script directory)
  2. **Local file** (absolute path `/home/NUI/...`)
  3. **GitHub URL** (fallback option)
- **Returns**: `(source_path, platform_name)` tuple

#### 2. JSON Loading and Source Support
- **Function**: `load_json(source)`
- **Supported Sources**:
  - HTTP/HTTPS URL
  - Local file path
- **Returns**: Parsed JSON object

#### 3. Topology Generation
- **Function**: `generate_topology(config_json)`
- **Input**: JSON in link_test_configs format
- **Processing Logic**:
  1. Check if input is already in topology format (check for `pimInfo` key)
  2. Extract port information from `sw.ports`
  3. Filter ports with `expectedLLDPValues["2"]` (ports with explicit LLDP neighbors)
  4. Create bidirectional connection mapping
  5. Preserve the actual `profileID` for each port
- **Output**: JSON in topology format, containing:
  ```json
  {
    "platform": "wedge800bact",
    "pimInfo": [
      {
        "slot": 1,
        "pimName": "",
        "interfaces": {
          "port_name": {
            "neighbor": "neighbor_port_name",
            "profileID": <profile_id>,
            "hasTransceiver": true
          }
        },
        "tcvrs": {}
      }
    ]
  }
  ```

#### 4. Port Pair Validation

##### Config Format Validation
- **Function**: `validate_port_pairs(config_json)`
- **Checks**:
  1. **Neighbor pointing**: Whether the port's `expectedLLDPValues` neighbor correctly points to it
  2. **ProfileID matching**: Whether the port pair's `profileID` values are the same
  3. **Speed matching**: Whether the port pair's `speed` values are the same
- **Returns**: List of issues (List[Dict])

##### Topology Format Validation
- **Function**: `validate_topology(topology_json)`
- **Checks**:
  1. **Neighbor pointing**: Whether the interface's `neighbor` correctly points to it
  2. **ProfileID matching**: Whether the interface pair's `profileID` values are the same
- **Returns**: List of issues (List[Dict])

#### 5. Helper Functions

##### Get Expected Neighbor Name
- **Function**: `get_expected_neighbor_name(port: dict)`
- **Handles Formats**:
  - `{"name": "..."}`
  - `{"2": "..."}`
  - Automatically searches for string values containing "eth"

##### Extract Port Number
- **Function**: `extract_port_number(port_name: str)`
- **Format**: `eth1/17/1` → `17`

#### 6. CSV Report Generation
- **Function**: `generate_csv_report(topology_json, source_filename, output_csv)`
- **Format**:
  ```csv
  Port,<filename>
  1,<profileID>
  2,<profileID>
  ...
  33,<profileID>
  ```
- **Range**: Ports 1-33
- **Content**: ProfileID for each port number

#### 7. Validation Report Output
- **Function**: `print_validation_report(config_issues, topology_issues)`
- **Display Content**:
  - Input configuration issue statistics
  - Generated topology issue statistics
  - Detailed issue list (port name, logicalID, neighbor, issue description)
  - Pass/Fail status

### Command Line Arguments

```bash
python convert.py [OPTIONS]
```

| Parameter | Short | Default | Description |
|------|------|--------|------|
| `--config` | `-c` | None (auto-select) | link_test_configs JSON source (URL or local path). If not specified, will auto-select based on platform |
| `--platform` | `-p` | None (auto-detect) | Platform name (MINIPACK3BA/MINIPACK3N/WEDGE800BACT/WEDGE800CACT). If not specified, will auto-detect from fruid.json |
| `--output` | `-o` | Auto-named | Output topology JSON filename. If not specified, will auto-name based on platform (e.g. `montblanc_link_test_topology.json`) |
| `--skip-validation` | - | False | Skip port pair validation |
| `--csv` | - | None | Output CSV report filename |

### Workflow

```
┌─────────────────────┐
│  Run convert.py     │
└──────────┬──────────┘
           │
           ├──> Has -c parameter?
           │    └──> Yes: Use specified config source
           │    └──> No: Continue ↓
           │
           ├──> Has -p parameter?
           │    └──> Yes: Use specified platform
           │    └──> No: Read fruid.json for auto-detection
           │
           ├──> Check local file
           │    └──> Exists: Use local file
           │    └──> Not exists: Download from GitHub
           │
           ├──> Load and convert JSON
           │
           ├──> Validate port pairs (optional)
           │
           └──> Output topology JSON + CSV (optional)
```

**Detailed Steps**:

1. **Detect Platform** (if -c or -p not specified):
   - Read `/var/facebook/fboss/fruid.json`
   - Extract Product Name
   - Map to platform code

2. **Select Config Source**:
   - Check local file first
   - If not exists, use GitHub URL

3. **Load and Convert**:
   - Load config JSON
   - Generate topology JSON
   - Validate port pairs (optional)

4. **Output Results**:
   - Save topology JSON
   - Generate CSV report (optional)
   - Display validation report

1. **Detect Platform** (if -c or -p not specified):
   - Read `/var/facebook/fboss/fruid.json`
   - Extract Product Name
   - Map to platform code

2. **Select Config Source**:
   - Check local file first
   - If not exists, use GitHub URL

3. **Load and Convert**:
   - Load config JSON
   - Generate topology JSON
   - Validate port pairs (optional)

4. **Output Results**:
   - Save topology JSON
   - Generate CSV report (optional)
   - Display validation report

### Usage Examples

#### Fully Automatic Mode (Recommended) ⭐
```bash
# Auto-detect platform, auto-select local file or download, auto-name output
python convert.py

# Automatic mode + CSV report
python convert.py --csv ports.csv
```

#### Manually Specify Platform
```bash
# Specify platform, still auto-selects best file source
python convert.py -p MINIPACK3BA

# Specify platform and output filename
python convert.py -p WEDGE800BACT -o my_topology.json
```

#### Manually Specify Config File (old method still supported)
```bash
# Local file
python convert.py -c /path/to/config.json

# URL
python convert.py -c https://example.com/config.json
```

#### Combined Usage
```bash
# Specify platform, auto-select file source, generate CSV
python convert.py -p MINIPACK3N --csv minipack3n_ports.csv

# Fully manual specification of all parameters
python convert.py -c custom.json -p WEDGE800BACT -o output.json --csv report.csv
```

### Example Output

#### Auto-detect MINIPACK3BA (local file exists)
```bash
$ python convert.py
Detected product: MINIPACK3
Using local file: /home/NUI/link_test_configs/MINIPACK3BA/montblanc.materialized_JSON
Detected platform: MINIPACK3BA
Output file: montblanc_link_test_topology.json
Reading from local file: /home/NUI/link_test_configs/MINIPACK3BA/montblanc.materialized_JSON
Config loaded successfully, generating topology...

Conversion complete! Output file: montblanc_link_test_topology.json
Contains XX interface entries (approximately XX connection pairs)
```

#### Specify MINIPACK3N (local file not exists, auto-download)
```bash
$ python convert.py -p MINIPACK3N
Local file not found, will download from URL: https://raw.githubusercontent.com/...
Detected platform: MINIPACK3N
Output file: minipack3n_link_test_topology.json
Downloading from URL: https://raw.githubusercontent.com/...
Config loaded successfully, generating topology...

Conversion complete! Output file: minipack3n_link_test_topology.json
Contains 40 interface entries (approximately 20 connection pairs)
```

### Platform Detection Example

Assuming `/var/facebook/fboss/fruid.json` content is:
```json
{
  "Information": {
    "Product Name": "MINIPACK3"
  }
}
```

Running `python convert.py` will:
1. Detect platform: `MINIPACK3BA`
2. Look for: `/home/NUI/link_test_configs/MINIPACK3BA/montblanc.materialized_JSON`
3. If not exists, download from GitHub
4. Output: `montblanc_link_test_topology.json`

### Error Handling

#### FRUID File Not Found
```
Warning: FRUID file not found: /var/facebook/fboss/fruid.json
Error: Cannot auto-detect platform, please specify manually using --platform parameter
```

**Solution**: Use `-p` parameter to manually specify platform

#### Unsupported Product Type
```
Detected product: UNKNOWN_PRODUCT
Warning: Unsupported product type: UNKNOWN_PRODUCT
Error: Cannot auto-detect platform, please specify manually using --platform parameter
```

**Solution**: Use `-p` or `-c` parameter to manually specify

### Backward Compatibility

✅ All old usage methods are still supported:
- `-c` parameter to directly specify URL or local path
- `-o` parameter to specify output file
- `--skip-validation` and `--csv` parameters

### Return Values
- `0`: Success with no validation issues
- `1`: Error occurred or validation failed

---

## reconvert.py

### Purpose
Downloads configuration from FBOSS GitHub, removes specific objects, and regenerates port configuration based on topology and speed requirements. Supports dynamic port generation (800G/400G/200G/100G) and multi-platform configuration.

### ⭐ New Features (v0.0.0.1)

#### 🎯 Multi-Platform Support

reconvert.py now supports configuration management for four platforms:

| Platform | Config File | Topology File | CSV Mapping File |
|------|---------|--------------|-------------|
| **minipack3ba** | montblanc.materialized_JSON | Topology/MINIPACK3BA/montblanc.materialized_JSON | montblanc_port_profile_mapping.csv |
| **minipack3n** | minipack3n.materialized_JSON | Topology/MINIPACK3N/minipack3n.materialized_JSON | minipack3n_port_profile_mapping.csv |
| **wedge800bact** | wedge800bact.materialized_JSON | Topology/WEDGE800BACT/wedge800bact.materialized_JSON | wedge800bact_port_profile_mapping.csv |
| **wedge800cact** | wedge800bact.materialized_JSON | Topology/WEDGE800CACT/wedge800bact.materialized_JSON | wedge800bact_port_profile_mapping.csv |

#### 📂 Intelligent File Management

**File Source Priority Order**:
1. ✅ Local file (preferred)
2. 🌐 GitHub URL (automatic download)

**Local File Path Structure**:
```
/home/NUI/
├── link_test_configs/
│   ├── MINIPACK3BA/
│   ├── MINIPACK3N/
│   ├── WEDGE800BACT/
│   └── WEDGE800CACT/
└── Topology/
    ├── MINIPACK3BA/
    ├── MINIPACK3N/
    ├── WEDGE800BACT/
    └── WEDGE800CACT/
```

#### 🔧 Platform Configuration Dictionary

Added `PLATFORMS` dictionary to centrally manage all platform configurations:
- **local**: Local file paths (config, csv, topology)
- **urls**: GitHub URLs (config, csv, topology)
- **output**: Output filenames

### Main Features

#### 1. File Download and Management
- **Function**: `download_file(url, output_file)`
- **Tool**: Uses `curl -o`
- **Purpose**: Download JSON config, CSV mapping, topology files

- **Function**: `get_file(local_path, url, temp_file)`
- **Logic**: 
  1. Check if local file exists
  2. Exists: Use local file
  3. Not exists: Download from URL
- **Purpose**: Intelligent file source selection

#### 2. CSV Mapping Parsing
- **Function**: `parse_csv_mapping(csv_file)`
- **Input**: CSV containing `Port_Name` and `Logical_PortID` fields
- **Output**: Dictionary mapping port names to logical port IDs

#### 3. Profile to Speed Mapping
- **Function**: `parse_profile_speed_mapping(thrift_file)`
- **Source**: `switch_config.thrift` file
- **Parsing Logic**:
  1. Search for `cfg::PortProfileID` or `PROFILE_` definitions
  2. Extract speed from name (800G, 400G, 200G, 100G, 50G, 25G, 10G)
  3. Convert to Mbps (e.g. 400G → 400000)
- **Default Mapping**:
  ```python
  {
    39: 800000,  # 800G
    38: 400000,  # 400G
    37: 200000,  # 200G
    36: 100000,  # 100G
    25: 400000,  # 400G
    23: 100000,  # 100G - Service port profile
    47: 200000,  # 200G
    22: 50000,   # 50G
    21: 25000,   # 25G
    20: 10000,   # 10G
  }
  ```

#### 4. Topology Loading
- **Function**: `load_topology(topology_file)`
- **Structure**: Extracted from `pimInfo[0].interfaces`
- **Output**: Dictionary of port information:
  ```python
  {
    "port_name": {
      "neighbor": "neighbor_port_name",
      "profileID": <profile_id>,
      "hasTransceiver": True
    }
  }
  ```

#### 5. Speed-Based Lane Configuration
- **Function**: `get_lane_suffixes_for_speed(speed)`
- **Mapping Rules**:
  | Speed | Lane Suffix | Port Count |
  |------|-----------|----------|
  | 800G | `/1` | 1 port |
  | 400G | `/1, /5` | 2 ports |
  | 200G | `/1, /3, /5, /7` | 4 ports |
  | 100G | `/1, /2, /3, /4, /5, /6, /7, /8` | 8 ports |

#### 6. Port Name Generation
- **Function**: `generate_port_names_with_topology(topology_info, profile_speed_map)`
- **Logic**:
  1. Process ports 1-64:
     - Check if `eth1/x/1` exists in topology
     - Get the port's `profileID` and corresponding speed
     - Generate appropriate number of lanes based on speed
  2. Process port 65:
     - Service port (service port)
     - Fixed to use `/1` only
  3. Output debug information (speed, Lane, ProfileID)
- **Output**: 
  - `port_names`: List of port names
  - `port_info_map`: Port information mapping

#### 7. Object Creation Functions

##### Port Object
- **Function**: `create_port_object(logical_id, port_name, ingress_vlan, speed, profile_id, neighbor, is_service_port=False)`
- **Included Fields**:
  - logicalID, state, minFrameSize, maxFrameSize
  - speed, profileID, portType
  - expectedLLDPValues (includes neighbor information)
  - pause, loopbackMode, sFlowIngressRate, etc.
- **Special Handling**:
  - Service port (logical_id == 351): `portType = 4`
  - When has neighbor: Set `expectedLLDPValues["2"]`

##### VLAN Object
- **Function**: `create_vlan_object(vlan_id)`
- **Fields**: name, id, recordStats, routable, ipAddresses

##### VLAN Port Object
- **Function**: `create_vlanport_object(vlan_id, logical_port)`
- **Fields**: vlanID, logicalPort, spanningTreeState, emitTags

##### Interface Object
- **Function**: `create_interface_object(vlan_id, ipv6_addr, ipv4_addr)`
- **Fields**: intfID, routerID, vlanID, ipAddresses, mtu, type

#### 8. Main Process (main)

##### Command Line Arguments

```bash
python reconvert.py [--platform PLATFORM]
```

| Parameter | Short | Default | Description |
|------|------|--------|------|
| `--platform` | `-p` | minipack3ba | Platform name (minipack3ba/minipack3n/wedge800bact/wedge800cact) |

##### Default Configuration (using minipack3ba as example)

**URL Sources**:
```python
config_url = "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/link_test_configs/montblanc.materialized_JSON"
csv_url = "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/lib/platform_mapping_v2/platforms/montblanc/montblanc_port_profile_mapping.csv"
topology_url = "https://raw.githubusercontent.com/facebook/fboss/refs/heads/main/fboss/oss/fboss_link_test_topology/montblanc.materialized_JSON"
```

**Local File Paths**:
```python
config_file = "/home/NUI/link_test_configs/MINIPACK3BA/montblanc.materialized_JSON"
csv_file = "/home/NUI/Topology/MINIPACK3BA/montblanc_port_profile_mapping.csv"
topology_file = "/home/NUI/Topology/MINIPACK3BA/montblanc.materialized_JSON"
thrift_file = "/home/NUI/fboss_src/switch_config.thrift"
output_file = "montblanc.materialized_JSON.tmp"
```

##### Execution Steps
1. **Platform Selection**:
   - Read platform name from command line arguments (default: minipack3ba)
   - Load corresponding platform configuration

2. **Preparation Phase**:
   - Check and create topology directory
   - Check local topology file or download from GitHub
   - Load topology information
   - Parse profile speed mapping
   
3. **Download Phase**:
   - Check local config JSON or download from GitHub
   - Check local CSV mapping file or download from GitHub

4. **Configuration Processing Phase**:
   - Read and parse JSON config
   - Parse CSV port mapping
   - Remove existing objects: `ports`, `vlans`, `vlanPorts`, `interfaces`

5. **Port Generation Phase**:
   - Generate port names based on topology and speed
   - Output port generation summary

6. **Object Creation Phase**:
   - Create default VLANs:
     - VLAN 10: `fbossLoopback0` (routable)
     - VLAN 4094: `default` (non-routable)
   - Create default interface (VLAN 10)
   - Iterate through all port names:
     - Create port object (including topology information)
     - Create corresponding VLAN
     - Create VLAN port
     - Create interface (incrementing IP addresses)
   - VLAN ID: Starting from 2001
   - IPv6: Starting from `2401::/64`, incrementing
   - IPv4: Starting from `10.0.0.0/24`, second octet incrementing

7. **Save and Validation Phase**:
   - Insert new objects into configuration
   - Save to output file
   - Output statistics (port count, VLAN count, etc.)
   - Validation summary:
     - Port count by speed
     - Verify service port configuration (logical_id == 351)

8. **Cleanup Phase**:
   - Delete temporary download files

### Usage Examples

#### Default Usage (minipack3ba)
```bash
$ python reconvert.py
Platform: minipack3ba
Checking file: montblanc.materialized_JSON
  ✓ Using local file: /home/NUI/link_test_configs/MINIPACK3BA/montblanc.materialized_JSON
Checking file: montblanc_port_profile_mapping.csv
  ✓ Using local file: /home/NUI/Topology/MINIPACK3BA/montblanc_port_profile_mapping.csv
Checking file: montblanc.materialized_JSON
  ✓ Using local file: /home/NUI/Topology/MINIPACK3BA/montblanc.materialized_JSON
...
Configuration generated successfully!
Output: montblanc.materialized_JSON.tmp
```

#### Specify Platform (wedge800bact)
```bash
$ python reconvert.py -p wedge800bact
Platform: wedge800bact
Checking file: wedge800bact.materialized_JSON
  ✗ Local file not found: /home/NUI/link_test_configs/WEDGE800BACT/wedge800bact.materialized_JSON
  Downloading from URL...
  Downloaded successfully to wedge800bact_config.tmp
...
Configuration generated successfully!
Output: wedge800bact.materialized_JSON.tmp
```

#### All Platform Examples
```bash
# MINIPACK3BA (Montblanc)
python reconvert.py -p minipack3ba

# MINIPACK3N
python reconvert.py -p minipack3n

# WEDGE800BACT
python reconvert.py -p wedge800bact

# WEDGE800CACT
python reconvert.py -p wedge800cact
```

### Service Port Special Handling

Service port identification and configuration:
- **Identification**: `logical_id == 351` or `eth1/65/1`
- **Configuration Characteristics**:
  - `portType = 4`
  - Usually speed is 100G (100000 Mbps)
  - Fixed to use lane `/1` only
- **Validation**: Script confirms service port is correctly configured at the end

### IP Address Configuration Scheme

#### Default Configuration
- **VLAN 10 (fbossLoopback0)**:
  - IPv6: `2531::/64`
  - IPv4: `140.0.0.0/24`

#### Dynamic Configuration (starting from VLAN 2001)
- **IPv6**: `{2401 + index}::/64`
  - Example: 2401::/64, 2402::/64, 2403::/64, ...
- **IPv4**: `{10 + index}.0.0.0/24`
  - Example: 10.0.0.0/24, 11.0.0.0/24, 12.0.0.0/24, ...

### Error Handling

Both scripts include complete error handling:
- File not found checks
- URL download failure handling
- JSON parsing error catching
- Full traceback output

---

## Workflow Integration

### Typical Use Cases

1. **Generate topology from config** (using convert.py):
   ```bash
   python convert.py -c link_test_config.json -o topology.json --csv report.csv
   ```

2. **Rebuild config using topology** (using reconvert.py):
   ```bash
   python reconvert.py
   # Ensure correct topology file exists in Topology/ directory
   ```

### File Dependencies

```
reconvert.py needs:
├── fboss_src/switch_config.thrift (Profile mapping)
├── Topology/MINIPACK3BA/montblanc.materialized_JSON (Topology)
├── CSV mapping file (downloaded from GitHub)
└── Config JSON (downloaded from GitHub)

convert.py produces:
└── link_test_topology JSON (can be used by reconvert.py)
```

---

### Technical Requirements

### Python Version
- Python 3.6+

### Standard Library Dependencies
```python
import json
import argparse
import csv
import re
import subprocess
import os
import sys
import ipaddress
from pathlib import Path
from urllib.request import urlopen
from typing import List, Dict
```

### External Tools
- `curl` (used by reconvert.py)

### New Functions (v0.0.0.1)

#### convert.py New Functions

1. **`detect_platform()`**
   - Read `/var/facebook/fboss/fruid.json`
   - Extract `Information.Product Name`
   - Map to platform code
   - Returns: Platform name or None

2. **`get_config_source(platform=None)`**
   - Auto-detect or use specified platform
   - Check local files (two paths)
   - Fallback to GitHub URL
   - Returns: (source_path, platform_name) tuple

3. **`PLATFORM_CONFIG` Dictionary**
   - Stores configuration for four platforms
   - URLs, local paths, filenames

#### reconvert.py New Functions

1. **`get_file(local_path, url, temp_file)`**
   - Check local file first
   - Auto-download if not exists
   - Returns: Actual file path used

2. **`PLATFORMS` Dictionary**
   - Manages configuration for four platforms
   - Local paths, URLs, output files

3. **Command Line Argument Handling**
   - Added `--platform` / `-p` parameter
   - Supports platform selection

---

## Output Format

### convert.py Output
- **JSON Topology File**: Standard link_test_topology format
- **CSV Report** (optional): Port to ProfileID mapping
- **Console Report**: Validation results and statistics

### reconvert.py Output
- **JSON Config File**: Contains regenerated ports, vlans, vlanPorts, interfaces
- **Console Debug Information**: 
  - Port generation summary
  - Speed configuration details
  - Service port validation
  - Port distribution by speed statistics

---

## Validation and Quality Assurance

### convert.py Validation
- ✅ Port pair bidirectional connection correctness
- ✅ ProfileID consistency
- ✅ Speed matching
- ✅ Neighbor relationship completeness

### reconvert.py Validation
- ✅ Service port configuration correctness (portType, speed)
- ✅ Port count statistics by speed
- ✅ Logical ID uniqueness
- ✅ VLAN and Interface pairing completeness

---

## Notes

1. **convert.py**:
   - Input can be config or topology format, will auto-detect
   - Will still generate output file when validation fails, but returns exit code 1
   - CSV report only includes first 33 ports
   - Supports auto-detection for four platforms (v0.0.0.1+)
   - Local files take priority over URL downloads (v0.0.0.1+)

2. **reconvert.py**:
   - Supports four platform configurations (v0.0.0.1+)
   - Intelligent file source selection (local first) (v0.0.0.1+)
   - Requires network connection to download files (if not locally available)
   - Service port must be logical_id 351
   - Will delete downloaded temporary files, keep generated configuration

3. **Common**:
   - Both scripts support full error traceback
   - Output uses UTF-8 encoding
   - JSON output uses 2-space indentation

---

## Test Results (v0.0.0.1)

### convert.py Tests
- ✅ MINIPACK3BA platform auto-detection - Passed
- ✅ MINIPACK3N local file usage - Passed
- ✅ WEDGE800BACT URL download - Passed
- ✅ WEDGE800CACT configuration - Passed
- ✅ Parameter help text - Correctly displayed
- ✅ Backward compatibility - Maintained

### reconvert.py Tests
- ✅ minipack3ba platform - Passed
- ✅ minipack3n platform - Passed
- ✅ wedge800bact platform - Passed
- ✅ wedge800cact platform - Passed
- ✅ Local file priority logic - Passed
- ✅ URL download fallback - Passed

---

## Version Information

- **Version**: v0.0.0.1
- **Written Date**: 2025-12-25
- **Updated Date**: 2025-12-25
- **Target Platform**: FBOSS (Facebook Open Switching System)
- **Supported Switches**: 
  - MINIPACK3BA (Montblanc)
  - MINIPACK3N
  - WEDGE800BACT
  - WEDGE800CACT

---

## License and Contributions

These scripts are part of the FBOSS ecosystem and follow the related open source license terms.
