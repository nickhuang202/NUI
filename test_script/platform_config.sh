#!/bin/bash
# Platform Configuration Script
# This script detects the platform and sets appropriate configuration paths
# Used by: ExitEVT.sh, SAI_T0_test.sh, Agent_HW_T0_test.sh, LINK_T0_test.sh

# Auto-detect platform from FRUID
FRUID_PATH="/var/facebook/fboss/fruid.json"
DETECTED_PLATFORM=""

if [ -f "$FRUID_PATH" ]; then
    # Try using python to parse JSON (most reliable)
    if command -v python3 &> /dev/null; then
        PRODUCT_NAME=$(python3 -c "import json; f=open('$FRUID_PATH'); data=json.load(f); print(data.get('Information', {}).get('Product Name', ''))" 2>/dev/null | tr '[:lower:]' '[:upper:]')
    elif command -v python &> /dev/null; then
        PRODUCT_NAME=$(python -c "import json; f=open('$FRUID_PATH'); data=json.load(f); print(data.get('Information', {}).get('Product Name', ''))" 2>/dev/null | tr '[:lower:]' '[:upper:]')
    else
        # Fallback to grep if python is not available
        PRODUCT_NAME=$(grep -o '"Product Name"[[:space:]]*:[[:space:]]*"[^"]*"' "$FRUID_PATH" | sed 's/.*"Product Name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' | tr '[:lower:]' '[:upper:]')
    fi
    
    echo "Detected Product: $PRODUCT_NAME"
    
    case "$PRODUCT_NAME" in
        MINIPACK3|MINIPACK3BA)
            DETECTED_PLATFORM="MINIPACK3BA"
            ;;
        MINIPACK3N)
            DETECTED_PLATFORM="MINIPACK3N"
            ;;
        WEDGE800BACT)
            DETECTED_PLATFORM="WEDGE800BACT"
            ;;
        WEDGE800CACT)
            DETECTED_PLATFORM="WEDGE800CACT"
            ;;
        *)
            echo "Warning: Unknown platform '$PRODUCT_NAME', defaulting to WEDGE800BACT"
            DETECTED_PLATFORM="WEDGE800BACT"
            ;;
    esac
else
    echo "Warning: FRUID file not found, defaulting to WEDGE800BACT"
    DETECTED_PLATFORM="WEDGE800BACT"
fi

echo "Using platform: $DETECTED_PLATFORM"

# Set platform-specific configurations
case "$DETECTED_PLATFORM" in
    MINIPACK3BA)
        PLATFORM_CONF='mp3ba_conf'
        AGENT_CONFIG=/home/NUI/montblanc.materialized_JSON.tmp
        QSFP_CONFIG=/home/NUI/qsfp_test_configs/MINIPACK3BA/montblanc.materialized_JSON
        FRU_CONFIG=$FRUID_PATH
        PLAT_MAP_CONFIG=""
        ;;
    MINIPACK3N)
        PLATFORM_CONF='mp3n_conf'
        AGENT_CONFIG=/home/NUI/minipack3n.materialized_JSON.tmp
        QSFP_CONFIG=/home/NUI/qsfp_test_configs/MINIPACK3N/minipack3n.materialized_JSON
        FRU_CONFIG=/opt/$PLATFORM_CONF/fruid_minipack3n.json
        PLAT_MAP_CONFIG=/opt/$PLATFORM_CONF/minipack3n_platform_mapping.json
        ;;
    WEDGE800BACT)
        PLATFORM_CONF='w800bact_conf'
        AGENT_CONFIG=/home/NUI/wedge800bact.materialized_JSON.tmp
        QSFP_CONFIG=/home/NUI/qsfp_test_configs/WEDGE800BACT/wedge800bact.materialized_JSON
        #FRU_CONFIG=/opt/$PLATFORM_CONF/fruid_wedge800ba.json
        #PLAT_MAP_CONFIG=/opt/$PLATFORM_CONF/wedge800bact_platform_mapping.json
        PLAT_MAP_CONFIG=/home/NUI/link_test_configs/WEDGE800BACT/Configs-20260126T054954Z-1-001/Configs/wedge800bact_platform_mapping-2025-1223-v0.15.json
        FRU_CONFIG=/home/NUI/link_test_configs/WEDGE800BACT/Configs-20260126T054954Z-1-001/Configs/fruid.json
        ;;
    WEDGE800CACT)
        PLATFORM_CONF='w800cact_conf'
        AGENT_CONFIG=/home/NUI/wedge800cact.materialized_JSON.tmp
        QSFP_CONFIG=/home/NUI/qsfp_test_configs/WEDGE800BACT/wedge800bact.materialized_JSON
        FRU_CONFIG=/opt/$PLATFORM_CONF/fruid_wedge800ca.json
        PLAT_MAP_CONFIG=/opt/$PLATFORM_CONF/wedge800cact_platform_mapping.json
        ;;
esac

echo "AGENT_CONFIG: $AGENT_CONFIG"
echo "QSFP_CONFIG: $QSFP_CONFIG"
echo "FRU_CONFIG: $FRU_CONFIG"
echo "PLAT_MAP_CONFIG: $PLAT_MAP_CONFIG"
