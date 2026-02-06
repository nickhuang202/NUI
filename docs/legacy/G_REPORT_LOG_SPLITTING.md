# G Report - Log Splitting Feature

## Overview

G Report (Organized Report) now includes automatic splitting of `.log.tar.gz` archives into individual test log files.

When downloading G Report, the system automatically extracts and splits log archives, creating separate `.log` files for each test item within the Logs directory.

---

## Feature Description

### Original Functionality
G Report organizes test reports into a structured directory hierarchy:
```
T0/T1/T2/
├── YYYYMMDD/
│   ├── SAI_Test/
│   │   ├── Configs/
│   │   └── Logs/           # Contains .log.tar.gz files
│   ├── Agent_HW_test/
│   └── Link_Test/
```

### New Feature
The `.log.tar.gz` files in the `Logs/` directory are now automatically split into individual test log files:

```
Logs/
├── SAI_T0_WEDGE800BACT_xxxxx_2026-01-28-AM10-50.log.tar.gz  # Original archive
├── AgentAclAndDscpQueueMappingTest.VerifyAclAndQosMap.log   # ✨ New: Individual test logs
├── AgentAclCounterTest.VerifyAclPrioritySportHitFrontPanel.log
├── AgentAclCounterTest.VerifyCounterBumpOnSportHitCpu.log
├── AgentAclPriorityTest.AclNameChange.log
└── ... (other test log files)
```

---

## Technical Implementation

### 1. Log Splitting Logic

**File Location:** `/home/NUI/organize_test_reports.py`

**New Function:** `split_log_tar_file(log_tar_path, output_log_dir)`

#### Execution Steps:
1. **Extract .log.tar.gz**
   - Extract `.log.tar.gz` to temporary directory `/tmp/log_extract`
   - Find internal `.log` file

2. **Identify Test Markers**
   ```python
   START_MARKER = "########## Running test:"
   END_MARKER = "Running all tests took"
   ```

3. **Split Log File**
   - Read main log file line by line
   - Create new test log file when `START_MARKER` is encountered
   - Write test content to corresponding log file
   - Stop processing when `END_MARKER` is encountered

4. **Filename Processing**
   - Extract test name from marker (e.g., `AgentAclPriorityTest.CheckAclPriorityOrder`)
   - Replace path separators `/` and `\` with `_` to avoid filesystem issues
   - Generate filename: `{test_name}.log`

5. **Cleanup**
   - Remove temporary directory
   - Keep original `.log.tar.gz` file

---

### 2. Integration Flow

**Trigger:** When user clicks the "G report" button on Dashboard

#### Execution Flow:
```
User clicks "G report" button
    ↓
API: /api/dashboard/download_organized/<platform>/<date>
    ↓
Python script: organize_test_reports.py
    ↓
1. Extract archive files
2. Organize into directory structure
3. Copy log files to Logs/ directory
4. 🆕 Detect .log.tar.gz files
5. 🆕 Call split_log_tar_file() for each .log.tar.gz
6. 🆕 Extract individual test logs to Logs/ directory
    ↓
Return organized .tar.gz for download
```

---

### 3. Code Changes

#### Change Location 1: Track log tar files
**File:** `organize_test_reports.py` (Line ~274)

```python
files_copied = {'version': 0, 'config': 0, 'log': 0, 'qsfp': 0, 'csv': 0, 'xlsx': 0}
log_tar_files = []  # 🆕 Track .log.tar.gz files for splitting

# ... file extraction loop ...

elif file_cat == 'log':
    target = os.path.join(log_dir, filename)
    tar.extract(member, path='/tmp')
    shutil.copy2(os.path.join('/tmp', member.name), target)
    files_copied['log'] += 1
    
    # 🆕 Track .log.tar.gz files for splitting
    if filename.endswith('.log.tar.gz'):
        log_tar_files.append(target)
```

#### Change Location 2: Execute log splitting
**File:** `organize_test_reports.py` (Line ~310)

```python
# 🆕 Split log tar files into individual test logs
if log_tar_files:
    print(f"   🔧 Splitting {len(log_tar_files)} log file(s) into individual test logs...")
    total_split_logs = 0
    for log_tar in log_tar_files:
        split_count = split_log_tar_file(log_tar, log_dir)
        if split_count > 0:
            total_split_logs += split_count
            print(f"      ✓ {os.path.basename(log_tar)}: {split_count} test logs extracted")
    
    if total_split_logs > 0:
        print(f"   ✅ Total {total_split_logs} individual test log files created")
```

---

## Usage Example

### Scenario: Download MINIPACK3BA test report for 2026-01-28

1. **Open Dashboard**
   ```
   http://<DUT_IP>:5000/dashboard/MINIPACK3BA/2026-01-28
   ```

2. **Click "G report" button**

3. **System Processing (Console Output):**
   ```
   📦 Processing: SAI_T0_MINIPACK3BA_xxxxx_2026-01-28-AM10-50.tar.gz
      Category: SAI_Test, Level: T0, Topology: None
      ✅ Copied: 1 version, 5 configs, 2 logs, 1 csv, 1 xlsx, 2 qsfp configs
      🔧 Splitting 1 log file(s) into individual test logs...
         ✓ SAI_T0_MINIPACK3BA_xxxxx_2026-01-28-AM10-50.log.tar.gz: 245 test logs extracted
      ✅ Total 245 individual test log files created
   ```

4. **Downloaded File Structure:**
   ```
   organized_MINIPACK3BA_20260128.tar.gz
   └── T0/
       └── 20260128/
           └── SAI_Test/
               ├── Configs/
               │   ├── fruid.json
               │   ├── platform_mapping.json
               │   └── qsfp_test_configs/
               └── Logs/
                   ├── SAI_T0_MINIPACK3BA_xxxxx.log.tar.gz  ← Original
                   ├── AgentAclAndDscpQueueMappingTest.VerifyAclAndQosMap.log  ← 🆕 New
                   ├── AgentAclConflictAndDscpQueueMappingTest.VerifyAclAndQosMapConflict.log
                   ├── AgentAclCounterTest.VerifyAclPrioritySportHitFrontPanel.log
                   └── ... (243 more test logs)
   ```

---

## Related Files

| File | Description |
|------|-------------|
| `/home/NUI/organize_test_reports.py` | Main logic: Organize reports + split logs |
| `/home/NUI/split_and_report.py` | Standalone tool: Split logs + generate Excel report |
| `/home/NUI/app.py` | API endpoint: `/api/dashboard/download_organized` |
| `/home/NUI/templates/dashboard.html` | Frontend: G report button |

---

## Error Handling

### Common Issues:

1. **Log file not found**
   ```
   ⚠️  No .log file found inside XXX.log.tar.gz
   ```
   - Possible cause: Tar file internal structure does not match expectations
   - Handling: Skip the file and continue processing other files

2. **Extraction failed**
   ```
   ❌ Error splitting log: [error message]
   ```
   - Possible cause: File corrupted or permission issues
   - Handling: Report error and clean up temporary files

3. **No START_MARKER found**
   - Handling: No split log files will be generated (file_count = 0)
   - Keep original .log.tar.gz file

---

## Benefits

1. **Quick Search** ✅
   - View all test items without extracting archives
   - Directly open individual test log files

2. **Time Saving** ⏱️
   - Automated splitting, no manual processing required
   - Integrated into G report download workflow

3. **Preserve Original Files** 📦
   - Keep both `.log.tar.gz` and split files
   - Ensure data integrity

4. **Compatibility** 🔄
   - Does not affect existing functionality
   - Can choose to use original tar file or individual log files

---

## Future Improvements

1. **Excel Report Integration**
   - Consider integrating Excel report functionality from `split_and_report.py`
   - Automatically generate test result summary

2. **Optional Splitting**
   - Provide option for users to choose whether to split logs
   - Save processing time (if individual logs not needed)

3. **Progress Display**
   - Display splitting progress on frontend
   - Avoid confusion about long wait times

---

## Version History

| Version | Date | Updates |
|---------|------|----------|
| v1.0 | 2026-01-28 | 🎉 Added log splitting feature |

