# Schedule Profile with Test Item Durations

## Overview
This document describes the feature that saves and displays test item durations in Saved Procedures and Schedule Profiles.

## Feature Description
When saving a Test Procedure, you can now configure the estimated duration for each test item (SAI T0, T1, T2; Agent HW T0, T1, T2; Link T0, T1; EVT Exit). These durations are:
1. Saved with the procedure configuration
2. Used when dragging procedures into the Schedule Timeline
3. Displayed as total time in both the modal preview and the schedule display

## How It Works

### Step 1: Configure Test Item Durations in NUI
1. Go to the **"Test Configuration"** section in NUI
2. Check which test items you want to run
3. Scroll to **"💾 Save Current Test Procedure"** section
4. A new panel appears: **"⏱️ Test Item Durations (minutes)"**
5. For each checked test item, set the estimated duration in minutes
  - SAI T0: 7 minutes (T1: 10m, T2: 15m)
  - Agent HW T0: 7 minutes (T1: 10m, T2: 15m)
  - Link T0: 5 minutes (T1: 10m)
   - EVT Exit: Default 5 minutes
6. Durations are saved to localStorage for future use
7. Click **"💾 Save Procedure"** to save the entire configuration

Example durations:
```
SAI T0: 7 mins
SAI T1: 10 mins
SAI T2: 15 mins
Agent HW T0: 7 mins
Agent HW T1: 10 mins
Agent HW T2: 15 mins
Link T0: 5 mins
Link T1: 10 mins
EVT Exit: 5 mins
```

### Step 2: Create Schedule Profile with Timeline
1. Open **Schedule App** (either standalone or from Lab Monitor)
2. In the **"Test Procedures"** panel on the left, you'll see your saved procedures
3. Each procedure now displays: `Procedure • XXX mins` (calculated from saved item durations)
4. Drag a procedure to the **Schedule Timeline**
5. The block will use the calculated duration from the procedure
6. Adjust position and size as needed:
   - Drag to change start time
   - Resize right edge to adjust duration
7. Click **"Edit Daily Profile..."** to open the modal

### Step 3: Save Schedule Profile
In the **"Profile Settings & Rule"** modal:
1. You'll see a summary list showing:
   - **Total Duration**: e.g., "2h 30m (from 00:00 to 02:30)"
   - Each test block with its scheduled time
2. Configure the recurrence rule (Daily, Weekly, Custom Cron)
3. Enter a profile name
4. Click **"Save Profile and Assign Rule"**

### Step 4: View Schedule Profile with Time Information
After saving, the profile display shows:
```
Profile: My_Test_Profile
Schedule active: [recurrence rule] on PLATFORM • ⏱️ Duration: 2h 30m
```

## Data Model

### Procedure Configuration
```json
{
  "platform": "MINIPACK3BA",
  "script": "run_all_test.sh",
  "bin": "fboss_bins_bcm_xgs_...tar.zst",
  "test_level": "default",
  "topology": "default",
  "topology_file": "Env_Test.materialized_JSON",
  "clean_fboss": false,
  "test_items": {
    "sai_test": true,
    "sai_t0": true,
    "sai_t1": true,
    "sai_t2": false,
    "agent_hw_test": true,
    "agent_t0": true,
    "agent_t1": true,
    "agent_t2": false,
    "link_test": true,
    "link_t0": true,
    "link_t1": false,
    "evt_exit": true
  },
  "test_item_durations": {
    "sai_t0": 7,
    "sai_t1": 10,
    "sai_t2": 15,
    "agent_t0": 7,
    "agent_t1": 10,
    "agent_t2": 15,
    "link_t0": 5,
    "link_t1": 10,
    "evt_exit": 5
  }
}
```

### Schedule Profile with Tests
```json
{
  "profile_name": "My_Test_Profile",
  "cron_rule": {
    "type": "daily",
    "preview": "Daily at 00:00"
  },
  "tests": [
    {
      "title": "Env_Test",
      "type": "cron",
      "startOffsetMinutes": 0,
      "durationMinutes": 60
    },
    {
      "title": "Nick_SAI_Test",
      "type": "event",
      "startOffsetMinutes": 60,
      "durationMinutes": 90
    },
    {
      "title": "Link_Test",
      "type": "single",
      "startOffsetMinutes": 150,
      "durationMinutes": 30
    }
  ]
}
```

## Features

### Duration Persistence
- Test item durations are stored in localStorage with keys: `test_duration_${item_key}`
- Durations are preserved across browser sessions
- Modified durations are automatically saved when changed

### Timeline Visualization
- Each test block shows its time range: e.g., "02:00 - 02:30"
- Total profile duration is calculated as: maximum(startOffsetMinutes + durationMinutes) minutes
- Format: "Xh Ym" (e.g., "2h 30m") or just "Xm" for durations under 1 hour

### Automatic Duration Calculation
When you load a procedure into the Schedule Timeline:
1. System fetches the procedure's `test_item_durations`
2. Sums all durations from enabled test items
3. Rounds to nearest 30-minute interval (aligns with timeline grid)
4. Uses this as the block's default width

## API Endpoints

### Get Procedure with Durations
```
GET /api/test/procedures/{procedure_name}
```

Response includes:
```json
{
  "success": true,
  "name": "My_Procedure",
  "config": {
    "test_items": { ... },
    "test_item_durations": { ... },
    ...
  }
}
```

### Save Schedule Profile with Time Information
```
POST /api/schedule/profiles
```

Payload includes:
```json
{
  "profile_name": "My_Profile",
  "cron_rule": { ... },
  "tests": [
    {
      "title": "...",
      "startOffsetMinutes": 0,
      "durationMinutes": 60,
      ...
    }
  ]
}
```

## Best Practices

1. **Set Realistic Durations**: Base durations on actual test execution times
2. **Account for Overhead**: Include time for setup, teardown, and potential delays
3. **Review Schedule Timeline**: Visually verify the schedule before saving
4. **Monitor First Run**: Check actual execution time and adjust durations for future runs
5. **Use Procedure Templates**: Create procedures with standard durations for consistent scheduling

## Limitations

- Duration must be between 1 and 120 minutes per test item
- Timeline uses 30-minute intervals, so durations are rounded up to nearest 30 minutes
- Maximum schedule runtime is 24 hours (00:00 to 23:59)

## Future Enhancements

- [ ] Historical duration tracking (average actual runtime)
- [ ] Automatic duration optimization based on actual execution data
- [ ] Parallel test execution (non-overlapping duration calculation)
- [ ] Duration templates per platform
