# NUI Topology Flask Server

**Version**: v0.0.0.27

This Flask application serves `NUI.html` and provides a comprehensive interface for FBOSS switch management, including topology configuration, link testing, and transceiver monitoring. It also includes a Lab Monitor Dashboard for centralized multi-lab DUT monitoring.

## Features

### 1. Topology Management
- **Visual Configuration**: Interactive port map for creating connections.
- **Multi-Platform Support**: MINIPACK3N, MINIPACK3BA, WEDGE800BACT, WEDGE800CACT.
- **Auto-Save & Apply**: Automatically saves topology and applies configuration via `reconvert.py`.
- **Load/Save**: Manage multiple topology files per platform.

### 2. Service Monitoring
- **Real-time Status**: Monitors `qsfp_service` and `sai_mono_link_test`.
- **Visual Indicators**: LED-style status lights in the header.

### 3. Link Test Execution (Test Info)
- **Live Progress**: Watch test cases execute in real-time.
- **Result Summaries**: Instant Pass/Fail statistics.
- **Report Download**: Download full test reports (.tar.gz) directly from the UI.
- **Live Log Viewer**: Stream test logs as they happen.

### 4. Test Report Dashboard
- **Historical Reports**: View past test results by date and platform.
- **Charts & Statistics**: Visual breakdown of pass/fail rates for SAI, Agent HW, and Link tests.
- **Version Tracking**: Detailed commit and version information for each test run.
- **Access**: `http://localhost:5000/dashboard`

### 5. **[NEW] Lab Monitor Dashboard**
- **Centralized Monitoring**: Monitor multiple labs and DUTs from a central server.
- **Auto-Detection**: Automatically enables when FRUID is not detected (non-platform environment).
- **Hierarchical Structure**: Labs → Platforms → DUTs organization.
- **Drag & Drop**: Intuitive drag-and-drop interface for reorganizing equipment.
- **Real-time Status**: Live monitoring of DUT status (Online/Offline/Testing).
- **Config Management**: Support for multiple configuration types (Config A/B/C).
- **Access**: `http://localhost:5000/lab_monitor` or auto-redirect from `/`
- **Documentation**: See [LAB_MONITOR.md](LAB_MONITOR.md) for detailed usage.

### 6. Transceiver Monitoring (Transceiver Info)
- **Port Map View**: Visual grid showing health of all ports.
- **Detailed Metrics**: Monitor Temperature, Vcc, Tx Bias, and Optical Power.
- **Power Thresholds**: Automatic detection of Warning/Critical power levels.
- **Vendor Info**: display vendor, part number, and serial number.

## Usage

### 1. Setup
Create a `Topology` folder in the workspace root with platform subfolders:
- `Topology/MINIPACK3N/`
- `Topology/MINIPACK3BA/`
- `Topology/WEDGE800BACT/`
- `Topology/WEDGE800CACT/`

### 2. Running
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # on Windows
python app.py
```
Open http://localhost:5000/ in your browser.

### 3. API Endpoints
- `GET /api/platforms`: List supported platforms.
- `GET /api/topology/<platform>`: Get current topology.
- `POST /api/save_topology`: Save topology configuration.
- `POST /api/apply_topology`: Save and apply (run `reconvert.py`).
- `GET /api/test_info`: Get test status and results.
- `GET /api/transceiver_info`: Get transceiver details.

## Documentation
- [SPEC.md](SPEC.md): Technical Specification.
- [TEST_INFO.md](TEST_INFO.md): Test Info feature details.
- [TRANSCEIVER_INFO.md](TRANSCEIVER_INFO.md): Transceiver Info feature details.
- [TOPOLOGY_AUTO_SAVE.md](TOPOLOGY_AUTO_SAVE.md): Auto-save functionality.
