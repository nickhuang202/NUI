#!/bin/bash
export PATH=/usr/bin:/bin:/usr/sbin:/sbin


# Load platform configuration (before cd)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/platform_config.sh"

dmesg -C
dmesg -C
rm -rf /dev/shm/fboss/

cd /opt/fboss/

ZST_VER=$1
TEST_LEVEL=$2
DATE=`date +"%Y-%m-%d-%p%I-%M"`

if [ "$ZST_VER" == "" ];then
	BIN=`cat /opt/fboss/Version_Info.txt | grep BIN |  awk '{print $3}'`
	echo "Usage: ./Agent_HW_T0_test.sh <zst_version> [test_level]"
	echo "Example: ./Agent_HW_T0_test.sh $BIN t0"
	echo "         ./Agent_HW_T0_test.sh $BIN t1"
	echo "         ./Agent_HW_T0_test.sh $BIN t2"
	echo ""
	echo "test_level: t0 (default), t1, or t2"
	exit 1
fi

# Set default test level to t0 if not specified
if [ "$TEST_LEVEL" == "" ];then
	TEST_LEVEL="t0"
fi

echo "Test Level: $TEST_LEVEL"

export CONFIGERATOR_PRETEND_NOT_PROD=1
rmmod linux_ngknet linux_ngbde linux_user_bde linux_kernel_bde &> /dev/null
# use Derek's kernel module
lsmod | grep -q '^linux_ngbde' || insmod /home/linux_ngbde.ko
lsmod | grep -q '^linux_ngknet' || insmod /home/linux_ngknet.ko

sudo sync        # Flush file system buffers
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

#SAI AGENT HW TEST
LINK_TEST_LOG="${TEST_LEVEL}_sai_agent_test_${ZST_VER}_${DATE}.log"
LINK_TEST_LOG_TAR=$LINK_TEST_LOG.tar.gz

source bin/setup_fboss_env
rm -f /opt/fboss/*.csv
rm -f /opt/fboss/*.tar.gz
rm -f /opt/fboss/*.log*

echo "========================================================================"
echo "Starting SAI Agent HW ${TEST_LEVEL^^} Test"
echo "========================================================================"
echo "Test Log: $LINK_TEST_LOG"
echo ""

rm ./TEST_STATUS 2>/dev/null
echo "Sart Time:${DATE}" > ./TEST_STATUS

# Set platform-specific configurations
case "$DETECTED_PLATFORM" in
	MINIPACK3BA)
    ./bin/run_test.py sai_agent --filter_file=./share/hw_sanity_tests/${TEST_LEVEL}_agent_hw_tests.conf --config $AGENT_CONFIG --enable-production-features --asic tomahawk5 --production-features ./share/production_features/asic_production_features.materialized_JSON --known-bad-tests-file ./share/hw_known_bad_tests/sai_agent_known_bad_tests.materialized_JSON --skip-known-bad-tests "brcm/11.7.0.0_odp/11.7.0.0_odp/tomahawk5" --mgmt-if eth0 2>&1 | tee $LINK_TEST_LOG
		;;
	MINIPACK3N)
    ./bin/run_test.py sai_agent --filter_file=./share/hw_sanity_tests/${TEST_LEVEL}_agent_hw_tests.conf --config $AGENT_CONFIG --enable-production-features --asic tomahawk5 --production-features ./share/production_features/asic_production_features.materialized_JSON --known-bad-tests-file ./share/hw_known_bad_tests/sai_agent_known_bad_tests.materialized_JSON --skip-known-bad-tests "brcm/11.7.0.0_odp/11.7.0.0_odp/tomahawk5" --mgmt-if eth0 2>&1 | tee $LINK_TEST_LOG
		;;
	WEDGE800BACT)
    ./bin/run_test.py sai_agent --filter_file=./share/hw_sanity_tests/${TEST_LEVEL}_agent_hw_tests.conf --config $AGENT_CONFIG --enable-production-features --asic tomahawk5 --production-features ./share/production_features/asic_production_features.materialized_JSON --known-bad-tests-file ./share/hw_known_bad_tests/sai_agent_known_bad_tests.materialized_JSON --skip-known-bad-tests "brcm/11.7.0.0_odp/11.7.0.0_odp/tomahawk5" --fruid-path $FRU_CONFIG --mgmt-if eth0 --platform_mapping_override_path $PLAT_MAP_CONFIG 2>&1 | tee $LINK_TEST_LOG
		;;
	WEDGE800CACT)
    ./bin/run_test.py sai_agent --filter_file=./share/hw_sanity_tests/${TEST_LEVEL}_agent_hw_tests.conf --config $AGENT_CONFIG --enable-production-features --asic tomahawk5 --production-features ./share/production_features/asic_production_features.materialized_JSON --known-bad-tests-file ./share/hw_known_bad_tests/sai_agent_known_bad_tests.materialized_JSON --skip-known-bad-tests "brcm/11.7.0.0_odp/11.7.0.0_odp/tomahawk5" --fruid-path $FRU_CONFIG --mgmt-if eth0 --platform_mapping_override_path $PLAT_MAP_CONFIG 2>&1 | tee $LINK_TEST_LOG
		;;
esac

tar zcvf $LINK_TEST_LOG_TAR $LINK_TEST_LOG

echo ""
echo "========================================================================"
echo "SAI Agent HW ${TEST_LEVEL^^} Test completed"
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

FINAL_ARCHIVE="AGENT_HW_${TEST_LEVEL}_${DETECTED_PLATFORM}_${ZST_VER}_${DATE}.tar.gz"

cd /opt/fboss

# List files to be archived
echo "Files to be archived:"
ls -lh *.csv 2>/dev/null || echo "  No CSV files found"
ls -lh Version_Info.txt 2>/dev/null || echo "  No Version_Info.txt found"
ls -lh *.log.tar.gz 2>/dev/null || echo "  No log.tar.gz files found"
ls -lh demsg.log 2>/dev/null || echo "  No demsg.log found"

# Create the archive with all test results
echo ""
echo "Creating archive: $FINAL_ARCHIVE"

# Prepare list of files to archive
ARCHIVE_FILES="*.csv fboss2_show_port.txt Version_Info.txt *.log.tar.gz demsg.log TEST_STATUS"

# Add configuration files if they exist
[ -f "$AGENT_CONFIG" ] && ARCHIVE_FILES="$ARCHIVE_FILES $AGENT_CONFIG"
[ -f "$QSFP_CONFIG" ] && ARCHIVE_FILES="$ARCHIVE_FILES $QSFP_CONFIG"
[ -n "$FRU_CONFIG" ] && [ -f "$FRU_CONFIG" ] && ARCHIVE_FILES="$ARCHIVE_FILES $FRU_CONFIG"
[ -n "$PLAT_MAP_CONFIG" ] && [ -f "$PLAT_MAP_CONFIG" ] && ARCHIVE_FILES="$ARCHIVE_FILES $PLAT_MAP_CONFIG"

tar zcvf "$FINAL_ARCHIVE" $ARCHIVE_FILES 2>/dev/null || true

if [ -f "$FINAL_ARCHIVE" ]; then
    ARCHIVE_SIZE=$(du -h "$FINAL_ARCHIVE" | cut -f1)
    
    # Clean up .log.tar.gz after it's included in the final archive
    rm -f *.log.tar.gz 2>/dev/null
    
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

