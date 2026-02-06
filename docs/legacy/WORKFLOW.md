# Topology Application Workflow Diagram

## Overall Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Open NUI Interface                          │
│                   http://localhost:5000                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Select Platform (Choose One)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌────────┐│
│  │ MINIPACK3N  │  │ MINIPACK3BA │  │ WEDGE800BACT │  │WEDGE800││
│  │             │  │             │  │              │  │  CACT  ││
│  └─────────────┘  └─────────────┘  └──────────────┘  └────────┘│
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Auto-display Save Target Path                       │
│   Platform: MINIPACK3BA | Save Target: Topology/MINIPACK3BA/... │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Configure Port Connections                      │
│   • Click ports to create connections                            │
│   • Set Profile ID                                               │
│   • Can load existing topology files                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Click "⚙️ Apply topology" Button                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Confirmation Dialog                             │
│   Are you sure you want to save topology and run reconvert.py?  │
│                 ┌───────┐    ┌──────┐                           │
│                 │  OK   │    │Cancel│                           │
│                 └───┬───┘    └──────┘                           │
└─────────────────────┼────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│          Step 1/2: Auto-save Current Topology                    │
│                                                                  │
│  Determine save path based on current platform:                 │
│  • MINIPACK3BA   → Topology/MINIPACK3BA/montblanc.mat...JSON    │
│  • MINIPACK3N    → Topology/MINIPACK3N/minipack3n.mat...JSON    │
│  • WEDGE800BACT  → Topology/WEDGE800BACT/wedge800bact...JSON    │
│  • WEDGE800CACT  → Topology/WEDGE800CACT/wedge800bact...JSON    │
│                                                                  │
│  Collect information:                                            │
│  - All port connections                                          │
│  - Profile ID for each port                                      │
│  - Platform information                                          │
│                                                                  │
│  Build JSON structure:                                           │
│  {                                                               │
│    "platform": "minipack3ba",                                    │
│    "pimInfo": [{                                                 │
│      "slot": 1,                                                  │
│      "interfaces": {                                             │
│        "eth1/1/1": {                                             │
│          "neighbor": "eth1/2/1",                                 │
│          "profileID": 39,                                        │
│          "hasTransceiver": true                                  │
│        },                                                        │
│        ...                                                       │
│      }                                                           │
│    }],                                                           │
│    "metadata": {                                                 │
│      "saved_by": "NUI",                                          │
│      "timestamp": "2025-12-29T...",                              │
│      "connection_count": 36                                      │
│    }                                                             │
│  }                                                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│             Step 2/2: Execute reconvert.py                       │
│                                                                  │
│  Execute command: python reconvert.py                            │
│                                                                  │
│  reconvert.py will:                                              │
│  1. Read Topology/<platform>/<file>                              │
│  2. Convert to system configuration format                       │
│  3. Apply to actual hardware configuration                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Display Results                                 │
│                                                                  │
│  Success: ✓ Apply topology succeeded                             │
│  Failure: ✗ Apply topology failed: [error message]               │
└─────────────────────────────────────────────────────────────────┘
```

## Platform Mapping Table

| Platform Code | Save Directory | Default Filename | Purpose |
|---------|---------|-------------|------|
| MINIPACK3BA | Topology/MINIPACK3BA/ | montblanc.materialized_JSON | Montblanc Switch Topology |
| MINIPACK3N | Topology/MINIPACK3N/ | minipack3n.materialized_JSON | Minipack3N Switch Topology |
| WEDGE800BACT | Topology/WEDGE800BACT/ | wedge800bact.materialized_JSON | Wedge800B ACT Topology |
| WEDGE800CACT | Topology/WEDGE800CACT/ | wedge800bact.materialized_JSON | Wedge800C ACT Topology |

## Manual Save Workflow

```
Click "⤓ Topology mgmt" Button
        │
        ▼
Display Topology Management Window
        │
        ├─→ Select Existing File (LOAD)
        │
        └─→ Enter New Filename + Click SAVE
                │
                ▼
        Auto-save to Topology/<current_platform>/
```

## API Endpoints

### 1. POST /api/save_topology
Save topology configuration

**Request:**
```json
{
  "platform": "MINIPACK3BA",
  "filename": "montblanc.materialized_JSON",
  "connections": [
    {
      "port1": "eth1/1/1",
      "port2": "eth1/2/1",
      "profile1": 39,
      "profile2": 39
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "file": "montblanc.materialized_JSON",
  "path": "/home/NUI/Topology/MINIPACK3BA/montblanc.materialized_JSON",
  "connections": 36
}
```

### 2. POST /api/apply_topology
Execute reconvert.py

**Request:**
```json
{
  "platform": "MINIPACK3BA"
}
```

**Response:**
```json
{
  "success": true,
  "message": "reconvert.py executed successfully",
  "stdout": "...",
  "stderr": ""
}
```

## File Structure

```
/home/NUI/
├── app.py                              # Flask backend application
├── NUI.html                            # Frontend interface (updated)
├── reconvert.py                        # Topology configuration conversion script
├── test_topology_feature.py            # Test script
├── TOPOLOGY_AUTO_SAVE.md               # Feature documentation
├── WORKFLOW.md                         # This document
│
└── Topology/                           # Topology configuration directory
    ├── MINIPACK3BA/
    │   ├── montblanc.materialized_JSON            # Default file ⭐
    │   ├── montblanc.materialized_400G_JSON
    │   ├── montblanc.materialized_800G_400G_MIX_JSON
    │   └── montblanc.materialized_800G_400G_200G_MIX_JSON
    │
    ├── MINIPACK3N/
    │   ├── minipack3n.materialized_JSON           # Default file ⭐
    │   ├── minipack3n_800G_AEC_OPTIC_MIX.materialized_JSON
    │   ├── minipack3n.materialized_800_400G_AEC_OPTIC_MIX_JSON
    │   └── minipack3n_port_profile_mapping.csv
    │
    ├── WEDGE800BACT/
    │   ├── wedge800bact.materialized_JSON         # Default file ⭐
    │   ├── copper_wedge800bact.materialized_JSON
    │   ├── optics_one_wedge800bact.materialized_JSON
    │   ├── optics_two_wedge800bact.materialized_JSON
    │   └── wedge800bact_port_profile_mapping.csv
    │
    └── WEDGE800CACT/
        └── wedge800bact.materialized_JSON         # Default file ⭐
```

## Important Notes

1. ⚠️ **Automatic Overwrite**: Apply topology will overwrite default files
2. ✓ **Auto-create**: Directories will be automatically created if they don't exist
3. ✓ **Bidirectional Connections**: System automatically creates bidirectional connections
4. ⚠️ **Confirmation Required**: Confirmation dialog shown before execution
5. ✓ **Status Feedback**: Execution status displayed throughout

## Error Handling

| Error Scenario | Handling |
|---------|---------|
| No connections configured | Prompt "No connections to apply" |
| Save failed | Display error message, don't execute reconvert.py |
| reconvert.py execution failed | Display complete error message |
| Network request failed | Display error and maintain current state |
