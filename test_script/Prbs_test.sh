#!/bin/bash
set -euo pipefail

######################################
# Arguments
######################################
ZST_VER=${1:-}
TOPOLOGY_NAME=${2:-}
TEST_CASES=${3:-}
DATE=$(date +"%Y%m%d_%H%M%S")

######################################
# Usage
######################################
if [ -z "$ZST_VER" ] || [ -z "$TOPOLOGY_NAME" ]; then
    BIN=$(awk '/BIN/ {print $3}' /opt/fboss/Version_Info.txt)
    echo "Usage: ./Prbs_test.sh <zst_version> <topology_name> [test_cases]"
    echo "Example: ./Prbs_test.sh $BIN default"
    echo ""
    echo "Topology names: 400g, default"
    exit 1
fi

######################################
# PRBS test definitions
######################################
link_test_PRBS_400G=(
Prbs_ASIC_P31_TO_ASIC_P31.prbsSanity:Prbs_ASIC_P31_TO_TCVR_S_P31Q_FR4_400G.prbsSanity:Prbs_TCVR_L_P31Q_TO_TCVR_L_P31Q_FR4_400G.prbsSanity
)

link_test_PRBS_800G=(
Prbs_ASIC_P31_TO_ASIC_P31.prbsSanity
)
#Prbs_ASIC_P31_TO_ASIC_P31.prbsSanity:Prbs_ASIC_P31_TO_TCVR_S_P31Q_FR4_800G.prbsSanity:Prbs_TCVR_L_P31Q_TO_TCVR_L_P31Q_FR4_800G.prbsSanity

######################################
# Load platform configuration
######################################
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/platform_config.sh"

######################################
# Select PRBS test cases by topology
######################################
case "$TOPOLOGY_NAME" in
    400g)
        link_test_PRBS=("${link_test_PRBS_400G[@]}")
        ;;
    default)
        link_test_PRBS=("${link_test_PRBS_800G[@]}")
        ;;
    *)
        echo "ERROR: Unsupported topology: $TOPOLOGY_NAME"
        exit 1
        ;;
esac

META_BASIC_TEST_ITEMS=$(IFS=:; echo "${link_test_PRBS[*]}")

if [ -z "$TEST_CASES" ]; then
    TEST_CASES="$META_BASIC_TEST_ITEMS"
fi

######################################
# Environment prep
######################################
dmesg -C || true
mount -o remount,size=4G /dev/shm || true
rm -rf /dev/shm/fboss/

cd /opt/fboss

export CONFIGERATOR_PRETEND_NOT_PROD=1

rmmod linux_ngknet linux_ngbde linux_user_bde linux_kernel_bde &>/dev/null || true
lsmod | grep -q '^linux_ngbde' || insmod /home/linux_ngbde.ko
lsmod | grep -q '^linux_ngknet' || insmod /home/linux_ngknet.ko

sync
echo 3 > /proc/sys/vm/drop_caches

######################################
# Logs
######################################
LINK_TEST_LOG="prbs_link_test_${ZST_VER}_${DATE}.log"
LINK_TEST_LOG_TAR="${LINK_TEST_LOG}.tar.gz"
TEST_STATUS="/opt/fboss/TEST_STATUS"

source bin/setup_fboss_env

rm -f /opt/fboss/*.csv /opt/fboss/*.tar.gz /opt/fboss/*.log*

echo "========================================================================"
echo "Starting Link PRBS Test"
echo "========================================================================"
echo "Test Log: $LINK_TEST_LOG"
echo ""

echo "Start Time:${DATE}" > "$TEST_STATUS"
echo "Topology:${TOPOLOGY_NAME}" >> "$TEST_STATUS"
echo "Platform:${DETECTED_PLATFORM}" >> "$TEST_STATUS"

######################################
# Run tests
######################################
case "$DETECTED_PLATFORM" in
    MINIPACK3BA)
        ./bin/run_test.py link --agent-run-mode mono --test-run-timeout 16000 \
            --filter="$TEST_CASES" \
            --config "$AGENT_CONFIG" \
            --qsfp-config "$QSFP_CONFIG" \
            --mgmt-if eth0 2>&1 | tee "$LINK_TEST_LOG"
        ;;
    MINIPACK3N)
        ./bin/run_test.py link --agent-run-mode mono --test-run-timeout 16000 \
            --filter="$TEST_CASES" \
            --config "$AGENT_CONFIG" \
            --qsfp-config "$QSFP_CONFIG" \
            --mgmt-if eth0 2>&1 | tee "$LINK_TEST_LOG"
        ;;
    WEDGE800BACT|WEDGE800CACT)
        ./bin/run_test.py link --agent-run-mode mono --test-run-timeout 16000 \
            --filter="$TEST_CASES" \
            --config "$AGENT_CONFIG" \
            --qsfp-config "$QSFP_CONFIG" \
            --fruid-path "$FRU_CONFIG" \
            --platform_mapping_override_path "$PLAT_MAP_CONFIG" \
            --mgmt-if eth0 2>&1 | tee "$LINK_TEST_LOG"
        ;;
    *)
        echo "ERROR: Unsupported platform $DETECTED_PLATFORM"
        exit 1
        ;;
esac

######################################
# Post processing
######################################
tar zcvf "$LINK_TEST_LOG_TAR" "$LINK_TEST_LOG"
dmesg > dmesg.log

DATE_END=$(date +"%Y%m%d_%H%M%S")
FINAL_ARCHIVE="LINK_PRBS_${DETECTED_PLATFORM}_${ZST_VER}_${TOPOLOGY_NAME}_${DATE_END}.tar.gz"

echo "End Time:${DATE_END}" >> "$TEST_STATUS"
echo "Archive:${FINAL_ARCHIVE}" >> "$TEST_STATUS"

######################################
# Create final archive
######################################
ARCHIVE_FILES="*.csv fboss2_show_port.txt fboss2_show_transceivers.txt Version_Info.txt *.log.tar.gz dmesg.log TEST_STATUS"

[ -f "$AGENT_CONFIG" ] && ARCHIVE_FILES+=" $AGENT_CONFIG"
[ -f "$QSFP_CONFIG" ] && ARCHIVE_FILES+=" $QSFP_CONFIG"
[ -f "${FRU_CONFIG:-}" ] && ARCHIVE_FILES+=" $FRU_CONFIG"
[ -f "${PLAT_MAP_CONFIG:-}" ] && ARCHIVE_FILES+=" $PLAT_MAP_CONFIG"

tar zcvf "$FINAL_ARCHIVE" $ARCHIVE_FILES || true

if [ -f "$FINAL_ARCHIVE" ]; then
    # Clean up .log.tar.gz after it's included in the final archive
    rm -f *.log.tar.gz 2>/dev/null
fi

REPORT_DIR="/home/NUI/test_report/${DETECTED_PLATFORM}"
mkdir -p "$REPORT_DIR"
mv "$FINAL_ARCHIVE" "$REPORT_DIR/"

echo "========================================================================"
echo "✓ Link PRBS Test completed"
echo "Archive: $REPORT_DIR/$FINAL_ARCHIVE"
echo "========================================================================"
