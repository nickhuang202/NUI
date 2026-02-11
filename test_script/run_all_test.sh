#!/bin/bash
export PATH=/usr/bin:/bin:/usr/sbin:/sbin

if [ $# -lt 2 ]; then
    echo "Usage: ./run_all_test.sh  <fboss_zst_file> <topology_name> [test_items]"
    echo ""
    echo "Examples:"
    echo "  ./run_all_test.sh fboss_bins_bcm_JC_20251030.tar.zst copper"
    echo "  ./run_all_test.sh fboss_bins_bcm_JC_20251030.tar.zst optics_one 'SAI_T0,SAI_T1,AGENT_T0'"
    echo ""
    echo "Topology name:"
    echo "  - default (Accton Config 1 - 800G)"
    echo "  - 400g (Accton Config 2 - 400G)"
    echo "  - copper (DAC)"
    echo "  - optics_one (Optics Config 1)"
    echo "  - optics_two (Optics Config 2)"
    echo ""
    echo "Test items (comma-separated, optional):"
    echo "  - SAI_T0, SAI_T1, SAI_T2"
    echo "  - AGENT_T0, AGENT_T1, AGENT_T2"
    echo "  - LINK_T0, LINK_T1, LINK_T2"
    echo "  - EVT_EXIT"
    exit 1
fi

DBG_LIB=dbglib.tar.gz

FBOSS_TAR_ZST=$1
TOPOLOGY_NAME=$2
TEST_ITEMS=$3

# Parse test items - if empty, run all tests
RUN_SAI_T0=true
RUN_SAI_T1=true
RUN_SAI_T2=true
RUN_AGENT_T0=true
RUN_AGENT_T1=true
RUN_AGENT_T2=true
RUN_LINK_T0=false
RUN_LINK_T1=false
RUN_LINK_T2=false
RUN_EVT_EXIT=false

if [ -n "$TEST_ITEMS" ]; then
    # User selected specific tests - disable all by default
    RUN_SAI_T0=false
    RUN_SAI_T1=false
    RUN_SAI_T2=false
    RUN_AGENT_T0=false
    RUN_AGENT_T1=false
    RUN_AGENT_T2=false
    RUN_LINK_T0=false
    RUN_LINK_T1=false
    RUN_LINK_T2=false
    RUN_EVT_EXIT=false
    
    # Enable selected tests
    IFS=',' read -ra TEST_ARRAY <<< "$TEST_ITEMS"
    for item in "${TEST_ARRAY[@]}"; do
        case "$item" in
            SAI_T0) RUN_SAI_T0=true ;;
            SAI_T1) RUN_SAI_T1=true ;;
            SAI_T2) RUN_SAI_T2=true ;;
            AGENT_T0) RUN_AGENT_T0=true ;;
            AGENT_T1) RUN_AGENT_T1=true ;;
            AGENT_T2) RUN_AGENT_T2=true ;;
            LINK_T0) RUN_LINK_T0=true ;;
            LINK_T1) RUN_LINK_T1=true ;;
            LINK_T2) RUN_LINK_T2=true ;;
            EVT_EXIT) RUN_EVT_EXIT=true ;;
        esac
    done
fi
HOME_DIR="/home"
HOME_TEST_SCRIPT_DIR="/home/NUI/test_script"
DEST_DIR="/opt/fboss"

# Load platform configuration to determine DETECTED_PLATFORM
source "$HOME_TEST_SCRIPT_DIR/platform_config.sh"

# Write platform cache file for dashboard
echo "========================================================================"
echo "Platform Detection"
echo "========================================================================"
echo "Detected Platform: $DETECTED_PLATFORM"
echo "Writing platform cache for dashboard..."

# Write .platform_cache file in NUI directory
PLATFORM_CACHE_FILE="/home/NUI/.platform_cache"
echo "$DETECTED_PLATFORM" > "$PLATFORM_CACHE_FILE"

if [ $? -eq 0 ]; then
    echo "✓ Platform cache file created: $PLATFORM_CACHE_FILE"
else
    echo "⚠ Warning: Failed to create platform cache file"
fi
echo "========================================================================"
echo ""

#remove log
rm  /var/facebook/logs/fboss/*

if [[ -f "$HOME_DIR/$FBOSS_TAR_ZST" && ! -d "$DEST_DIR" ]]; then
    mkdir -p "$DEST_DIR"
    pushd ./
    cd "$HOME_DIR" || { echo "can not enter $HOME_DIR"; exit 1; }
    zstd -d "$FBOSS_TAR_ZST" || { echo "uncompress zst failure!!!"; exit 1; }
    FBOSS_TAR="${FBOSS_TAR_ZST%.zst}"

    if [ ! -f "$FBOSS_TAR" ]; then
        echo "Can not find tar file：$FBOSS_TAR"
        exit 1
    fi
    tar xvf "$CONF_TAR" -C "$DEST_DIR"
    tar xvf "$FBOSS_TAR" -C "$DEST_DIR"
    tar xvf "/home/$DBG_LIB" -C "$DEST_DIR/lib/"
    rm "$FBOSS_TAR"
    popd
else
    echo "Use original /opt/fboss/ verson!!"
    rm /opt/fboss/*.tar.gz 2>/dev/null
fi

echo "Run Test!!"
echo "Test Items: $TEST_ITEMS"
echo "Topology Names: $TOPOLOGY_NAMES"

# SAI test
if [ "$RUN_SAI_T0" = true ]; then
    echo "Running SAI T0 test..."
    $HOME_TEST_SCRIPT_DIR/SAI_TX_test.sh $FBOSS_TAR_ZST t0
fi
if [ "$RUN_SAI_T1" = true ]; then
    echo "Running SAI T1 test..."
    $HOME_TEST_SCRIPT_DIR/SAI_TX_test.sh $FBOSS_TAR_ZST t1
fi
if [ "$RUN_SAI_T2" = true ]; then
    echo "Running SAI T2 test..."
    $HOME_TEST_SCRIPT_DIR/SAI_TX_test.sh $FBOSS_TAR_ZST t2
fi

# Agent HW test
if [ "$RUN_AGENT_T0" = true ]; then
    echo "Running Agent HW T0 test..."
    $HOME_TEST_SCRIPT_DIR/Agent_HW_TX_test.sh $FBOSS_TAR_ZST t0
fi
if [ "$RUN_AGENT_T1" = true ]; then
    echo "Running Agent HW T1 test..."
    $HOME_TEST_SCRIPT_DIR/Agent_HW_TX_test.sh $FBOSS_TAR_ZST t1
fi
if [ "$RUN_AGENT_T2" = true ]; then
    echo "Running Agent HW T2 test..."
    $HOME_TEST_SCRIPT_DIR/Agent_HW_TX_test.sh $FBOSS_TAR_ZST t2
fi

# Basic Link Test
if [ "$RUN_LINK_T0" = true ]; then
    echo "Running Link T0 test..."
    $HOME_TEST_SCRIPT_DIR/Link_T0_test.sh $FBOSS_TAR_ZST $TOPOLOGY_NAME
fi

# Link Test T1
if [ "$RUN_LINK_T1" = true ]; then
    echo "Running Link T1 test..."
    $HOME_TEST_SCRIPT_DIR/Link_T1_test.sh $FBOSS_TAR_ZST $TOPOLOGY_NAME
fi

# Link Test T2 (placeholder for future implementation)
if [ "$RUN_LINK_T2" = true ]; then
    echo "⚠ Link Test T2 is not yet implemented"
    # $HOME_TEST_SCRIPT_DIR/Link_T2_test.sh $FBOSS_TAR_ZST $TOPOLOGY_NAME
fi

# ExitEVT
if [ "$RUN_EVT_EXIT" = true ]; then
    echo "Running EVT Exit test..."
    $HOME_TEST_SCRIPT_DIR/ExitEVT.sh $FBOSS_TAR_ZST $TOPOLOGY_NAME
fi 

#PRBS Test
#$HOME_TEST_SCRIPT_DIR/Prbs_test.sh $FBOSS_TAR_ZST $TOPOLOGY_NAME 



# Organize test reports
DATE_DIR="all_test_$(date +%Y-%m-%d)"
REPORT_BASE="/home/NUI/test_report/$DETECTED_PLATFORM"
TARGET_DIR="$REPORT_BASE/$DATE_DIR"

echo ""
echo "========================================================================"
echo "Organizing Test Reports..."
echo "Target Directory: $TARGET_DIR"
echo "========================================================================"

mkdir -p "$TARGET_DIR"

# Move archives to target directory
# Archives may be found in REPORT_BASE (moved by individual scripts) or /opt/fboss (if not moved yet)

# Move from REPORT_BASE if present (ExitEVT.sh and others move there)
if [ -d "$REPORT_BASE" ]; then
    find "$REPORT_BASE" -maxdepth 1 -name "*.tar.gz" -exec mv {} "$TARGET_DIR/" \;
fi

# Also check /opt/fboss just in case any script didn't move it
find /opt/fboss -maxdepth 1 -name "*.tar.gz" -mmin -60 -exec mv {} "$TARGET_DIR/" \; 2>/dev/null

echo "✓ Reports organized in $TARGET_DIR"
ls -lh "$TARGET_DIR"

# Copy ExitEVT Excel report into the organized folder (if it exists)
EVT_REPORT_GLOB="/opt/fboss/${DETECTED_PLATFORM}_Testing_EVT_Exit_Link_*.xlsx"
if ls $EVT_REPORT_GLOB >/dev/null 2>&1; then
    cp -f $EVT_REPORT_GLOB "$TARGET_DIR/"
    if [ $? -eq 0 ]; then
        echo "✓ ExitEVT Excel report copied to $TARGET_DIR"
    else
        echo "⚠ Warning: Failed to copy ExitEVT Excel report to $TARGET_DIR"
    fi
fi
# Generate dashboard cache
echo ""
echo "========================================================================"
echo "Generating Dashboard Cache..."
echo "========================================================================"

# Extract date from folder name (all_test_YYYY-MM-DD)
TEST_DATE=$(date +%Y-%m-%d)

# Call Python script to generate cache
python3 "$HOME_TEST_SCRIPT_DIR/generate_cache.py" "$DETECTED_PLATFORM" "$TEST_DATE"

if [ $? -eq 0 ]; then
    echo "✓ Dashboard cache generated successfully"
else
    echo "⚠ Warning: Dashboard cache generation failed (not critical)"
fi

echo ""
echo "========================================================================"
echo "All Tests Completed!"
echo "========================================================================"
echo "Platform: $DETECTED_PLATFORM"
echo "Date: $TEST_DATE"
echo "Reports Location: $TARGET_DIR"
echo "========================================================================"
