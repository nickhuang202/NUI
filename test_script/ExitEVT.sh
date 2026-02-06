#!/bin/bash
export PATH=/usr/bin:/bin:/usr/sbin:/sbin


META_BASIC_TEST_ITEMS=""

mono_link_test_default_400g=(
AgentEnsembleEmptyLinkTest.CheckInit
AgentEnsembleLinkSanityTestDataPlaneFlood.qsfpWarmbootIsHitLess
AgentEnsembleLinkTest.asicLinkFlap
AgentEnsembleLinkTest.clearIphyInterfaceCounters
AgentEnsembleLinkTest.getTransceivers
AgentEnsembleLinkTest.iPhyInfoTest
AgentEnsembleLinkTest.opticsTxDisableEnable
AgentEnsembleLinkTest.opticsTxDisableRandomPorts
AgentEnsembleLinkTest.qsfpColdbootAfterAgentUp
AgentEnsembleLinkTest.testOpticsRemediation
AgentEnsembleOpticsTest.verifyTxRxLatches
AgentEnsembleQsfpFsdbTest.phy
AgentEnsembleQsfpFsdbTest.portState
AgentEnsembleQsfpFsdbTest.tcvr
AgentEnsembleFsdbTest.statsPublishSubscribe
AgentEnsembleLinkTest.verifyIphyFecBerCounters
AgentEnsembleQsfpFsdbTest.portStateWithResetHold
AgentEnsembleLinkSanityTestDataPlaneFlood.warmbootIsHitLess
AgentEnsembleLinkTest.ecmpShrink
AgentEnsembleLinkTest.trafficRxTx
AgentEnsembleMacLearningTest.l2EntryFlap
AgentEnsemblePtpTests.enablePtpPortDown
AgentEnsemblePtpTests.verifyPtpTcAfterLinkFlap
AgentEnsemblePtpTests.verifyPtpTcDelayRequest
AgentFabricLinkTest.linkActiveAndLoopStatus
)

mono_link_test=(
AgentEnsembleEmptyLinkTest.CheckInit
AgentEnsembleLinkSanityTestDataPlaneFlood.qsfpWarmbootIsHitLess
AgentEnsembleLinkTest.asicLinkFlap
AgentEnsembleLinkTest.clearIphyInterfaceCounters
AgentEnsembleLinkTest.getTransceivers
AgentEnsembleLinkTest.iPhyInfoTest
AgentEnsembleLinkTest.opticsTxDisableEnable
AgentEnsembleLinkTest.opticsTxDisableRandomPorts
AgentEnsembleLinkTest.qsfpColdbootAfterAgentUp
AgentEnsembleLinkTest.testOpticsRemediation
AgentEnsembleOpticsTest.verifyTxRxLatches
AgentEnsembleQsfpFsdbTest.phy
AgentEnsembleQsfpFsdbTest.portState
AgentEnsembleQsfpFsdbTest.tcvr
AgentEnsembleFsdbTest.statsPublishSubscribe
AgentEnsembleLinkTest.verifyIphyFecBerCounters
AgentEnsembleQsfpFsdbTest.portStateWithResetHold
AgentEnsembleLinkSanityTestDataPlaneFlood.warmbootIsHitLess
AgentEnsembleLinkTest.ecmpShrink
AgentEnsembleLinkTest.trafficRxTx
AgentEnsembleMacLearningTest.l2EntryFlap
AgentEnsemblePtpTests.enablePtpPortDown
AgentEnsemblePtpTests.verifyPtpTcAfterLinkFlap
AgentEnsemblePtpTests.verifyPtpTcDelayRequest
AgentEnsembleSpeedChangeTest.FOURHUNDREDGToTWOHUNDREDG
AgentEnsembleSpeedChangeTest.HUNDREDGToTWOHUNDREDG
AgentEnsembleSpeedChangeTest.TWOHUNDREDGToHUNDREDG
AgentFabricLinkTest.linkActiveAndLoopStatus
AgentEnsembleSpeedChangeTest.TWOHUNDREDGToFOURHUNDREDG
)

mono_link_test_retest=(
AgentEnsembleLinkTest.opticsTxDisableEnable
AgentEnsembleLinkTest.opticsTxDisableRandomPorts
)

mono_link_test_T0=(
AgentEnsembleLinkTest.opticsTxDisableEnable
)

mono_link_test_prbs=(
AgentEnsembleLinkTest.opticsTxDisableEnable
PRBS_TEST=Prbs_ASIC_P31_TO_ASIC_P31.prbsSanity:Prbs_ASIC_P31_TO_TCVR_S_P31Q_FR4_400G.prbsSanity:Prbs_TCVR_L_P31Q_TO_TCVR_L_P31Q_FR4_400G.prbsSanity

)



FBOSS_TAR_ZST=$1
TOPOLOGY_NAME=$2
SHEET_NAME=$(echo "$FBOSS_TAR_ZST" | sed -E 's/.*_([0-9]{8}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[a-f0-9]{10}).*/\1/')
echo "$SHEET_NAME"

TEST_CASES=$3
DATE=`date +"%Y-%m-%d-%p%I-%M"`

if [ "$FBOSS_TAR_ZST" == "" ] || [ "$TOPOLOGY_NAME" == "" ];then
        BIN=`cat /opt/fboss/Version_Info.txt | grep BIN | awk '{print $3}'`
	echo "Usage: ./ExitEVT.sh <fboss_tar_zst> <topology_name> [test_cases]"
	echo "Example: ./ExitEVT.sh $BIN copper"
	echo "         ./ExitEVT.sh $BIN optics_one"
	echo "         ./ExitEVT.sh $BIN copper AgentEnsembleLinkTest.iPhyInfoTest"
	echo ""
	echo "Topology name:"
	echo "  - copper (DAC)"
	echo "  - optics_one (Optics Config 1)"
	echo "  - optics_two (Optics Config 2)"
	echo "  - default (800G default config)"
	echo "  - 400g (Accton Config 2 - 400G)"
	exit
fi

ZST_VER=$FBOSS_TAR_ZST

if [ "$TEST_CASES" == "" ];then
    # Determine test items based on topology type
    if [ "$TOPOLOGY_NAME" == "optics_one" ] || [ "$TOPOLOGY_NAME" == "optics_two" ] || [ "$TOPOLOGY_NAME" == "copper" ]; then
        # For optics one/two/copper topology
        META_BASIC_TEST_ITEMS=$(IFS=:; echo "${mono_link_test[*]}")
    else
        # For optics default/400g topology
        META_BASIC_TEST_ITEMS=$(IFS=:; echo "${mono_link_test_default_400g[*]}")
    fi
    TEST_CASES="$META_BASIC_TEST_ITEMS"
fi

# Load platform configuration (before cd)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/platform_config.sh"

dmesg -C
mount -o remount,size=8G /dev/shm
rm -rf /dev/shm/fboss/

cd /opt/fboss/

export CONFIGERATOR_PRETEND_NOT_PROD=1
rmmod linux_ngknet linux_ngbde linux_user_bde linux_kernel_bde &> /dev/null
# use Derek's kernel module
lsmod | grep -q '^linux_ngbde' || insmod /home/linux_ngbde.ko
lsmod | grep -q '^linux_ngknet' || insmod /home/linux_ngknet.ko

export CONFIGERATOR_PRETEND_NOT_PROD=1

sudo sync        # Flush file system buffers
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

echo "\"$TEST_CASES\""
LINK_TEST_LOG=link_test_"$ZST_VER"_"$DATE"_BASIC.log
LINK_TEST_LOG_TAR=$LINK_TEST_LOG.tar.gz
source bin/setup_fboss_env
rm -f /opt/fboss/*.csv
rm -f /opt/fboss/*.tar.gz
rm -f /opt/fboss/*.log*

rm ./TEST_STATUS 2>/dev/null
echo "Sart Time:${DATE}" > ./TEST_STATUS
echo "Topology:${TOPOLOGY_NAME}" >> ./TEST_STATUS

# Set platform-specific configurations
case "$DETECTED_PLATFORM" in
	MINIPACK3BA)
	./bin/run_test.py link --filter="$TEST_CASES" --agent-run-mode mono  --config $AGENT_CONFIG --qsfp-config $QSFP_CONFIG  --mgmt-if eth0 2>&1 | tee "$LINK_TEST_LOG"
		;;
	MINIPACK3N)
	./bin/run_test.py link --filter="$TEST_CASES" --agent-run-mode mono  --config $AGENT_CONFIG --qsfp-config $QSFP_CONFIG  --mgmt-if eth0 2>&1 | tee "$LINK_TEST_LOG"
		;;
	WEDGE800BACT)
	./bin/run_test.py link --filter="$TEST_CASES" --agent-run-mode mono  --config $AGENT_CONFIG --qsfp-config $QSFP_CONFIG  --fruid-path=$FRU_CONFIG --mgmt-if eth0 --platform_mapping_override_path $PLAT_MAP_CONFIG 2>&1 | tee "$LINK_TEST_LOG"
		;;
	WEDGE800CACT)
	./bin/run_test.py link --filter="$TEST_CASES" --agent-run-mode mono  --config $AGENT_CONFIG --qsfp-config $QSFP_CONFIG  --fruid-path=$FRU_CONFIG --mgmt-if eth0 --platform_mapping_override_path $PLAT_MAP_CONFIG 2>&1 | tee "$LINK_TEST_LOG"
		;;
esac

tar zcvf  "$LINK_TEST_LOG_TAR" "$LINK_TEST_LOG"

dmesg > dmesg.log

DATE=`date +"%Y-%m-%d-%p%I-%M"`
echo "log:$FINAL_ARCHIVE" >> ./TEST_STATUS
echo "End Time:${DATE}" >> ./TEST_STATUS

# Generate Excel report using fill_result_v1.py
echo ""
echo "========================================================================"
echo "Generating Excel test report..."
echo "========================================================================"

# Find the hwtest_results CSV file
HWTEST_CSV=$(ls -t /opt/fboss/hwtest_results_*.csv 2>/dev/null | head -1)

if [ -n "$HWTEST_CSV" ]; then
    echo "Found hwtest CSV: $HWTEST_CSV"
    
    # Determine column index based on topology name
    case "$TOPOLOGY_NAME" in
        optics_one)
            COLUMN_INDEX=1
            ;;
        optics_two)
            COLUMN_INDEX=2
            ;;
        copper)
            COLUMN_INDEX=3
            ;;
        aec)
            COLUMN_INDEX=4
            ;;
        default|800g)
            COLUMN_INDEX=5
            ;;
        400g)
            COLUMN_INDEX=6
            ;;
        *)
            echo "Warning: Unknown topology '$TOPOLOGY_NAME', using column 1"
            COLUMN_INDEX=1
            ;;
    esac
    
    # Set template and output paths
    SCRIPT_DIR=/home/NUI/test_script
    TEMPLATE_FILE="${SCRIPT_DIR}/EVT_Testing_EVT_Exit_Link.xlsx"
    OUTPUT_FILE="/opt/fboss/${DETECTED_PLATFORM}_Testing_EVT_Exit_Link.xlsx"
    
    # Check if template exists, fall back to WEDGE800BACT template if not
    if [ ! -f "$TEMPLATE_FILE" ]; then
        echo "Warning: Template not found: $TEMPLATE_FILE"
        exit 1
    fi
    
    if [ -f "$TEMPLATE_FILE" ]; then
        echo "Template: $TEMPLATE_FILE"
        echo "Topology: $TOPOLOGY_NAME (Column $COLUMN_INDEX)"
        echo "Sheet name: $SHEET_NAME"
        echo "Output: $OUTPUT_FILE"
        echo ""
        
        python3 "${SCRIPT_DIR}/fill_result_v1.py" \
            "$HWTEST_CSV" \
            "$TEMPLATE_FILE" \
            "$OUTPUT_FILE" \
            "$COLUMN_INDEX" \
            "$SHEET_NAME"
        
        if [ $? -eq 0 ]; then
            echo "✓ Excel report generated successfully: $OUTPUT_FILE"
        else
            echo "✗ Failed to generate Excel report"
        fi
    else
        echo "Error: Template file not found: $TEMPLATE_FILE"
    fi
else
    echo "Warning: No hwtest_results CSV file found in /opt/fboss/"
fi

echo ""

# Create comprehensive test results archive
echo ""
echo "========================================================================"
echo "Creating comprehensive test results archive..."
echo "========================================================================"

FINAL_ARCHIVE="ExitEVT_${DETECTED_PLATFORM}_${ZST_VER}_${TOPOLOGY_NAME}_${DATE}.tar.gz"

cd /opt/fboss

# List files to be archived
echo "Files to be archived:"
ls -lh *.csv 2>/dev/null || echo "  No CSV files found"
ls -lh *.xlsx 2>/dev/null || echo "  No Excel files found"
ls -lh fboss2_show_port*.txt 2>/dev/null || echo "  No fboss2_show_port.txt found"
ls -lh fboss2_show_transceivers*.txt 2>/dev/null || echo "  No fboss2_show_transceivers.txt found"
ls -lh Version_Info.txt 2>/dev/null || echo "  No Version_Info.txt found"
ls -lh *.log.tar.gz 2>/dev/null || echo "  No log.tar.gz files found"
ls -lh demsg.log 2>/dev/null || echo "  No demsg.log found"

# Create the archive with all test results
echo ""
echo "Creating archive: $FINAL_ARCHIVE"

# Prepare list of files to archive
ARCHIVE_FILES="*.csv *.xlsx fboss2_show_port.txt fboss2_show_transceivers.txt Version_Info.txt *.log.tar.gz demsg.log TEST_STATUS"

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
        echo "========================================================================"
    fi
else
    echo ""
    echo "========================================================================"
    echo "✗ Warning: Failed to create archive"
    echo "========================================================================"
fi


