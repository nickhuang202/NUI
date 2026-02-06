# SAI Test Status & Features Overview

## Overview
The "Test Info" tab has been enhanced to provide comprehensive status monitoring for SAI/Link tests, service health indicators, and direct test report downloads.

> [!NOTE]
> For detailed technical documentation on the Test Info feature, please refer to [docs/TEST_INFO.md](docs/TEST_INFO.md).

## Key Features

### 1. Service Status Indicators
Located at the top of the interface, these indicators show real-time health of critical background services:
- **QSFP Service**: Monitors `qsfp_service` process.
- **SAI Service**: Monitors `sai_mono_link_test` process.
- **Test Status**: Shows if a test is currently running (Yellow) or completed (Green).

### 2. Test Type Recognition
Automatically identifies and displays the running test type:
- **SAI TEST** (Purple)
- **LINK TEST** (Orange)
- **AGENT HW TEST** (Cyan)

### 3. Live Progress Tracking
During test execution:
- Displays Start Time and current Log File path.
- **Real-time Checklist**:
  - ✓ PASS (Green)
  - ✗ FAIL (Red)
  - ⏳ Testing... (Yellow)
  - ○ Not tested yet (Gray)

### 4. Test Report Download
When testing completes:
- Shows summary statistics (Passed/Failed/Total).
- Provides a **Download Button** for the full report archive (`.tar.gz`).
- Report includes all logs, CSV results, and configuration files.

## Architecture Summary

### Backend (app.py)
- **`/api/test_info`**: Aggregates service status, test progress, and results.
- **`/api/download_report`**: Securely serves generated report archives.
- **Process Monitoring**: Background threads poll system processes (`pgrep`) and file status (`TEST_STATUS` file).

### Frontend
- **Auto-Refresh**: Polls status every second.
- **Dynamic UI**: Switches between "Running" view (checklist) and "Completed" view (results table).

## Related Documentation
- [docs/TEST_INFO.md](docs/TEST_INFO.md) - Detailed technical specification.
- [docs/SPEC.md](docs/SPEC.md) - Full NUI system specification.
