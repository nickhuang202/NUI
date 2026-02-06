# ExitEVT.sh Test Report Generation

## Overview
After running ExitEVT.sh tests, an Excel report is automatically generated using the hwtest_results CSV file.

## Usage

### ExitEVT.sh
```bash
./ExitEVT.sh <zst_version> <topology_name> [test_cases]
```

**Parameters:**
- `zst_version`: FBOSS binary version (e.g., `fboss_bins_bcm_20250930_18_03_21_aa63c704c0.tar.zst`)
- `topology_name`: Topology configuration name (see below)
- `test_cases`: (Optional) Specific test cases to run

**Topology Names:**
- `copper` - DAC configuration (Column 3)
- `optics_one` - Optics Config 1 (Column 1)
- `optics_two` - Optics Config 2 (Column 2)
- `aec` - AEC Config 1 (Column 4)
- `default` or `800g` - 800G default config (Column 5)
- `400g` - 400G config (Column 6)

### Platform-Specific Run Scripts

#### MINIPACK3BA
```bash
./run_mp3ba_test.sh <fboss_zst_file> <topology_name> [test_case]

# Examples:
./run_mp3ba_test.sh fboss_bins_bcm_20250930.tar.zst default
./run_mp3ba_test.sh fboss_bins_bcm_20250930.tar.zst optics_one
```

#### WEDGE800BACT
```bash
./run_w800bact_test.sh <config_tar> <fboss_zst_file> <topology_name> [test_case]

# Examples:
./run_w800bact_test.sh w800bact_conf_800G.tar.gz fboss_bins_bcm_JC_20251030.tar.zst copper
./run_w800bact_test.sh w800bact_conf_400G.tar.gz fboss_bins_bcm_JC_20251030.tar.zst optics_one
```

## Output Files

### Excel Report
- **Location:** `/opt/fboss/{platform}_Testing_EVT_Exit_Link.xlsx`
- **Format:** Multi-sheet workbook with one sheet per test run
- **Sheet Name:** Extracted from zst filename (commit ID timestamp)
- **Content:** Test results (PASS/FAIL) filled in appropriate column based on topology

### Archive
- **Location:** `/opt/fboss/ExitEVT_{platform}_{version}_{date}.tar.gz`
- **Contents:**
  - All CSV files (including hwtest_results_*.csv)
  - Excel report (.xlsx)
  - fboss2_show_port.txt
  - fboss2_show_transceivers.txt
  - Version_Info.txt
  - Log files (*.log.tar.gz)
  - demsg.log

## Templates

Template files are required for each platform:
- `MINIPACK3BA_EVT_Testing_EVT_Exit_Link.xlsx`
- `MINIPACK3N_EVT_Testing_EVT_Exit_Link.xlsx`
- `WEDGE800BACT_EVT_Testing_EVT_Exit_Link.xlsx`
- `WEDGE800CACT_EVT_Testing_EVT_Exit_Link.xlsx`

If a platform-specific template is not found, it falls back to WEDGE800BACT template.

## Process Flow

1. Run ExitEVT.sh with topology name
2. Tests execute and generate hwtest_results_*.csv
3. Script automatically detects platform from FRUID
4. Script calls fill_result_v1.py with:
   - hwtest CSV file
   - Platform-specific template
   - Column index based on topology name
   - Sheet name from zst filename
5. Excel report is generated/updated
6. All results archived in tar.gz

## Example Complete Workflow

```bash
# For MINIPACK3BA with copper topology
cd /home/NUI/test_script
./run_mp3ba_test.sh fboss_bins_bcm_20250930_18_03_21_aa63c704c0.tar.zst copper

# Results will be in:
# /opt/fboss/MINIPACK3BA_Testing_EVT_Exit_Link.xlsx (Excel report)
# /opt/fboss/ExitEVT_MINIPACK3BA_fboss_bins_bcm_20250930_18_03_21_aa63c704c0.tar.zst_2025-12-30-PM03-45.tar.gz (Archive)
```

## Notes

- Platform is auto-detected from `/var/facebook/fboss/fruid.json`
- If output Excel file exists, a new sheet is added/updated
- Test names are normalized (boot prefixes removed)
- Results are normalized to PASS/FAIL
- If hwtest CSV is not found, Excel generation is skipped with a warning
