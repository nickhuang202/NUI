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

## 3. Schedule Test (Daily Profile) APIs

These APIs manage daily schedule profiles and execute scheduled tests.

### Get Schedule System Info
Returns hostname, platform, CPU, and memory usage for schedule UI.

```bash
curl -X GET http://172.17.9.199:5000/api/schedule/sysinfo
```

### Get Schedule Execution Status
Returns current schedule runner status (running profile, current test title, PID).

```bash
curl -X GET http://172.17.9.199:5000/api/schedule/execution-status
```

### List Saved Schedule Profiles

```bash
curl -X GET http://172.17.9.199:5000/api/schedule/profiles
```

### Get One Schedule Profile

```bash
curl -X GET "http://172.17.9.199:5000/api/schedule/profiles/SAI_T0_only"
```

### Save Schedule Profile
Creates or updates a profile and syncs it to crontab.

```bash
curl -X POST http://172.17.9.199:5000/api/schedule/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "profile_name": "SAI_T0_only",
    "cron_rule": {
      "type": "daily",
      "preview": "Every Day"
    },
    "tests": [
      {
        "title": "Nick_SAI_Test_T0_only",
        "type": "single",
        "startOffsetMinutes": 660,
        "durationMinutes": 30
      }
    ]
  }'
```

### Run Schedule Profile Now (Manual Trigger)
Starts `run_scheduled_profile.py` immediately for a saved profile.

```bash
curl -X POST "http://172.17.9.199:5000/api/schedule/profiles/SAI_T0_only/run"
```

### Stop Running Schedule Profile(s)
Stops active schedule runner processes. Optional `profile_name` filters which runner to stop.

```bash
curl -X POST http://172.17.9.199:5000/api/schedule/run/stop \
  -H "Content-Type: application/json" \
  -d '{
    "profile_name": "SAI_T0_only"
  }'
```

### Delete Schedule Profile

```bash
curl -X DELETE "http://172.17.9.199:5000/api/schedule/profiles/SAI_T0_only"
```

---

## 4. Topology Management

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

### Complete Topology Creation Examples

#### Example 1: Create Multi-Port Topology
This example creates a topology with multiple port connections using different profile IDs.

```bash
#!/bin/bash
# Multi-Port Topology API Script
# Creates a topology with multiple port connections

API_HOST="172.17.9.199:5000"
PLATFORM="WEDGE800BACT"
TOPOLOGY_NAME="multi_port_topology"

echo "Creating topology file with multiple connections..."
echo "Connections:"
echo "  - eth1/1/1 (profile 39) <--> eth1/2/1 (profile 39)"
echo "  - eth1/3/1 (profile 39) <--> eth1/4/1 (profile 39)"
echo "  - eth1/5/1 (profile 38) <--> eth1/6/1 (profile 38)"

# Step 1: Create the topology file
SAVE_RESPONSE=$(curl -s -X POST http://${API_HOST}/api/save_topology \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "'"${PLATFORM}"'",
    "filename": "'"${TOPOLOGY_NAME}"'",
    "connections": [
      {
        "port1": "eth1/1/1",
        "port2": "eth1/2/1",
        "profile1": 39,
        "profile2": 39
      },
      {
        "port1": "eth1/3/1",
        "port2": "eth1/4/1",
        "profile1": 39,
        "profile2": 39
      },
      {
        "port1": "eth1/5/1",
        "port2": "eth1/6/1",
        "profile1": 38,
        "profile2": 38
      }
    ]
  }')

echo "Save Response:"
echo "$SAVE_RESPONSE" | python3 -m json.tool

# Check if save was successful
if echo "$SAVE_RESPONSE" | grep -q '"success": true'; then
    echo "✓ Topology file created successfully!"
    
    # Step 2: Apply the topology
    echo "Applying topology..."
    
    APPLY_RESPONSE=$(curl -s -X POST http://${API_HOST}/api/apply_topology \
      -H "Content-Type: application/json" \
      -d '{
        "platform": "'"${PLATFORM}"'",
        "config_filename": "'"${TOPOLOGY_NAME}.materialized_JSON"'"
      }')
    
    echo "Apply Response:"
    echo "$APPLY_RESPONSE" | python3 -m json.tool
    
    if echo "$APPLY_RESPONSE" | grep -q '"success": true'; then
        echo "✓ Topology applied successfully!"
    else
        echo "✗ Failed to apply topology"
    fi
else
    echo "✗ Failed to create topology file"
fi
```

**Expected Output:**
```json
{
  "success": true,
  "file": "multi_port_topology.materialized_JSON",
  "path": "/home/NUI/Topology/WEDGE800BACT/multi_port_topology.materialized_JSON",
  "connections": 3
}
```

#### Example 2: Query Topology Information
This example demonstrates how to list and retrieve topology information.

```bash
#!/bin/bash
# Topology Query API Script
# Lists and retrieves topology information

API_HOST="172.17.9.199:5000"
PLATFORM="WEDGE800BACT"

echo "=========================================="
echo "Topology Query Script"
echo "=========================================="

# Step 1: List all available topology files
echo "Step 1: Listing available topology files for ${PLATFORM}..."
LIST_RESPONSE=$(curl -s http://${API_HOST}/api/topology_files/${PLATFORM})

echo "Available Topology Files:"
echo "$LIST_RESPONSE" | python3 -m json.tool

# Step 2: Get current topology configuration
echo ""
echo "Step 2: Getting current topology configuration..."
TOPOLOGY_RESPONSE=$(curl -s http://${API_HOST}/api/topology/${PLATFORM})

echo "Current Topology:"
echo "$TOPOLOGY_RESPONSE" | python3 -m json.tool

# Step 3: Get specific topology file (if provided as argument)
if [ -n "$1" ]; then
    echo ""
    echo "Step 3: Getting specific topology file: $1"
    
    SPECIFIC_RESPONSE=$(curl -s "http://${API_HOST}/api/topology/${PLATFORM}?file=$1")
    
    echo "Specific Topology Details:"
    echo "$SPECIFIC_RESPONSE" | python3 -m json.tool
fi

echo ""
echo "Usage: $0 [topology_filename]"
echo "Example: $0 custom_topology.materialized_JSON"
```

**Example Output (List Files):**
```json
{
  "platform": "WEDGE800BACT",
  "files": [
    "copper_jan30_wedge800bact.materialized_JSON",
    "jc_copper_2026_0206_wedge800bact.materialized_JSON",
    "multi_port_topology.materialized_JSON",
    "wedge800bact.materialized_JSON"
  ]
}
```

**Example Output (Get Topology):**
```json
{
  "platform": "WEDGE800BACT",
  "file": "multi_port_topology.materialized_JSON",
  "connections": [
    {
      "port1": "eth1/1/1",
      "port2": "eth1/2/1",
      "profile1": 39,
      "profile2": 39
    },
    {
      "port1": "eth1/3/1",
      "port2": "eth1/4/1",
      "profile1": 39,
      "profile2": 39
    }
  ],
  "profile_stats": {
    "39": 4,
    "38": 2
  }
}
```

#### Common Profile IDs
- **Profile 23**: 100G
- **Profile 25**: 200G
- **Profile 38**: 400G
- **Profile 39**: 800G
- **Profile 48**: 50G (service ports)
- **Profile 50**: 800G (alternative)

---

## 5. Dashboard & Reports

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

## 6. System Health & Ports

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

## 7. Test Procedures & Scripts

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

  ### Schedule Profiles (Daily/Weekly/Custom)

  #### Create or Update Schedule Profile
  Saves a scheduling profile, syncs crontab, and (for repeating rules) auto-starts today's runner.

  ```bash
  curl -X POST http://172.17.9.199:5000/api/schedule/profiles \
    -H "Content-Type: application/json" \
    -d '{
      "profile_name": "SAI_T0_TEST",
      "cron_rule": {
        "type": "daily",
        "preview": "Every Day (Daily)"
      },
      "tests": [
        {
          "title": "Env_Test",
          "type": "cron",
          "startOffsetMinutes": 630,
          "durationMinutes": 60
        }
      ]
    }'
  ```

  **Example Output:**
  ```json
  {
    "success": true,
    "message": "Profile \"SAI_T0_TEST\" saved successfully",
    "cron_synced": true,
    "today_runner_started": true,
    "today_runner_pid": 3264073,
    "today_runner_reason": "started"
  }
  ```

  #### List Schedule Profiles

  ```bash
  curl -X GET http://172.17.9.199:5000/api/schedule/profiles
  ```

  #### Get Single Schedule Profile

  ```bash
  curl -X GET http://172.17.9.199:5000/api/schedule/profiles/SAI_T0_TEST
  ```

  #### Adjust Existing Profile to Daily 05:00 (Reference)
  This is the same operation done via MCP client: update an existing profile to run every day at **05:00**.

  **Step 1: Read existing profile**
  ```bash
  curl -X GET "http://172.17.9.199:5000/api/schedule/profiles/Profile%202/28/2026"
  ```

  **Step 2: Save profile with custom cron `0 5 * * *`**
  ```bash
  curl -X POST http://172.17.9.199:5000/api/schedule/profiles \
    -H "Content-Type: application/json" \
    -d '{
      "profile_name": "Profile 2/28/2026",
      "cron_rule": {
        "type": "custom",
        "preview": "Cron: 0 5 * * *"
      },
      "tests": [
        {
          "title": "Nick_SAI_Test",
          "type": "event",
          "startOffsetMinutes": 870,
          "durationMinutes": 60
        }
      ]
    }'
  ```

  **Step 3: Verify updated profile**
  ```bash
  curl -X GET "http://172.17.9.199:5000/api/schedule/profiles/Profile%202/28/2026"
  ```

  #### Delete Schedule Profile

  ```bash
  curl -X DELETE http://172.17.9.199:5000/api/schedule/profiles/SAI_T0_TEST
  ```

  #### Get Current Schedule Execution Status
  Returns currently running scheduled profile and test block (used by Schedule UI Testing indicator).

  ```bash
  curl -X GET http://172.17.9.199:5000/api/schedule/execution-status
  ```

  **Example Output:**
  ```json
  {
    "success": true,
    "status": {
      "running": true,
      "profile_name": "SAI_T0_TEST",
      "current_test_title": "Env_Test",
      "pid": 3264073,
      "updated_at": "2026-02-28T10:30:00.000750"
    }
  }
  ```

  #### Get Schedule Page Sysinfo

  ```bash
  curl -X GET http://172.17.9.199:5000/api/schedule/sysinfo
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



## 8. MCP (Model Context Protocol) Server

The NUI platform includes an MCP server implementation (`mcp_server.py`) that uses the official `mcp` Python SDK to expose API operations as AI Agent Tools. This allows AI assistants like Claude, Cursor, or NUI's internal agents to query state and update schedule profiles.

### Setup and Prerequisites
The official `mcp` SDK requires Python 3.10+. If your system has an older Python version, it is highly recommended to use the [`uv`](https://docs.astral.sh/uv/) package manager, which will easily manage the environment and CLI execution for you:
```bash
# If uv is not installed: curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Registered MCP Tools
The `NUI_Stats` MCP Server currently exposes the following context-gathering tools:
1. `get_system_health()`: Maps to `GET /api/v1/health`
2. `get_test_status()`: Maps to `GET /api/test/status`
3. `get_port_status()`: Maps to `GET /api/port_status`
4. `get_transceiver_info()`: Maps to `GET /api/transceiver_info`
5. `get_schedule_profiles()`: Maps to `GET /api/schedule/profiles`
6. `get_schedule_profile(profile_name)`: Maps to `GET /api/schedule/profiles/{profile_name}`
7. `set_schedule_profile_daily_time(profile_name, hour, minute)`: Reads profile then saves with custom cron via `POST /api/schedule/profiles`

### Running the MCP Server
You can run the MCP server efficiently using `uvx` (which auto-manages the environment):
```bash
uvx --python 3.12 --from mcp[cli] --with fastmcp --with httpx mcp run mcp_server.py
```

### Example Usage (Client-side)
If you want to consume this MCP server programmatically from a Python client, use the `mcp.client` library to connect to it via `stdio` or `sse`:

```python
import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
import os

async def main():
    server_params = StdioServerParameters(
        command="uvx",
        args=["--python", "3.12", "--from", "mcp[cli]", "--with", "fastmcp", "--with", "httpx", "mcp", "run", "/home/NUI/mcp_server.py"],
        env=dict(os.environ)
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")
            
            # Call the get_system_health tool
            result = await session.call_tool("get_system_health", arguments={})
            print(f"System Health: {result.content}")

if __name__ == "__main__":
    asyncio.run(main())
```
