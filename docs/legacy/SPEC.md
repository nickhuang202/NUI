# NUI - FBOSS Configuration Conversion Tool Technical Specification Document

**Version**: v0.0.0.1  
**Last Updated**: 2025-12-25  
**Project**: FBOSS Configuration Conversion and Visualization Management System  
**Status**: Production Ready

---

## Version History

| Version | Date | Changes |
|------|------|---------|
| v0.0.0.27 | 2026-01-09 | Added Test Info tab with real-time test monitoring and reasoning. Added Transceiver Info tab for QSFP monitoring. Added Topology Auto-Save and Apply validation. |
| v0.0.0.1 | 2025-12-25 | Initial version created, integrating convert.py and reconvert.py platform auto-detection, intelligent file source selection, multi-platform support (4 platforms), FRUID file detection, backward compatibility maintained |

---

## 1. Document Overview

NUI (Network User Interface) is a Flask-based web application that provides an interactive visual interface for managing and monitoring FBOSS (Facebook Open Switching System) network topology configurations. The system enables network engineers to configure port connections, visualize network topology, monitor service status in real-time, and validate port pair configurations across multiple switch platforms.

### 1.1 Project Overview

**Purpose:** Simplify network topology configuration and link testing for FBOSS-based switches through an intuitive visual interface.

**Target Users:** Network engineers, test engineers, system administrators working with FBOSS switch platforms.

**Deployment:** Single-server Flask application with web-based frontend accessible via browser.

### 1.2 Key Features

- **Interactive Visual Port Configuration**: Drag-and-click interface for creating port connections
- **Real-time Service & Port Monitoring**: Live status updates with LED indicators
- **Multi-Platform Support**: MINIPACK3N, MINIPACK3BA, WEDGE800BACT, WEDGE800CACT (65-33 ports)
- **Link Test Execution**: Run and monitor link tests with real-time logs and results (Test Info)
- **Transceiver Diagnostics**: Monitor QSFP power levels, temperature, and presence (Transceiver Info)
- **Automatic Platform Detection**: FRUID-based platform identification
- **Dynamic Profile Switching**: 8 profiles supporting 100G-800G speeds (Copper/Optical)
- **Topology File Management**: Multiple topology configurations per platform
- **Smart Validation**: Profile matching and consistency checking
- **Fallback Mechanism**: Automatic topology file fetching from GitHub
- **Zero Configuration**: Auto-detection and initialization on startup
- **Validation Tools**: Standalone scripts for topology consistency verification

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Web Browser                                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    NUI.html (Frontend)                         │  │
│  │  │ Port Grid    │  │ Connection   │  │  Status Monitor  │   │  │
│  │  │ Renderer     │  │ Manager      │  │  (LED/Colors)    │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │ SVG Engine   │  │ Profile      │  │  Tab Navigation  │   │  │
│  │  │ (Lines)      │  │ Switcher     │  │  (Test/Xcvr)     │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │ Test Info    │  │ Transceiver  │  │  File Selector   │   │  │
│  │  │ Viewer       │  │ Monitor      │  │  Modal           │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST API (AJAX Polling: 1s/30s)
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      Flask Backend (app.py)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │  API Layer   │  │  Topology    │  │  Background Monitor      │ │
│  │  (7 Routes)  │  │  Parser      │  │  Thread (1s polling)     │ │
│  │              │  │  (3 formats) │  │  • qsfp_service          │ │
│  └──────────────┘  └──────────────┘  │  • sai_mono_link_test    │ │
│                                       │  • Transceiver Monitor   │ │
│                                       └──────────────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │  FRUID       │  │  File        │  │  Port Status Reader      │ │
│  │  Reader      │  │  Manager     │  │  (fboss2 show port)      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼──────┐  ┌─────────▼────────────┐
│  Local Files   │  │  System Cmds  │  │  GitHub Fallback     │
│  Topology/     │  │  • fboss2     │  │  facebook/fboss      │
│  ├─MINIPACK3N  │  │  • pgrep      │  │  /main/fboss/oss/    │
│  ├─MINIPACK3BA │  │  • curl/wget  │  │  fboss_link_test_    │
│  ├─WEDGE800BACT│  │               │  │  topology/           │
│  └─WEDGE800CACT│  │               │  │                      │
└────────────────┘  └───────────────┘  └──────────────────────┘
```

### 2.2 Component Details

#### Backend Components (app.py)

| Component | Responsibility | Technology |
|-----------|----------------|------------|
| **Flask Web Server** | HTTP server, routing, static file serving | Flask 2.0+ |
| **REST API Layer** | 7 endpoint handlers, request validation | Flask routes |
| **Topology Parser** | Parse 3 formats (FBOSS Config, Materialized JSON, CSV) | Python JSON/CSV |
| **Service Monitor** | Background daemon thread, 1s polling | Python threading |
| **Transceiver Monitor** | Background daemon thread, 30s polling | Python threading |
| **Port Status Reader** | Execute fboss2, parse output, detect errors | subprocess |
| **FRUID Reader** | Auto-detect platform from system file | JSON parser |
| **File Manager** | List files, fetch fallbacks, cache locally | os, subprocess |

#### Frontend Components (NUI.html)

| Component | Responsibility | Technology |
|-----------|----------------|------------|
| **Port Grid Renderer** | Generate dynamic port layout (65/33 ports) | JavaScript DOM |
| **Connection Manager** | Track bidirectional connections, colors | JavaScript Object |
| **SVG Engine** | Draw curved connection lines, filters | SVG Path, Bezier |
| **Profile Switcher** | Cycle through 8 profiles (speed/type) | Event handlers |
| **Status Monitor** | Poll APIs (1s/30s), update LED/colors | AJAX, setInterval |
| **File Selector Modal** | Display file list, load topology | Modal overlay |
| **Group Box Renderer** | Draw upstream/downstream boxes (WEDGE) | CSS absolute positioning |

#### Data Flow

```
User Action (Click Port) 
  → JavaScript Handler 
    → Update connections{} object
      → Draw SVG lines
        → Apply colors to ports
          → Display status message

API Poll (setInterval)
  → fetch('/api/service_status')
    → Update LED states
  → fetch('/api/test_info') (if Test tab active)
    → Update test progress
  → fetch('/api/transceiver_info') (if Xcvr tab active)
    → Update power readings

Topology Load
  → fetch('/api/topology/<platform>?file=X')
    → Parse connections[]
      → Set profileID per port
        → Create bidirectional mapping
          → Render all connections
```

---

## 3. Backend Specification

### 3.1 Technology Stack

- **Language**: Python 3.x
- **Framework**: Flask 2.0+
- **Dependencies**:
  - Flask >= 2.0
  - requests >= 2.0 (optional, for fallback fetching)
- **System Requirements**:
  - Linux environment (for process monitoring)
  - curl or wget (for fallback fetching)
  - fboss2 CLI tool (for port status)

### 3.2 REST API Endpoints

#### 3.2.1 Platform Management

##### `GET /api/platforms`
Returns list of supported platforms.

**Response:**
```json
[
  "MINIPACK3N",
  "MINIPACK3BA",
  "WEDGE800BACT",
  "WEDGE800CACT"
]
```

##### `GET /api/detect_initial`
Auto-detects platform from FRUID file.

**Source**: `/var/facebook/fboss/fruid.json`

**Response:**
```json
{
  "platform": "WEDGE800BACT",
  "preferred_file": "wedge800bact.materialized_JSON",
  "product": "WEDGE800BACT"
}
```

**Detection Rules:**
- `MINIPACK3` or `MINIPACK3BA` → `MINIPACK3BA` platform
- `MINIPACK3N` → `MINIPACK3N` platform
- `WEDGE800BACT` → `WEDGE800BACT` platform
- `WEDGE800CACT` → `WEDGE800CACT` platform

#### 3.2.2 Topology Management

##### `GET /api/topology_files/<platform>`
Lists available topology files (.json, .csv) for a platform.

**Parameters:**
- `platform` (path): Platform name (case-insensitive)

**Process:**
1. Convert platform name to uppercase
2. Check `Topology/<PLATFORM>/` directory
3. List all `.json` and `.csv` files
4. Sort alphabetically
5. Return file list

**Response:**
```json
{
  "platform": "WEDGE800BACT",
  "files": [
    "copper_link.json",
    "optics_link_one.json",
    "optics_link_two.json",
    "wedge800bact.materialized_JSON"
  ]
}
```

**Error Response:**
```json
{
  "platform": "WEDGE800BACT",
  "files": [],
  "error": "Directory not found"
}
```

**Use Case:** Called when user clicks "Load Topology" button to show file selection modal.

##### `GET /api/topology/<platform>?file=<filename>`
Returns parsed topology connections for a platform.

**Parameters:**
- `platform` (path): Platform name
- `file` (query, optional): Specific topology filename

**Response:**
```json
{
  "platform": "WEDGE800BACT",
  "file": "wedge800bact.materialized_JSON",
  "connections": [
    {
      "src": "eth1/1/1",
      "dst": "eth1/2/1",
      "profileID": 39
    },
    {
      "src": "eth1/3/1",
      "dst": "eth1/4/1",
      "profileID": 38
    }
  ]
}
```

#### 3.2.3 Service Monitoring

##### `GET /api/service_status`
Returns current status of monitored services.

**Monitored Services:**
- `qsfp_service`: QSFP transceiver service
- `sai_mono_link_test-sai_impl`: SAI link test service

**Response:**
```json
{
  "qsfp_service": true,
  "sai_mono_link_test-sai_impl": true,
  "sai_mono_link_test-sai_impl_cmd": "sai_mono_link_test-sai_impl --gtest_filter=SaiLinkTest.*",
  "sai_mono_link_test-sai_impl_filter": "SaiLinkTest.*",
  "sai_mono_link_test-sai_impl_message": "sai_mono_link_test-sai_impl --gtest_filter=SaiLinkTest.*\nCurrently testing SaiLinkTest.*"
}
```

**Monitoring Method:**
- Uses `pgrep -f <process_name>` to detect running processes
- Background thread polls every 1 second
- Extracts gtest_filter from command line for SAI tests

##### `GET /api/port_status`
Returns port link states from fboss2.

**Response:**
```json
{
  "ports": {
    "eth1/1/1": {
      "link": "Up",
      "mismatchedNeighbor": false
    },
    "eth1/2/1": {
      "link": "Down",
      "mismatchedNeighbor": false
    },
    "eth1/3/1": {
      "link": "Up",
      "mismatchedNeighbor": true
    }
  }
}
```

**Error Responses:**
- `503`: Services not running
- `404`: fboss2 not found
- `500`: Command execution error
- `504`: Command timeout

**Implementation:**
- Executes `fboss2 show port` command
- Parses output for LinkState and MISMATCHED_NEIGHBOR flags
- 30-second timeout for command execution

#### 3.2.4 Test Information
##### `GET /api/test_info`
Returns status of current link tests.

**Response Structure:**
- `test_running`: boolean
- `test_list`: array of strings (test names)
- `passed_tests`: array of strings
- `failed_tests`: array of strings
- `current_test`: string
- `log_file`: string (path)
- `start_time`: string

##### `GET /api/test_log_tail`
Returns last N lines of current log.

##### `GET /api/test_reports`
Returns list of available report archives.

##### `GET /api/download_report`
Downloads a specific test report.

#### 3.2.5 Transceiver Information
##### `GET /api/transceiver_info`
Returns parsed transceiver details (power, temp, vcc).

##### `GET /api/present_transceivers`
Returns list of ports with present transceivers.

##### `GET /api/absent_ports`
Returns list of ports without transceivers.

#### 3.2.6 Topology Actions
##### `POST /api/save_topology`
Saves current topology to file.

##### `POST /api/apply_topology`
Saves topology and executes `reconvert.py`.

#### 3.3.1 FBOSS Config Format

```json
{
  "sw": {
    "ports": [
      {
        "logicalID": 3,
        "name": "eth1/17/1",
        "speed": 400000,
        "profileID": 38,
        "expectedLLDPValues": {
          "2": "eth1/18/1"
        }
      }
    ]
  }
}
```

**Key Fields:**
- `sw.ports[]`: Array of port configurations
- `name`: Port identifier (ethX/Y/Z format)
- `profileID`: Profile configuration ID
- `speed`: Port speed in Mbps
- `expectedLLDPValues`: Neighbor mapping (key "2" or "name")

#### 3.3.2 Materialized JSON Format

```json
{
  "pimInfo": [
    {
      "interfaces": {
        "eth1/1/1": {
          "neighbor": "eth1/2/1",
          "profileID": 39
        }
      }
    }
  ]
}
```

**Key Fields:**
- `pimInfo[].interfaces`: Interface mapping
- Interface key: Port name
- `neighbor`: Connected port name
- `profileID`: Profile configuration ID

---

## 4. Frontend Specification

### 4.1 Technology Stack

- **HTML5** with semantic markup
- **CSS3** with modern features (Grid, Flexbox, animations)
- **Vanilla JavaScript** (ES6+)
- **SVG** for connection visualization

### 4.2 Layout Architecture

#### 4.2.1 Header Section
- **Platform Selector**: Buttons for 4 platforms
- **Service Indicators**: LED-style status indicators
  - Blue LED: qsfp_service
  - Green LED: sai_mono_link_test
  - Blinking animation when active
  - Tooltip shows current test details
- **Control Buttons**:
  - Load Topology: Opens file selector
  - Quick Connect: Auto-connects ports
  - Clear: Removes all connections

### 4.3 Port Configuration UI

#### 4.3.1 Profile Configuration Matrix

**Note**: Profile 30 is configured as a 2-port profile to support MINIPACK3N service ports.

| Profile ID | Speed | Ports | Type    | Color     | Use Case        |
|-----------|-------|-------|---------|-----------|-----------------|
| 30        | 25G   | 2     | Optical | #B39DDB   | Service ports   |
| 50        | 800G  | 1     | Copper  | #e6e6ff   | High-speed DAC  |
| 45        | 400G  | 2     | Copper  | #ccccff   | Dual DAC        |
| 35        | 400G  | 1     | Copper  | #b3b3ff   | Single DAC      |
| 39        | 800G  | 1     | Optical | #4CAF50   | High-speed optics|
| 38        | 400G  | 2     | Optical | #90EE90   | Dual optics     |
| 30        | 25G   | 2     | Optical | #B39DDB   | Service ports   |
| 25        | 200G  | 2     | Optical | #1565C0   | Medium optics   |
| 23        | 100G  | 2     | Optical | #64B5F6   | Standard optics |
| 47        | 100G  | 1     | Optical | #64B5F6   | Single optics   |

#### 4.3.2 Profile Cycling

**Right-Click (Speed Cycle):**
- Cycles within same port count
- 1-port cycle: 50 → 35 → 39 -> 47 → 50
- 2-port cycle: 45 → 38 → 25 → 23 → 45

**Left-Click on Profile (Port Count Toggle):**
- Switches between 1-port and 2-port cycles
- 1-port → 2-port: Use first profile from 2-port cycle
- 2-port → 1-port: Use first profile from 1-port cycle
- Auto-disconnects existing connections on switch

### 4.4 Connection Management

#### 4.4.0 Special Port Handling

**MINIPACK3N Service Port (Port 65)**

The UI dynamically generates service ports with special sub-port naming:

```javascript
// Standard ports: eth1/1/1, eth1/1/3, eth1/1/5, eth1/1/7
// Service port 65: eth1/65/1, eth1/65/2

const isServicePort = (currentPlatform === 'MINIPACK3N' && i === 65);
const subPorts = isServicePort ? ['1', '2'] : ['1', '3', '5', '7'];
```

**Port Visibility Logic**:
- Detects number of port divs (2 for service port, 4 for standard)
- For 2-port profiles:
  - Service port: Shows both `/1` and `/2`
  - Standard port: Shows `/1` and `/5` (hides `/3` and `/7`)

**Loopback Connection Visualization**

When a port connects to itself (loopback), the UI draws a circle instead of a line:

```javascript
if (port1 === port2) {
  // Draw SVG circle to the right of port
  const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  circle.setAttribute('cx', x + 25);
  circle.setAttribute('cy', y);
  circle.setAttribute('r', 18);
  // Apply same color as connection
}
```

**Use Cases**:
- Testing port self-loopback configurations
- Marking unpaired ports in topology
- Visualizing service port configurations

#### 4.4.1 Connection Workflow

1. **First Click**: Select source port (highlight)
2. **Second Click**: 
   - Same port → Deselect
   - Different port → Create connection
   - Validate profile match
3. **Connection Created**:
   - Assign unique color
   - Draw SVG connection line
   - Apply color to port borders
   - Mark ports as "connected"
4. **Click Connected Port**: Remove connection

### 4.7 File Selection Modal (Load Topology)

#### 4.7.1 Modal Structure

```html
<div class="modal-overlay" id="fileSelectionModal">
  <div class="modal-content">
    <div class="modal-header">Select Topology File - <span id="modalPlatformName"></span></div>
    <div class="modal-body">
      <div class="file-list" id="fileList">
        <!-- Dynamic file items populated by API -->
        <div class="file-item">copper_link.json</div>
        <div class="file-item">optics_link_one.json</div>
        <div class="file-item">optics_link_two.json</div>
        <div class="file-item">wedge800bact.materialized_JSON</div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="modal-btn cancel" onclick="closeFileSelectionModal()">Cancel</button>
    </div>
  </div>
</div>
```

#### 4.7.2 Complete Workflow

**Step 1: User Initiates**
- User clicks "Load Topology" button in header
- Calls `showTopologyFileSelector()` → `showFileSelectionModal(currentPlatform)`

**Step 2: Fetch Available Files**
```javascript
fetch(`/api/topology_files/${platform}`)
  .then(r => r.json())
  .then(data => {
    // data.files = ["copper_link.json", "optics_link_one.json", ...]
    displayFileList(data.files);
  })
```

**Step 3: Display Modal**
- Modal overlay appears with platform name
- File list populated based on current platform:
  - `MINIPACK3N` → `Topology/MINIPACK3N/` files
  - `MINIPACK3BA` → `Topology/MINIPACK3BA/` files
  - `WEDGE800BACT` → `Topology/WEDGE800BACT/` files (3-4 files typically)
  - `WEDGE800CACT` → `Topology/WEDGE800CACT/` files
- Each file shown as clickable item with hover effect

**Step 4: User Selects File**
- User clicks file item → triggers `loadTopologyFile(platform, filename)`
- Modal closes automatically

**Step 5: Load Topology**
```javascript
fetch(`/api/topology/${platform}?file=${encodeURIComponent(filename)}`)
  .then(r => r.json())
  .then(data => {
    // data.connections = [{src: 'eth1/1/1', dst: 'eth1/2/1', profileID: 39}, ...]
    applyTopology(data.connections);
  })
```

**Step 6: Apply to UI**
- Clear all existing connections
- Switch platform if different (update active button, regenerate ports)
- For each connection:
  - Set port container profileID
  - Update profile indicator and speed
  - Create bidirectional connection mapping
  - Assign unique color
  - Draw SVG connection line
- Update status message

**Example:**
```
Platform: WEDGE800BACT
├─ copper_link.json          ← User selects this
├─ optics_link_one.json
├─ optics_link_two.json
└─ wedge800bact.materialized_JSON

Result: All ports configured as copper connections (Profile 35/45/50)
        with corresponding port pairs connected
```

#### 4.7.3 Error Handling

| Error Scenario | Handling |
|----------------|----------|
| No files found | Display: "No topology files available for this platform" |
| API fetch fails | Display: "Failed to load file list" |
| Topology load fails | Status message: "Failed to load topology: {error}" |
| Invalid JSON | Caught by parser, returns empty connections |

---

## 5. Platform Configurations

### 5.1 Platform Summary

| Platform | Ports | Default Profile | Layout | Topology Files | Notes |
|----------|-------|----------------|--------|----------------|-------|
| MINIPACK3N | 65 | 39 (800G Optical) | Multi-row grid | 1 file | Port 65 is service port with `/1` `/2` sub-ports |
| MINIPACK3BA | 65 | 39 (800G Optical) | Multi-row grid | 1 file | Standard port configuration |
| WEDGE800BACT | 33 | 39 (800G Optical) | 4-row grid + grouping | 3-4 files | Upstream/downstream grouping |
| WEDGE800CACT | 33 | 39 (800G Optical) | 4-row grid + grouping | 1 file (shared) | Uses WEDGE800BACT topology |

---

## 6. Deployment

### 6.1 Installation

```bash
# Clone or extract project
cd NUI

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Ensure topology directory exists
mkdir -p Topology/MINIPACK3N
mkdir -p Topology/MINIPACK3BA
mkdir -p Topology/WEDGE800BACT
mkdir -p Topology/WEDGE800CACT
```

### 6.2 Running the Server

**Development Mode:**
```bash
python app.py
```

**Production Mode:**
```bash
# Using gunicorn (recommended)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 6.3 Access

- **URL:** http://localhost:5000/
- **Default Port:** 5000

---

## 7. Quick Reference

### 7.1 Command Cheat Sheet

```bash
# Start Development Server
python app.py
# Access: http://localhost:5000

# Run Validation Tool
python check_port_pairs.py

# Test API Endpoints
curl http://localhost:5000/api/platforms
curl http://localhost:5000/api/topology_files/WEDGE800BACT
curl http://localhost:5000/api/topology/WEDGE800BACT?file=copper_link.json
curl http://localhost:5000/api/service_status
curl http://localhost:5000/api/port_status

# Check Services
ps aux | grep qsfp_service
ps aux | grep sai_mono_link_test
fboss2 show port
```

### 7.2 Keyboard Shortcuts (Frontend)

| Action | Shortcut | Function |
|--------|----------|----------|
| Select Platform | Platform Buttons | Switch between 4 platforms |
| Cycle Speed | Right-Click Container | Cycle profiles (same port count) |
| Toggle Port Count | Left-Click Profile | Switch 1-port ↔ 2-port |
| Connect Ports | Click → Click | Create connection |
| Disconnect | Click Connected Port | Remove connection |
| Quick Connect | Button "Quick Connect" | Auto-pair all ports |
| Clear All | Button "Clear" | Remove all connections |
| Load Topology | Button "Load Topology" | Open file selector |

### 7.3 API Quick Reference

| Endpoint | Method | Returns | Use Case |
|----------|--------|---------|----------|
| `/` | GET | HTML page | Main UI |
| `/api/platforms` | GET | Platform list | Get supported platforms |
| `/api/detect_initial` | GET | Detected platform | Auto-detection on startup |
| `/api/topology_files/<platform>` | GET | File list | Show modal file selector |
| `/api/topology/<platform>` | GET | Connections | Load topology data |
| `/api/service_status` | GET | Service states | Update LED indicators |
| `/api/port_status` | GET | Port link states | Update port colors |
| `/api/test_info` | GET | Test progress | Monitor Link Test |
| `/api/transceiver_info` | GET | Xcvr details | Monitor Transceivers |
| `/api/save_topology` | POST | Success status | Save configuration |
| `/api/apply_topology` | POST | Execution result | Apply configuration |

---

## 8. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| v0.0.0.1 | 2025-12-25 | System | Initial version: Integrated convert.py and reconvert.py platform auto-detection, multi-platform support (MINIPACK3BA/3N, WEDGE800BACT/CACT), intelligent file source selection, FRUID file detection, backward compatibility |
| 1.1 | 2025-12-20 | System | Enhanced with detailed workflow and quick reference |
| 1.0 | 2025-12-20 | System | Initial specification document |

---

## 9. Related Documents

- [convert_reconvert_SPEC.md](convert_reconvert_SPEC.md) - convert.py and reconvert.py detailed technical specification (v0.0.0.1)
- [README.md](README.md) - Project usage instructions
- ~~[CONVERT_UPDATE.md](CONVERT_UPDATE.md)~~ - Integrated into convert_reconvert_SPEC.md (v0.0.0.1)

---

**End of Specification**
