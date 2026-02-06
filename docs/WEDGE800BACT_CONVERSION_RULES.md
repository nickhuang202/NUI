# WEDGE800BACT Topology to Link Test Config Conversion Rules

## Overview

The WEDGE800BACT platform supports three different topology configurations:
1. **Copper Link**: Uses copper cables for connectivity
2. **Optics Link One**: Uses optical transceivers (configuration variant 1)
3. **Optics Link Two**: Uses optical transceivers (configuration variant 2)

## File Mapping

### Topology Files → Link Test Config Files

| Topology File | Link Test Config File |
|--------------|----------------------|
| `copper_wedge800bact.materialized_JSON` | `copper_link.json` |
| `optics_one_wedge800bact.materialized_JSON` | `optics_link_one.json` |
| `optics_two_wedge800bact.materialized_JSON` | `optics_link_two.json` |

## Key Conversion Rules

### 1. Port State Management

**Copper Configuration:**
- Ports **NOT in topology**: `state: 1` (disabled), no LLDP neighbor info
- Ports **IN topology**: `state: 2` (enabled), includes LLDP neighbor information

**Optics Configurations:**
- Ports **IN topology**: `state: 2` (enabled), includes LLDP neighbor information
- More ports are enabled compared to copper configuration

### 2. Profile ID to Speed Mapping

Common profile mappings used in WEDGE800BACT:

| Profile ID | Speed | Description |
|-----------|-------|-------------|
| 23 | 100G | 100 Gigabit Ethernet |
| 25 | 200G | 200 Gigabit Ethernet (optics) |
| 38 | 400G | 400 Gigabit Ethernet |
| 45 | 400G | 400 Gigabit Ethernet (copper) |
| 47 | 200G | 200 Gigabit Ethernet (optics variant 2) |
| 50 | 800G | 800 Gigabit Ethernet |

### 3. Lane Configuration

Speed determines lane configuration:
- **800G**: `/1` only (single lane)
- **400G**: `/1`, `/5` (two lanes)
- **200G**: `/1`, `/3`, `/5`, `/7` (four lanes)
- **100G**: `/1`, `/2`, `/3`, `/4`, `/5`, `/6`, `/7`, `/8` (eight lanes)

### 4. Copper vs Optics Differences

**Copper Link (copper_wedge800bact.materialized_JSON):**
```json
{
  "eth1/17/1": { "profileID": 38, "hasTransceiver": true },  // Disabled (not in active topology)
  "eth1/19/1": { "neighbor": "eth1/20/1", "profileID": 38, "hasTransceiver": true }  // Enabled
}
```

**Optics Link One (optics_one_wedge800bact.materialized_JSON):**
```json
{
  "eth1/17/1": { "neighbor": "eth1/18/1", "profileID": 38, "hasTransceiver": true },  // Enabled
  "eth1/19/1": { "neighbor": "eth1/20/1", "profileID": 25, "hasTransceiver": true }   // Enabled, different profile
}
```

**Optics Link Two (optics_two_wedge800bact.materialized_JSON):**
```json
{
  "eth1/17/1": { "neighbor": "eth1/18/1", "profileID": 38, "hasTransceiver": true },  // Enabled
  "eth1/17/5": { "neighbor": "eth1/18/5", "profileID": 25, "hasTransceiver": true },  // Mixed speeds
  "eth1/19/1": { "neighbor": "eth1/20/1", "profileID": 47, "hasTransceiver": true }   // Different profile
}
```

### 5. Port Configuration Structure

**Disabled Port (state: 1):**
```json
{
  "logicalID": 3,
  "state": 1,
  "speed": 400000,
  "name": "eth1/17/1",
  "profileID": 38,
  "expectedLLDPValues": {}  // Empty - no neighbor
}
```

**Enabled Port (state: 2):**
```json
{
  "logicalID": 3,
  "state": 2,
  "speed": 400000,
  "name": "eth1/17/1",
  "profileID": 38,
  "expectedLLDPValues": {
    "2": "eth1/18/1"  // Neighbor information
  }
}
```

## Usage Examples

### Generate Single Config

```bash
# Generate copper link config
python reconvert.py wedge800bact copper

# Generate optics_one config
python reconvert.py wedge800bact optics_one

# Generate optics_two config
python reconvert.py wedge800bact optics_two
```

### Generate All Configs

```bash
# Generate all three configs at once
python reconvert.py wedge800bact all
```

## Topology Structure

All topology files follow this structure:
```json
{
  "platform": "wedge800bact",
  "pimInfo": [
    {
      "slot": 1,
      "pimName": "",
      "interfaces": {
        "eth1/19/1": {
          "neighbor": "eth1/20/1",
          "profileID": 38,
          "hasTransceiver": true
        },
        ...
      },
      "tcvrs": {}
    }
  ]
}
```

## Key Implementation Details

1. **Port Discovery**: Script processes ports 1-64 in order, plus port 65 (service port)
2. **State Assignment**: 
   - Ports in topology get `state: 2` (enabled)
   - Ports not in topology get `state: 1` (disabled) with default 800G profile
3. **Neighbor Information**: Only enabled ports include LLDP neighbor values
4. **Profile-based Lane Generation**: Script automatically generates appropriate lane numbers based on profile speed

## Platform Configuration

In `reconvert.py`, WEDGE800BACT is configured with:

```python
"wedge800bact": {
    "topologies": {
        "copper": "Topology/WEDGE800BACT/copper_wedge800bact.materialized_JSON",
        "optics_one": "Topology/WEDGE800BACT/optics_one_wedge800bact.materialized_JSON",
        "optics_two": "Topology/WEDGE800BACT/optics_two_wedge800bact.materialized_JSON"
    },
    "outputs": {
        "copper": "copper_link.json",
        "optics_one": "optics_link_one.json",
        "optics_two": "optics_link_two.json"
    }
}
```

## Notes

- The service port (eth1/65/1) is always enabled with profile 23 (100G)
- Copper configs typically have fewer active ports than optics configs
- Profile IDs determine not only speed but also the type of cable/transceiver required
- The script maintains consistency with FBOSS configuration standards
