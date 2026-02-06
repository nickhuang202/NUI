# Transceiver Info Feature - NUI Documentation

## Overview

The **Transceiver Info** tab in NUI provides comprehensive real-time monitoring of QSFP transceiver modules. It allows network engineers to verify the physical layer status, check power levels against thresholds, and visualize port status across the switch.

## Features

### 1. Real-Time Status Monitoring
- **Auto-Refresh**: Updates every 30 seconds automatically.
- **Transceiver Presence**: Detects which ports have transceivers inserted.
- **Link State**: Shows physical link state (Up/Down).
- **Vendor Information**: Displays Vendor Name, Part Number, and Serial Number.

### 2. Power Level Analysis
- **Tx/Rx Power Monitoring**: Displays real-time optical power levels per channel (lane).
- **Threshold Validation**: Automatically compares readings against transceiver-specific thresholds:
  - **High Alarm/Warn**: Power too high.
  - **Low Alarm/Warn**: Power too low (e.g., -40 dBm indicating signal loss).
- **Visual Status Indicators**:
  - 🟢 **Good**: All channels within normal range.
  - 🟡 **Warning**: One or more channels in warning range.
  - 🔴 **Critical**: One or more channels in alarm range or signal loss.

### 3. Visual Port Map
A graphical grid representation of all switch ports (matching physical layout):
- **Color-Coded Status**: Instantly identify problem ports (Red/Yellow/Green).
- **Vendor-Based Styling**: Subtle background color differences based on vendor (Eoptolink, Finisar, Innolight, Intel).
- **Interactive Cards**: Hover to see details, click to filter table.
- **Indicators**:
  - **Status Dot**: Overall health.
  - **Temp**: Current temperature.
  - **Vendor Tag**: Manufacturer name.
  - **Pulse Animation**: Critical/Warning ports pulse to attract attention.

### 4. Detailed Data Table
- **Sortable Columns**: Sort by Port, Vendor, Temperature, Vcc, etc.
- **Filtering**: Filter by Vendor or Health Status (Good/Warning/Critical).
- **Detailed Metrics**:
  - Temperature (°C)
  - Supply Voltage (Vcc)
  - Tx Bias Current (mA)
  - Tx Power (mW/dBm)
  - Rx Power (mW/dBm)

## Architecture

### Backend (app.py)

#### API Endpoints

##### `/api/transceiver_info`
Returns parsed transceiver data for all present modules.

**Response Structure:**
```json
{
  "eth1/1/1": {
    "present": true,
    "vendor": "INNOLIGHT",
    "part": "T-DQ4CN01",
    "serial": "123456789",
    "temperature": 35.5,
    "vcc": 3.28,
    "channels": [
      {
        "lane": 0,
        "tx_power": 0.5,
        "tx_dbm": -3.01,
        "rx_power": 0.4,
        "rx_dbm": -3.97,
        "tx_status": "OK",
        "rx_status": "OK"
      }
      // ... more channels
    ],
    "status": "Good", // or Warning/Critical
    "summary": "All channels OK"
  }
}
```

**Data Source**: 
- Executes `fboss2 show transceiver` standard command.
- Parses the table output format alongside detailed JSON/Text data if available.

##### `/api/present_transceivers`
Returns a simple list of ports with transceivers inserted.

##### `/api/absent_ports`
Returns a list of ports where no transceiver is detected.

### Frontend (NUI.html)

#### Status Classification Logic
The frontend (and backend) classifies port health based on power readings:

1. **Critical (Red)**:
   - Rx Power < -15 dBm (Signal Loss)
   - Any value exceeding High/Low Alarm thresholds
2. **Warning (Yellow)**:
   - Any value exceeding High/Low Warning thresholds (but not Alarm)
3. **Good (Green)**:
   - All values within nominal range

#### Visualization
- **View Switcher**: Toggle between "Table View" and "Port Map".
- **Summary Cards**: Top summary showing Count and percentage of Good/Warning/Critical ports.

## Troubleshooting

### "No Transceiver Information Available"
- **Cause**: service `qsfp_service` might be stopped or `fboss2` command failed.
- **Solution**: Check service status indicators in the header.

### "Rx Power -40.00 dBm / -inf"
- **Cause**: No optical signal received (cable unplugged or remote side down).
- **Result**: Port marked as **Critical** (Signal Loss).

### "Unknown Vendor"
- **Cause**: Transceiver EEPROM data unreadable or non-standard format.
- **Solution**: Check if transceiver is properly seated.
