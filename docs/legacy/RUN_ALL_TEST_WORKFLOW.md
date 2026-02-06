# Run All Test Workflow Documentation

## Overview

This document explains the complete execution flow when selecting `run_all_test.sh` in the RUN TEST web interface. The workflow involves frontend user interactions, backend API processing, test script execution, and dashboard result visualization.

---

## 1. Frontend User Operations (NUI.html)

### Load Saved Test Procedure (Optional):

- **Select from dropdown**: Load previously saved test configurations
- **Quick setup**: All parameters (script, bin, topology, options) are loaded automatically
- **Refresh button**: Updates the list of available saved procedures

### User Selects Parameters:

- **Test Script**: `run_all_test.sh`
- **Bin File**: e.g., `fboss_bins_bcm_JC_20251030.tar.zst`
- **Topology Type**: Options include:
  - `copper` - DAC (Direct Attach Copper) cables
  - `default` - Accton Config 1 (800G)
  - `400g` - Accton Config 2 (400G)
  - `optics_one` - Optics Configuration 1
  - `optics_two` - Optics Configuration 2
- **Topology File**: Select from saved topology configuration files (e.g., `copper_link.json`)
- **Clean /opt/fboss Option**: Checkbox to force removal and re-extraction of binaries

### Save Current Test Procedure (Optional):

- **Enter procedure name**: Give the configuration a descriptive name
- **Click "💾 Save Procedure"**: Saves all current selections for future use
- **Reusable configurations**: Quickly repeat the same test setup later

### When "▶️ Start Test" Button is Clicked:

The frontend sends a POST request to the backend:

```javascript
fetch('/api/test/start', {
    method: 'POST',
    body: JSON.stringify({
        script: 'run_all_test.sh',
        bin: 'fboss_bins_bcm_JC_20251030.tar.zst',
        topology: 'copper',
        topology_file: 'copper_link.json',
        clean_fboss: true  // User-selected option to clean /opt/fboss
    })
})
```

---

## 2. Backend API Processing (app.py - `/api/test/start`)

### Step 1: Apply Topology Configuration

**Important Note**: The switch configuration is NOT saved to `/opt/fboss/etc/`, but to the NUI working directory.

If `topology_file` is provided:
- Calls `/api/apply_topology` endpoint internally
- Executes `reconvert.py` with the selected topology file
- Generates switch config and saves to `/home/NUI/[platform].materialized_JSON.tmp`
  - Example: `montblanc.materialized_JSON.tmp` (MINIPACK3BA)
  - Example: `wedge800bact.materialized_JSON.tmp` (WEDGE800BACT)
- Test scripts will use these `.tmp` files as configuration

**reconvert.py Configuration Flow:**
```
User selects topology_file (e.g., copper_link.json)
    ↓
/api/apply_topology called
    ↓
reconvert.py executed: python reconvert.py wedge800bact copper_link.json
    ↓
Loads copper_link.json from link_test_configs/WEDGE800BACT/
    ↓
Generates switch config → /home/NUI/wedge800bact.materialized_JSON.tmp
    ↓
Test scripts reference this .tmp file via $AGENT_CONFIG environment variable
```

### Step 2: Terminate Previous Test Processes

- Calls `/api/test/kill-processes` to clean up any running test processes

### Step 3: Clean Old FBOSS Directory (Optional)

**User can choose to clean `/opt/fboss` directory through checkbox option:**
- If "Clean /opt/fboss" checkbox is checked OR a new .zst file was uploaded
- Executes `rm -rf /opt/fboss`
- Forces re-extraction of all binaries from the .zst file
- Useful when switching between different FBOSS versions or troubleshooting

**Behavior:**
- Checkbox unchecked + no new upload: Uses existing `/opt/fboss` (faster)
- Checkbox checked: Always removes and re-extracts (ensures clean state)
- New bin uploaded: Automatically cleans regardless of checkbox

### Step 4: Start Test Execution

- Builds execution command:
  ```bash
  cd /home/NUI/test_script && ./run_all_test.sh fboss_bins_bcm_JC_20251030.tar.zst copper
  ```
- Runs test in background using `subprocess.Popen`
- Records test state (PID, start time, script name, parameters)

---

## 3. Test Script Execution (test_script/run_all_test.sh)

### Phase 1: Platform Detection and Initialization

```bash
# Load platform configuration
source platform_config.sh

# Detect platform (MINIPACK3BA, MINIPACK3N, WEDGE800BACT, etc.)
echo "$DETECTED_PLATFORM" > /home/NUI/.platform_cache
```

Platform is auto-detected from hardware and cached for dashboard use.

### Phase 2: Extract FBOSS Binaries

```bash
# If .zst file exists and /opt/fboss doesn't exist
if [[ -f "$HOME_DIR/$FBOSS_TAR_ZST" && ! -d "$DEST_DIR" ]]; then
    mkdir -p /opt/fboss
    zstd -d fboss_bins_bcm_JC_20251030.tar.zst  # Decompress zst
    tar xvf fboss_bins_bcm_JC_20251030.tar -C /opt/fboss  # Extract tar
    tar xvf dbglib.tar.gz -C /opt/fboss/lib/  # Extract debug library
fi
```

This unpacks the FBOSS test binaries and libraries to `/opt/fboss/`.

### Phase 3: Execute All Test Items

Tests are executed sequentially in the following order:

#### 1. SAI T0 Test
```bash
./SAI_TX_test.sh fboss_bins_bcm_JC_20251030.tar.zst t0
```
- Loads kernel modules (linux_ngbde, linux_ngknet)
- Executes SAI layer tests: `run_test.py sai --filter_file=t0_sai_tests.conf`
- Generates log file `t0_sai_test_*.log` and archives as `.tar.gz`

#### 2. SAI T1 Test
```bash
./SAI_TX_test.sh fboss_bins_bcm_JC_20251030.tar.zst t1
```
- Similar to T0 but uses T1 test configuration

#### 3. Agent HW T0 Test
```bash
./Agent_HW_TX_test.sh fboss_bins_bcm_JC_20251030.tar.zst t0
```
- Executes Agent hardware tests: `run_test.py hw --filter_file=t0_agent_hw_tests.conf`

#### 4. Agent HW T1 Test
```bash
./Agent_HW_TX_test.sh fboss_bins_bcm_JC_20251030.tar.zst t1
```

#### 5. Link Test
```bash
./Link_T0_test.sh fboss_bins_bcm_JC_20251030.tar.zst copper
```
- Uses specified topology type (copper in this example)
- Test categories include:
  - warm_boot tests
  - cold_boot tests
  - bcm_link tests
- Generates log file `linktest_*.log.tar.gz`

#### 6. ExitEVT Test
```bash
./ExitEVT.sh fboss_bins_bcm_JC_20251030.tar.zst copper
```
- Executes EVT (Engineering Validation Test) suite
- Generates log file `exitevt_*.log.tar.gz`

### Phase 4: Organize Test Reports

```bash
# Create date-specific directory
DATE_DIR="all_test_$(date +%Y-%m-%d)"
TARGET_DIR="/home/NUI/test_report/MINIPACK3BA/$DATE_DIR"
mkdir -p "$TARGET_DIR"

# Move all .tar.gz log files to target directory
find /opt/fboss -name "*.tar.gz" -exec mv {} "$TARGET_DIR/" \;
```

All test log archives are organized into a date-specific directory structure.

### Phase 5: Generate Dashboard Cache

```bash
# Call Python script to generate cache
python3 generate_cache.py "MINIPACK3BA" "2026-01-17"
```

The `generate_cache.py` script:
- Parses all test log archives
- Counts PASS/FAIL statistics for each test category
- Generates JSON cache files for dashboard visualization
- Cache is stored in `/home/NUI/test_report/[PLATFORM]/[DATE]/.cache/`

---

## 4. Dashboard Result Display

After tests complete, users can:

1. **Switch to Dashboard Tab**
   - Select platform (e.g., MINIPACK3BA)
   - Select test date (e.g., 2026-01-17)

2. **View Test Statistics**
   - SAI T0/T1 test results with pass/fail counts
   - Agent HW T0/T1 test results
   - Link Test results by category (warm_boot, cold_boot, bcm_link)
   - ExitEVT test results
   - Interactive charts showing test distribution

3. **View Individual Test Logs**
   - Click "LOG DETAIL" button for any test
   - View full log content in browser (searchable with Ctrl+F)
   - Download log as TXT file
   - See test status (PASS/FAIL) with color coding

---

## Complete Flow Diagram

```
User Operations
    ↓
[Select run_all_test.sh + Topology + Bin File]
    ↓
[Click Start Test]
    ↓
Backend API (/api/test/start)
    ├─ Step 1: Apply Topology Configuration
    │   ├─ Execute reconvert.py
    │   └─ Generate /home/NUI/[platform].materialized_JSON.tmp
    ├─ Step 2: Terminate Old Processes
    ├─ Step 3: Clean /opt/fboss (if new bin uploaded)
    └─ Step 4: Start Test Script
        ↓
run_all_test.sh Execution
    ├─ Detect Platform
    ├─ Extract FBOSS Binaries to /opt/fboss
    ├─ SAI T0/T1 Tests (reads config from .tmp file)
    ├─ Agent HW T0/T1 Tests
    ├─ Link Test (using selected topology)
    ├─ ExitEVT Test
    ├─ Organize Reports → /home/NUI/test_report/[PLATFORM]/all_test_[DATE]/
    └─ Generate Dashboard Cache
        ↓
Tests Complete
    ↓
[Dashboard Displays Test Results]
```

---

## Execution Time

The complete test suite typically takes **several hours** to complete, depending on:
- Number of test cases in each category
- Hardware performance
- Network topology complexity
- Platform-specific test requirements

---

## Test Report Structure

All test logs are saved in the following structure:

```
/home/NUI/test_report/
├── MINIPACK3BA/
│   └── all_test_2026-01-17/
│       ├── t0_sai_test_*.log.tar.gz
│       ├── t1_sai_test_*.log.tar.gz
│       ├── t0_agent_hw_test_*.log.tar.gz
│       ├── t1_agent_hw_test_*.log.tar.gz
│       ├── linktest_*.log.tar.gz
│       ├── exitevt_*.log.tar.gz
│       └── .cache/
│           └── dashboard_cache.json
├── MINIPACK3N/
│   └── all_test_2026-01-17/
│       └── ...
└── WEDGE800BACT/
    └── all_test_2026-01-17/
        └── ...
```

Each `.tar.gz` archive contains:
- Test execution logs with timestamps
- Test case names and results (PASS/FAIL)
- Error messages and stack traces (if failures occur)
- Test markers for parsing: `"########## Running test:"` and `"Running all tests took"`

---

## Key Configuration Files

### Platform Configuration
- **File**: `test_script/platform_config.sh`
- **Purpose**: Defines platform-specific settings
- **Variables**:
  - `DETECTED_PLATFORM`: Auto-detected platform name
  - `AGENT_CONFIG`: Path to switch config (.tmp file)
  - `FRU_CONFIG`: Platform FRU configuration
  - `PLAT_MAP_CONFIG`: Platform mapping configuration

### Topology Configuration
- **Location**: `link_test_configs/[PLATFORM]/`
- **Examples**:
  - `copper_link.json` - DAC cable configuration
  - `optics_link_one.json` - Optical transceiver config 1
  - `optics_link_two.json` - Optical transceiver config 2
- **Usage**: Selected by user, applied via reconvert.py

### Test Filter Configuration
- **Location**: `/opt/fboss/share/hw_sanity_tests/`
- **Files**:
  - `t0_sai_tests.conf` - SAI T0 test filter
  - `t1_sai_tests.conf` - SAI T1 test filter
  - `t0_agent_hw_tests.conf` - Agent HW T0 test filter
  - `t1_agent_hw_tests.conf` - Agent HW T1 test filter

---

## Important Notes

1. **Switch Configuration Path**
   - Actual location: `/home/NUI/[platform].materialized_JSON.tmp`
   - Test scripts reference this via `$AGENT_CONFIG` environment variable

2. **Test Execution Order**
   - Tests run sequentially, not in parallel
   - Each test must complete before the next begins
   - Failure in one test does not stop subsequent tests

3. **Platform Detection**
   - Platform is auto-detected from hardware FRU data
   - Detection result is cached to `.platform_cache` file
   - Dashboard uses cached platform for report organization

4. **Log Archive Structure**
   - Test logs are nested in double-compressed archives
   - Outer archive: `test_name.log.tar.gz`
   - Inner structure: Contains individual `.log` files
   - Dashboard automatically handles nested extraction

5. **Test Status Detection**
   - Uses gtest result markers: `[  PASSED  ]` and `[  FAILED  ]`
   - Dashboard parses these markers to determine test outcomes
   - Generic "ERROR" strings in logs do not indicate test failure

6. **Test Procedure Management**
   - Test configurations can be saved with custom names
   - Saved procedures are stored in `/home/NUI/test_procedures/` directory
   - Each procedure is a JSON file containing all test parameters
   - Procedures can be loaded to quickly repeat the same test setup

---

## Test Procedure Save/Load Feature

### Saving a Test Procedure

1. **Configure test parameters** as needed (script, bin, topology, etc.)
2. **Enter a procedure name** in the "Save Current Test Procedure" section
3. **Click "💾 Save Procedure"** button
4. The configuration is saved to `/home/NUI/test_procedures/[name].json`

**Saved Configuration Includes:**
- Test script name
- Bin file name
- Test level (if applicable)
- Topology type
- Topology file
- Clean /opt/fboss option

**Example saved procedure file** (`test_procedures/copper_test_t0.json`):
```json
{
  "script": "run_all_test.sh",
  "bin": "fboss_bins_bcm_JC_20251030.tar.zst",
  "test_level": "",
  "topology": "copper",
  "topology_file": "copper_link.json",
  "clean_fboss": true
}
```

### Loading a Saved Procedure

1. **Select procedure** from the "Load Saved Test Procedure" dropdown
2. **All parameters are automatically populated**
3. **Modify if needed** before starting the test
4. **Click "▶️ Start Test"** to execute

### API Endpoints

**GET `/api/test/procedures`**
- Returns list of all saved test procedures
- Response: `{ "procedures": ["copper_test_t0", "optics_test_t1", ...] }`

**GET `/api/test/procedures/<procedure_name>`**
- Returns configuration for a specific procedure
- Response: `{ "success": true, "name": "...", "config": {...} }`

**POST `/api/test/procedures`**
- Saves a new test procedure
- Request body: `{ "name": "procedure_name", "config": {...} }`
- Response: `{ "success": true, "message": "...", "filename": "..." }`

**DELETE `/api/test/procedures/<procedure_name>`**
- Deletes a saved procedure
- Response: `{ "success": true, "message": "..." }`

---

## Related Documentation

- **TOPOLOGY_UPDATE.md**: Topology configuration and management
- **WORKFLOW.md**: General system workflow
- **SPEC.md**: API specifications
- **RELEASE_SCRIPTS.md**: Release and version management

---

## Troubleshooting

### Test Fails to Start
- Check if `/home/[bin_file].zst` exists
- Verify platform detection in `.platform_cache`
- Ensure no other tests are running (check processes)
- Try enabling "Clean /opt/fboss" option to force clean state

### Configuration Not Applied
- Verify topology file exists in `link_test_configs/[PLATFORM]/`
- Check reconvert.py execution logs
- Confirm `.tmp` file was generated in `/home/NUI/`

### Dashboard Shows No Results
- Check if test reports exist in `test_report/[PLATFORM]/all_test_[DATE]/`
- Verify dashboard cache was generated (`.cache/dashboard_cache.json`)
- Ensure platform and date selections match test execution

### Log Detail Feature Not Working
- Confirm test log archives are in correct directory
- Check archive file structure (should be `.tar.gz`)
- Verify test name matches between dashboard and log file

### Saved Procedure Not Loading
- Check if procedure file exists in `/home/NUI/test_procedures/`
- Verify JSON file format is valid
- Ensure all referenced bin files and topology files still exist
- Click "🔄 Refresh" button to update procedure list

### Binary Extraction Issues
- Enable "Clean /opt/fboss" checkbox to force re-extraction
- Verify .zst file is not corrupted
- Check disk space in `/opt` partition
- Review test script logs for extraction errors

---

*Document Version: 1.1*  
*Last Updated: January 17, 2026*  
*Author: NUI Testing Framework*
