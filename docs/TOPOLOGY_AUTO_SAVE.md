# Topology Auto-Save and Apply Functionality

## Feature Overview

Implemented automatic platform type detection and topology saving to corresponding directories, with automatic saving before executing reconvert.py.

## Four Platforms and Corresponding Files

| Platform | Save Path | Filename |
|------|----------|----------|
| MINIPACK3BA | `Topology/MINIPACK3BA/` | `montblanc.materialized_JSON` |
| MINIPACK3N | `Topology/MINIPACK3N/` | `minipack3n.materialized_JSON` |
| WEDGE800BACT | `Topology/WEDGE800BACT/` | `wedge800bact.materialized_JSON` |
| WEDGE800CACT | `Topology/WEDGE800CACT/` | `wedge800bact.materialized_JSON` |

## Main Updates

### 1. Automatic Save Path Detection

When switching platforms, the system automatically:
- Displays current platform
- Displays target path where topology will be saved
- Example: `Platform: MINIPACK3BA | Save Target: Topology/MINIPACK3BA/montblanc.materialized_JSON`

### 2. Enhanced Save Functionality

When clicking the **💾 SAVE** button in the topology management window:
- If no filename is entered, automatically uses the platform's default filename
- Automatically saves to `Topology/<platform_name>/<filename>`
- Displays full save path for confirmation

### 3. Apply Topology Workflow

When clicking the **⚙️ Apply topology** button, two steps are executed:

**Step 1/2**: Automatically save current topology
- Based on currently selected platform
- Save to corresponding `Topology/<platform>/` directory
- Use the platform's default filename

**Step 2/2**: Execute reconvert.py
- Automatically run `reconvert.py`
- Apply topology configuration to system

## Usage Examples

### Example 1: MINIPACK3BA Platform

1. Select platform: Click **MINIPACK3BA** button
2. Status bar shows: `Platform: MINIPACK3BA | Save Target: Topology/MINIPACK3BA/montblanc.materialized_JSON`
3. Configure port connections
4. Click **⚙️ Apply topology**
5. System automatically:
   - Saves topology to `Topology/MINIPACK3BA/montblanc.materialized_JSON`
   - Executes `reconvert.py`

### Example 2: WEDGE800BACT Platform

1. Select platform: Click **WEDGE800BACT** button
2. Status bar shows: `Platform: WEDGE800BACT | Save Target: Topology/WEDGE800BACT/wedge800bact.materialized_JSON`
3. Configure port connections
4. Click **⚙️ Apply topology**
5. System automatically:
   - Saves topology to `Topology/WEDGE800BACT/wedge800bact.materialized_JSON`
   - Executes `reconvert.py`

## Technical Details

### Frontend Modifications (NUI.html)

1. **switchPlatform()**: Displays save target path when switching platforms
2. **saveCurrentTopology()**: Automatically uses platform default filename
3. **applyTopologyConfig()**: Saves first, then executes reconvert.py

### Backend API (app.py)

- **/api/save_topology**: Saves topology to specified platform directory
- **/api/apply_topology**: Executes reconvert.py

## Confirmation Prompt

When executing Apply topology, a confirmation dialog is displayed:
```
Are you sure you want to save the topology and execute reconvert.py to apply the configuration?
```

After selecting "OK":
1. Automatically saves current topology configuration
2. Executes reconvert.py to apply configuration

## Status Feedback

During execution, the status bar displays:
- `Step 1/2: Saving topology to Topology/MINIPACK3BA/montblanc.materialized_JSON...`
- `Step 2/2: Executing reconvert.py (Platform: MINIPACK3BA)...`
- `✓ Apply topology succeeded` or `✗ Apply topology failed: [error message]`

## Important Notes

1. **Must Configure Connections First**: If there are no port connections, will prompt "Error: No connections to apply"
2. **Automatic Overwrite**: Saving will overwrite files with the same name in the corresponding platform directory
3. **Automatic Directory Creation**: If Topology directory doesn't exist, it will be created automatically

## File Structure

```
/home/NUI/
├── app.py                          # Flask backend
├── NUI.html                        # Frontend interface (updated)
├── reconvert.py                    # Configuration conversion script
└── Topology/
    ├── MINIPACK3BA/
    │   └── montblanc.materialized_JSON
    ├── MINIPACK3N/
    │   └── minipack3n.materialized_JSON
    ├── WEDGE800BACT/
    │   └── wedge800bact.materialized_JSON
    └── WEDGE800CACT/
        └── wedge800bact.materialized_JSON
```
