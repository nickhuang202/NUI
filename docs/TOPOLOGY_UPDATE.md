# Topology-Based EVT Testing Update

## Overview
Updated the test scripts and dashboard to support multiple topology configurations for EVT testing. This allows testing different hardware configurations (copper, optical transceivers, various speeds) separately.

## Changes Made

### 1. Test Scripts Modified

#### Link_T0_test.sh
- **Added**: TOPOLOGY_NAME parameter as $2
- **Updated**: Usage message to show topology parameter requirement
- **Modified**: FINAL_ARCHIVE format from `LINK_T0_{PLATFORM}_{VERSION}_{DATE}.tar.gz` to `LINK_T0_{PLATFORM}_{VERSION}_{TOPOLOGY}_{DATE}.tar.gz`
- **Added**: `Topology:${TOPOLOGY_NAME}` line to TEST_STATUS file

**New Usage:**
```bash
./Link_T0_test.sh <zst_version> <topology_name> [test_cases]
Example: ./Link_T0_test.sh fboss_bins_bcm_xgs_20260106.tar.zst default
```

**Supported Topology Names:**
- `default` - Default 800G configuration
- `400g` - 400G configuration
- `optics_one` - Optical transceiver config 1
- `optics_two` - Optical transceiver config 2
- `copper` - Copper DAC configuration

#### ExitEVT.sh
- **Modified**: FINAL_ARCHIVE format from `ExitEVT_{PLATFORM}_{VERSION}_{DATE}.tar.gz` to `ExitEVT_{PLATFORM}_{VERSION}_{TOPOLOGY}_{DATE}.tar.gz`
- **Added**: `Topology:${TOPOLOGY_NAME}` line to TEST_STATUS file
- Note: This script already had TOPOLOGY_NAME as $2, only archive naming was updated

#### run_all_test.sh
- **Modified**: Link_T0_test.sh invocation to pass TOPOLOGY_NAME parameter
- Changed from: `$HOME_TEST_SCRIPT_DIR/Link_T0_test.sh $FBOSS_TAR_ZST`
- Changed to: `$HOME_TEST_SCRIPT_DIR/Link_T0_test.sh $FBOSS_TAR_ZST $TOPOLOGY_NAME`

### 2. Dashboard Backend (dashboard.py)

#### Updated Data Structure
Modified the summary data structure to support 5 separate EVT topology categories:
```python
"link": {
    "t0": {...},
    "ev_default": {...},
    "ev_400g": {...},
    "ev_optics_one": {...},
    "ev_optics_two": {...},
    "ev_copper": {...}
}
```

#### Enhanced Topology Detection
Improved `update_test_stats()` function to extract topology from ExitEVT filenames:
- Searches through filename parts for known topology names
- Handles old format (without topology) by defaulting to "default"
- Supports variations: "400g", "copper", "optics_one", "optics_two"
- Case-insensitive matching

### 3. Dashboard Frontend (dashboard.html)

#### Updated Chart Layout
Replaced single "Link Test EVT" chart with 5 topology-specific charts:
- EVT Default
- EVT 400G
- EVT Optics One
- EVT Optics Two
- EVT Copper

#### Modified Functions
- **renderCharts()**: Now renders 5 separate EVT donut charts
- **showTestDetails()**: Updated level names mapping to include all 5 EVT topologies
- **Chart onclick handlers**: Each EVT chart calls `showTestDetails('link', 'ev_{topology}')`

## Archive Filename Format

### New Format
```
{TEST_TYPE}_{PLATFORM}_{VERSION}_{TOPOLOGY}_{DATE}.tar.gz
```

Examples:
```
LINK_T0_MINIPACK3BA_fboss_bins_20260109_{TOPOLOGY}_2026-01-09-PM02-30.tar.gz
ExitEVT_MINIPACK3BA_fboss_bins_20260109_{TOPOLOGY}_2026-01-09-PM04-15.tar.gz
```

Where `{TOPOLOGY}` can be:
- `default`
- `400g` or `400G`
- `copper`
- `optics_one` or `opticsone`
- `optics_two` or `opticstwo`

### Backward Compatibility
The dashboard maintains backward compatibility with old archive files that don't include topology name. These are automatically categorized as "default" topology.

## Testing Instructions

### Running Tests
1. Run all tests with specific topology:
   ```bash
   ./run_all_test.sh fboss_bins_bcm_xgs_20260109.tar.zst default
   ```

2. Run Link T0 test only:
   ```bash
   ./Link_T0_test.sh fboss_bins_bcm_xgs_20260109.tar.zst copper
   ```

3. Run ExitEVT test only:
   ```bash
   ./ExitEVT.sh fboss_bins_bcm_xgs_20260109.tar.zst optics_one
   ```

### Viewing Results
1. Start the dashboard server:
   ```bash
   python app.py
   ```

2. Open browser to `http://localhost:5000/dashboard`

3. Select platform and date

4. View separate charts for each EVT topology configuration

5. Click on any chart to see detailed pass/fail test items

## File Changes Summary
- ✅ test_script/Link_T0_test.sh - Added topology parameter
- ✅ test_script/ExitEVT.sh - Updated archive naming
- ✅ test_script/run_all_test.sh - Pass topology to Link_T0_test.sh
- ✅ dashboard.py - Support 5 EVT topology types
- ✅ templates/dashboard.html - Display 5 EVT charts

## Benefits
1. **Better Organization**: Separate test results by hardware configuration
2. **Detailed Tracking**: Track pass/fail rates for each topology independently
3. **Flexibility**: Easy to add new topology types in the future
4. **Backward Compatible**: Old test archives still work with the dashboard
5. **Clear Reporting**: Dashboard clearly shows which topology configuration has issues
