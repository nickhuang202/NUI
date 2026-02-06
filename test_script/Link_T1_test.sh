#!/bin/bash
export PATH=/usr/bin:/bin:/usr/sbin:/sbin

META_BASIC_TEST_ITEMS=""

ZST_VER=$1
TOPOLOGY_NAME=$2
TEST_CASES=$3
DATE=`date +"%Y-%m-%d-%p%I-%M"`

if [ "$ZST_VER" == "" ] || [ "$TOPOLOGY_NAME" == "" ];then
        BIN=`cat /opt/fboss/Version_Info.txt | grep BIN | awk '{print $3}'`
	echo "Usage: ./Link_T1_test.sh <zst_version> <topology_name> [test_cases]"
	echo "Example: ./Link_T1_test.sh $BIN default"
	echo ""
	echo "Topology name: default, 400g, optics_one, optics_two, copper"
	exit
fi

# Load platform configuration (before cd)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/platform_config.sh"

dmesg -C
dmesg -C
mount -o remount,size=4G /dev/shm
rm -rf /dev/shm/fboss/

cd /opt/fboss/

export CONFIGERATOR_PRETEND_NOT_PROD=1
rmmod linux_ngknet linux_ngbde linux_user_bde linux_kernel_bde &> /dev/null
# use Derek's kernel module
lsmod | grep -q '^linux_ngbde' || insmod /home/linux_ngbde.ko
lsmod | grep -q '^linux_ngknet' || insmod /home/linux_ngknet.ko

sudo sync        # Flush file system buffers
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

LINK_TEST_LOG=t1_link_test_"$ZST_VER"_"$DATE".log
LINK_TEST_LOG_TAR=$LINK_TEST_LOG.tar.gz

source bin/setup_fboss_env
rm -f /opt/fboss/*.csv
rm -f /opt/fboss/*.tar.gz
rm -f /opt/fboss/*.log*

echo "========================================================================"
echo "Starting Link T1 Test"
echo "========================================================================"
echo "Test Log: $LINK_TEST_LOG"
echo ""

rm ./TEST_STATUS 2>/dev/null
echo "Sart Time:${DATE}" > ./TEST_STATUS
echo "Topology:${TOPOLOGY_NAME}" >> ./TEST_STATUS

# Set platform-specific configurations
case "$DETECTED_PLATFORM" in
	MINIPACK3BA)
    ./bin/run_test.py link --agent-run-mode mono  --config $AGENT_CONFIG --qsfp-config $QSFP_CONFIG --known-bad-tests-file ./share/link_known_bad_tests/agent_ensemble_link_known_bad_tests.materialized_JSON --skip-known-bad-tests "montblanc/sai/asicsdk-13.3.0.0_odp/13.3.0.0_odp" --mgmt-if eth0 2>&1 | tee "$LINK_TEST_LOG"
		;;
	MINIPACK3N)
    ./bin/run_test.py link --agent-run-mode mono --config $AGENT_CONFIG --qsfp-config $QSFP_CONFIG --known-bad-tests-file ./share/link_known_bad_tests/agent_ensemble_link_known_bad_tests.materialized_JSON --skip-known-bad-tests "montblanc/sai/asicsdk-13.3.0.0_odp/13.3.0.0_odp" --mgmt-if eth0 2>&1 | tee "$LINK_TEST_LOG"
		;;
	WEDGE800BACT)
    ./bin/run_test.py link --agent-run-mode mono --config $AGENT_CONFIG --qsfp-config $QSFP_CONFIG --known-bad-tests-file ./share/link_known_bad_tests/agent_ensemble_link_known_bad_tests.materialized_JSON --skip-known-bad-tests "montblanc/sai/asicsdk-13.3.0.0_odp/13.3.0.0_odp" --fruid-path=$FRU_CONFIG --mgmt-if eth0 --platform_mapping_override_path $PLAT_MAP_CONFIG 2>&1 | tee "$LINK_TEST_LOG"
		;;
	WEDGE800CACT)
    ./bin/run_test.py link --agent-run-mode mono --config $AGENT_CONFIG --qsfp-config $QSFP_CONFIG --known-bad-tests-file ./share/link_known_bad_tests/agent_ensemble_link_known_bad_tests.materialized_JSON --skip-known-bad-tests "montblanc/sai/asicsdk-13.3.0.0_odp/13.3.0.0_odp" --fruid-path=$FRU_CONFIG --mgmt-if eth0 --platform_mapping_override_path $PLAT_MAP_CONFIG 2>&1 | tee "$LINK_TEST_LOG"
		;;
esac

tar zcvf  "$LINK_TEST_LOG_TAR" "$LINK_TEST_LOG"

dmesg > demsg.log

echo ""
echo "========================================================================"
echo "Link T1 Test completed"
echo "Log file: $LINK_TEST_LOG"
echo "Archive file: $LINK_TEST_LOG_TAR"
echo "========================================================================"

# Find the hwtest_results CSV file
HWTEST_CSV=$(ls -t /opt/fboss/hwtest_results_*.csv 2>/dev/null | head -1)

echo ""

# Create comprehensive test results archive
echo ""
echo "========================================================================"
echo "Creating comprehensive test results archive..."
echo "========================================================================"

DATE=`date +"%Y-%m-%d-%p%I-%M"`
echo "log:$FINAL_ARCHIVE" >> ./TEST_STATUS
echo "End Time:${DATE}" >> ./TEST_STATUS

FINAL_ARCHIVE="LINK_T1_${DETECTED_PLATFORM}_${ZST_VER}_${TOPOLOGY_NAME}_${DATE}.tar.gz"

cd /opt/fboss

# List files to be archived
echo "Files to be archived:"
ls -lh *.csv 2>/dev/null || echo "  No CSV files found"
ls -lh fboss2_show_port*.txt 2>/dev/null || echo "  No fboss2_show_port.txt found"
ls -lh fboss2_show_transceivers*.txt 2>/dev/null || echo "  No fboss2_show_transceivers.txt found"
ls -lh Version_Info.txt 2>/dev/null || echo "  No Version_Info.txt found"
ls -lh *.log.tar.gz 2>/dev/null || echo "  No log.tar.gz files found"
ls -lh demsg.log 2>/dev/null || echo "  No demsg.log found"

# Create the archive with all test results
echo ""
echo "Creating archive: $FINAL_ARCHIVE"

# Prepare list of files to archive
ARCHIVE_FILES="*.csv fboss2_show_port.txt fboss2_show_transceivers.txt Version_Info.txt *.log.tar.gz demsg.log TEST_STATUS"

# Add configuration files if they exist
[ -f "$AGENT_CONFIG" ] && ARCHIVE_FILES="$ARCHIVE_FILES $AGENT_CONFIG"
[ -f "$QSFP_CONFIG" ] && ARCHIVE_FILES="$ARCHIVE_FILES $QSFP_CONFIG"
[ -n "$FRU_CONFIG" ] && [ -f "$FRU_CONFIG" ] && ARCHIVE_FILES="$ARCHIVE_FILES $FRU_CONFIG"
[ -n "$PLAT_MAP_CONFIG" ] && [ -f "$PLAT_MAP_CONFIG" ] && ARCHIVE_FILES="$ARCHIVE_FILES $PLAT_MAP_CONFIG"

tar zcvf "$FINAL_ARCHIVE" $ARCHIVE_FILES 2>/dev/null || true

if [ -f "$FINAL_ARCHIVE" ]; then
    ARCHIVE_SIZE=$(du -h "$FINAL_ARCHIVE" | cut -f1)
    
    # Move archive to /home/NUI/test_report/{platform}/
    REPORT_DIR="/home/NUI/test_report/${DETECTED_PLATFORM}"
    mkdir -p "$REPORT_DIR"
    
    mv "$FINAL_ARCHIVE" "$REPORT_DIR/"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "========================================================================"
        echo "✓ Archive created successfully: $FINAL_ARCHIVE"
        echo "  Size: $ARCHIVE_SIZE"
        echo "  Location: $REPORT_DIR/$FINAL_ARCHIVE"
        echo "========================================================================"
    else
        echo ""
        echo "========================================================================"
        echo "✓ Archive created: $FINAL_ARCHIVE (Size: $ARCHIVE_SIZE)"
        echo "✗ Warning: Failed to move archive to $REPORT_DIR/"
        echo "  Location: /opt/fboss/$FINAL_ARCHIVE"
        echo "========================================================================"
    fi
else
    echo ""
    echo "========================================================================"
    echo "✗ Warning: Failed to create archive"
    echo "========================================================================"
fi

