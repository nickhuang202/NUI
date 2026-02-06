# NUI REST API Examples

This document provides `curl` command examples for interacting with the NUI REST API.

**Note:** Replace `172.17.9.199` with your DUT IP address (e.g., `172.17.9.199`) if running remotely.

## 1. Test Execution Workflow (Standard Procedure)

To start a test correctly, you must follow this 2-step procedure:

### Step 1: Apply Topology
Configures the switch with the specified topology file. This generates the necessary configuration files for the test service.

```bash
curl -X POST http://172.17.9.199:5000/api/apply_topology \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "MINIPACK3BA",
    "config_filename": "Env_Test.materialized_JSON"
  }'
```
*   `platform`: Target platform (e.g., `MINIPACK3BA`, `MINIPACK3N`, `WEDGE800BACT`).
*   `config_filename`: The name of the topology file in `Topology/{PLATFORM}/` or `link_test_configs/{PLATFORM}/`.

### Step 2: Start Test
Starts the main test script.

```bash
curl -X POST http://172.17.9.199:5000/api/test/start \
  -H "Content-Type: application/json" \
  -d '{
    "script": "run_all_test.sh",
    "bin": "fboss_bins_bcm_xgs_...tar.zst",
    "clean_fboss": false,
    "topology": "default",
    "topology_file": "Env_Test.materialized_JSON",
    "test_items": {
        "sai_t0": true,
        "evt_exit": true,
        "link_test": true
    }
  }'
```
*   `script`: The test script to run (e.g., `run_all_test.sh`).
*   `bin`: The FBOSS binary file name (must exist on the server).
*   `test_items`: (Optional) Specific tests to run. If omitted, runs default set.

---

## 2. Test Management

### Check Test Status
Returns the status of the currently running or last executed test.

```bash
curl -X GET http://172.17.9.199:5000/api/test/status
```

### Stop Running Test
Terminates the currently running test and kills associated processes.

```bash
curl -X POST http://172.17.9.199:5000/api/test/kill-processes
```

### List Available Bin Files
Lists all available binary files in the test directory.

```bash
curl -X GET http://172.17.9.199:5000/api/test/bins
```

### Upload Bin File
Uploads a custom `.zst` binary file to the server.

```bash
curl -X POST http://172.17.9.199:5000/api/test/upload-bin \
  -F "file=@/path/to/your/file.tar.zst"
```
*   `file`: The local path to the `.zst` file to upload.
*   **Note:** Upload progress is tracked by the client. `curl` displays a progress meter by default.

### Extract Bin File to /opt/fboss
Extracts a `.zst` archive from `/home` into `/opt/fboss`.

```bash
curl -X POST http://172.17.9.199:5000/api/test/extract-bin \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "fboss_bins.tar.zst",
    "clean_fboss": true 
  }'
```
*   `filename`: The `.zst` filename that already exists in `/home`.
*   `clean_fboss`: If `true`, clears `/opt/fboss` before extracting.

---

## 3. Topology Management

### List Topology Files
Lists available topology files for a specific platform.

```bash
curl -X GET http://172.17.9.199:5000/api/topology_files/MINIPACK3BA
```

### Save Topology
Saves a new topology configuration (connection map) to the server.

```bash
curl -X POST http://172.17.9.199:5000/api/save_topology \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "MINIPACK3BA",
    "filename": "My_Custom_Topology.materialized_JSON",
    "connections": [
        {
            "port1": "eth1/1/1",
            "port2": "eth1/2/1",
            "profile1": 39,
            "profile2": 39
        }
    ]
  }'
```

### Get Topology Content
Retrieves the parsed content of a specific topology file.

```bash
curl -X GET "http://172.17.9.199:5000/api/topology/MINIPACK3BA?file=Env_Test.materialized_JSON"
```

---

## 4. Dashboard & Reports

### Get Available Test Dates
Returns a list of dates for which test reports exist for a given platform.

```bash
curl -X GET http://172.17.9.199:5000/api/dashboard/dates/MINIPACK3BA
```
[root@172.17.9.199 ~]# curl -X GET http://172.17.9.199:5000/api/dashboard/dates/MINIPACK3BA
[
  "2026-02-05",
  "2026-02-04",
  "2026-02-03",
  "2026-02-02",
  "2026-01-30",
  "2026-01-29",
  "2026-01-28"
]

### Get Test Summary
Returns a summary of test results (pass/fail counts, duration) for a specific date.

```bash
curl -X GET http://172.17.9.199:5000/api/dashboard/summary/MINIPACK3BA/2026-02-04
```

### Get Trend Data
Returns trend data (pass/fail history) for the last 7 days.

```bash
curl -X GET http://172.17.9.199:5000/api/dashboard/trend/MINIPACK3BA
```

### Download Test Log
Downloads the log file for a specific test category and level.

```bash
curl -X GET http://172.17.9.199:5000/api/dashboard/download_log/MINIPACK3BA/2026-02-04/sai/t0 \
  --output sai_t0.log
```
*   `category`: Test category (e.g., `sai`, `link`, `agent_hw`).
*   `level`: Test level (e.g., `t0`, `t1`, `ev_default`).

---

## 5. System Health & Ports

### Check System Health
Returns comprehensive system health status including CPU, memory, and service status.

```bash
curl -X GET http://172.17.9.199:5000/api/v1/health
```

### Get Port Status
Returns the link status (up/down) of all ports.

```bash
curl -X GET http://172.17.9.199:5000/api/port_status
```

### Get Transceiver Info
Returns detailed information about inserted transceivers (temperature, power levels, serial numbers).

```bash
curl -X GET http://172.17.9.199:5000/api/transceiver_info
```

---

## 6. Test Procedures & Scripts

### List Test Scripts
Returns a list of available shell scripts for testing.

```bash
curl -X GET http://172.17.9.199:5000/api/test/scripts
```
[root@172.17.9.199 ~]# curl -X GET http://172.17.9.199:5000/api/test/scripts
{
  "scripts": [
    "Agent_HW_TX_test.sh",
    "ExitEVT.sh",
    "Link_T0_test.sh",
    "Link_T1_test.sh",
    "Prbs_test.sh",
    "SAI_TX_test.sh",
    "dummy_test.sh",
    "platform_config.sh",
    "run_all_test.sh"
  ]
}

### List Saved Procedures
Returns a list of saved test procedures (JSON configurations).

```bash
curl -X GET http://172.17.9.199:5000/api/test/procedures
```
[root@172.17.9.199 ~]# curl -X GET http://172.17.9.199:5000/api/test/procedures
{
  "procedures": [
    "Env_Test",
    "default",
    "optic_two",
    "test-t0",
    "test_t1"
  ]
}

### Save Test Procedure
Saves a new test procedure configuration.

```bash
curl -X POST http://172.17.9.199:5000/api/test/procedures \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My_Custom_Test",
    "script": "run_all_test.sh",
    "bin": "fboss_bins.tar.zst",
    "topology": "default",
    "test_items": {
        "sai_t0": true
    }
  }'
```

---

## 7. Lab Monitor

### Get Lab Configuration
Retrieves the full hierarchy of Labs, Platforms, and DUTs.

```bash
curl -X GET http://172.17.9.199:5000/api/lab_monitor/config
```

**Example Output:**

```json
{
  "labs": [
    {
      "id": "lab_20260121124137953279",
      "name": "Taichung_Lab",
      "description": "Taichung Lab",
      "platforms": [
        {
          "id": "platform_20260121124442016492",
          "name": "MINIPACK3BA",
          "description": "MINIPACK3BA TH5 BCM solusion",
          "duts": [
            {
              "id": "dut_20260121124905078197",
              "name": "AP29047232",
              "ip_address": "172.17.9.199",
              "config_type": "Config A",
              "description": "3BA",
              "created_at": "2026-01-21T12:49:05.078220",
              "updated_at": "2026-01-21T15:05:54.084675",
              "password": "root"
            }
          ]
        }
      ]
    }
  ],
  "version": "1.0"
}
```

### Lab Group Management

#### Add Lab
Creates a new lab group.

```bash
curl -X POST http://172.17.9.199:5000/api/lab_monitor/lab \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Validation Lab",
    "description": "Main validation lab"
  }'
```

#### Delete Lab
Deletes a lab group.

```bash
curl -X DELETE http://172.17.9.199:5000/api/lab_monitor/lab/lab_20260121124137953279
```

### Platform Management

#### Add Platform
Adds a new platform to a specific lab.

```bash
curl -X POST http://172.17.9.199:5000/api/lab_monitor/platform \
  -H "Content-Type: application/json" \
  -d '{
    "lab_id": "lab_20260121124137953279",
    "name": "MINIPACK3BA",
    "description": "Rack 1"
  }'
```

### DUT Management

#### Add DUT
Adds a new DUT to a platform.

```bash
curl -X POST http://172.17.9.199:5000/api/lab_monitor/dut \
  -H "Content-Type: application/json" \
  -d '{
    "lab_id": "lab_20260121124137953279",
    "platform_id": "platform_20260121124442016492",
    "name": "AP29047232",
    "ip_address": "172.17.9.199",
    "config_type": "Config A",
    "description": "3BA",
    "password": "root"
  }'
```

### Status & Testing

#### Get Lab Status
Returns the status of all DUTs (Device Under Test) in the lab.

```bash
curl -X GET http://172.17.9.199:5000/api/lab_monitor/status
```

**Example Output:**

```json
{
  "dut_20260121124905078197": {
    "status": "online",
    "last_seen": "2026-02-05T10:15:23.123456",
    "version": "Switch_SDK_v4.8",
    "has_new_reports": false
  }
}
```

#### Check if DUT is Testing
Checks if a specific DUT is currently running tests.

```bash
curl -X GET http://172.17.9.199:5000/api/lab_monitor/dut/dut_20260121124905078197/testing
```

**Example Output:**

```json
{
  "success": true,
  "testing": false,
  "dut_id": "dut_20260121124905078197"
}
```

#### Get DUT Version
Retrieves the software version information for a DUT.

```bash
curl -X GET http://172.17.9.199:5000/api/lab_monitor/dut/dut_20260121124905078197/version
```

### Reports

#### Get Report Summary
Returns a summary of test results for a DUT on a specific date.

```bash
curl -X GET http://172.17.9.199:5000/api/lab_monitor/dut/dut_20260121124905078197/dashboard/summary/2026-02-05
```

**Example Output:**

```json
{
  "success": true,
  "summary": {
    "platform": "MINIPACK3BA",
    "date": "2026-02-05",
    "lab_name": "Taichung_Lab",
    "dut_name": "AP29047232",
    "version_info": {
      "FBOSS_BINARY": "fboss_bins_mp3ba.tar.zst",
      "FBOSS_COMMIT_ID": "a1b2c3d4e5",
      "SDK_VERSION": "Switch_SDK_v4.8",
      "SAI_BUILD": "SAI_1.0"
    },
    "test_times": {
      "start": "2026-02-05 10:00:00",
      "end": "2026-02-05 12:30:00",
      "duration": "2h 30m"
    },
    "all_tests": {
      "passed": 45,
      "failed": 2,
      "total": 47
    },
    "tests": {
      "sai": {
        "t0": {
          "passed": 20,
          "failed": 0,
          "total": 20,
          "duration": "45m"
        }
      },
      "link": {
        "t0": {
          "passed": 25,
          "failed": 2,
          "total": 27,
          "duration": "1h 45m",
          "topology": "optics_one"
        }
      }
    }
  }
}
```

#### Client-Side CSV Generation
The "Download CSV" feature in the UI is generated client-side from the test summary. You can simulate this using `jq` to parse the JSON summary.

```bash
# Get summary and parse to CSV format (Test Name, Result, Note)
curl -s -X GET http://172.17.9.199:5000/api/lab_monitor/dut/dut_20260121124905078197/dashboard/summary/2026-02-05 \
| jq -r '.summary.tests.sai.t0.items[] | [.name, .result, .note] | @csv'
```

#### Download Log/Report
Downloads a specific log file or report.

```bash
# Download SAI T0 log
curl -X GET http://172.17.9.199:5000/api/lab_monitor/download_log/Taichung_Lab/MINIPACK3BA/AP29047232/2026-02-05/sai/t0 \
  --output sai_t0.log.tar.gz

# Download ALL logs for a date
curl -X GET http://172.17.9.199:5000/api/lab_monitor/download_log/Taichung_Lab/MINIPACK3BA/AP29047232/2026-02-05/all/all \
  --output all_logs.tar.gz
```


