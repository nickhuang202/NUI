import os
import sys
import shutil
import tarfile
import json
import unittest
from datetime import datetime

# Add parent directory to path to import dashboard
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dashboard

class TestDashboardLogic(unittest.TestCase):
    def setUp(self):
        # Setup temporary test directory
        self.test_dir = os.path.join(os.getcwd(), "test_report_mock")
        dashboard.TEST_REPORT_BASE = self.test_dir
        
        self.platform = "MINIPACK3BA"
        self.date = "2026-01-10"
        self.target_dir = os.path.join(self.test_dir, self.platform, f"all_test_{self.date}")
        
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.target_dir)

    def tearDown(self):
        # Clean up
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_dummy_archive(self, name, csv_content, version_content=None):
        tar_path = os.path.join(self.target_dir, name)
        with tarfile.open(tar_path, "w:gz") as tar:
            # Add CSV - Force identical name to verify no collision
            csv_info = tarfile.TarInfo(name="common_results.csv")
            csv_bytes = csv_content.encode('utf-8')
            csv_info.size = len(csv_bytes)
            tar.addfile(csv_info, io.BytesIO(csv_bytes))
            
            # Add Version Info if provided
            if version_content:
                v_info = tarfile.TarInfo(name="Version_Info.txt")
                v_bytes = version_content.encode('utf-8')
                v_info.size = len(v_bytes)
                tar.addfile(v_info, io.BytesIO(v_bytes))

    def test_dashboard_parsing(self):
        # 1. Create dummy data
        version_text = """FBOSS_COMMIT_URL: https://github.com/facebook/fboss/commit/abc
FBOSS_COMMIT_DESC: 123 Update
FBOSS_BINARY: fboss_bins_test.tar.zst
BCM SAI_VERSION: 1.0
OCP SAI_VERSION: 2.0
BCM HSDK_VERSION: 6.5.32"""

        csv_pass = "Test1,PASS,Msg\nTest2,PASS,Msg"
        csv_fail = "Test3,FAIL,Msg\nTest4,PASS,Msg"

        # Create archives with realistic filenames (that previously caused issue)
        
        # 1. SAI T0 (Should match SAI)
        self.create_dummy_archive(
            "SAI_t0_MINIPACK3BA_fboss_bins_varFBOSSsai_SAI_13_3_0_GA_tar.zst_2026-01-09.tar.gz",
            csv_pass,
            version_text
        )

        # 2. Agent HW T0 (Should match AGENT_HW, NOT SAI)
        self.create_dummy_archive(
            "AGENT_HW_t0_MINIPACK3BA_fboss_bins_varFBOSSsai_SAI_13_3_0_GA_tar.zst_2026-01-09.tar.gz",
            csv_pass
        )

        # 3. Link T0 (Should match LINK, NOT SAI)
        self.create_dummy_archive(
            "LINK_T0_MINIPACK3BA_fboss_bins_varFBOSSsai_SAI_13_3_0_GA_tar.zst_2026-01-09.tar.gz",
            csv_pass
        )

        # 4. ExitEVT (Should match ExitEVT, NOT SAI)
        self.create_dummy_archive(
            "ExitEVT_MINIPACK3BA_fboss_bins_varFBOSSsai_SAI_13_3_0_GA_tar.zst_2026-01-09.tar.gz",
            csv_pass
        )

        # 2. Run Dashboard Logic
        summary = dashboard.get_dashboard_summary(self.platform, self.date)
        
        # 3. Verify Results
        print("\n--- Dashboard Summary Result ---")
        print(json.dumps(summary, indent=2))

        self.assertEqual(summary["platform"], self.platform)
        self.assertEqual(summary["version_info"]["FBOSS_COMMIT_URL"], "https://github.com/facebook/fboss/commit/abc")
        
        # Check Stats
        # SAI T0: 2 Pass
        self.assertEqual(summary["tests"]["sai"]["t0"]["passed"], 2)
        
        # Agent HW T0: 2 Pass
        self.assertEqual(summary["tests"]["agent_hw"]["t0"]["passed"], 2)

        # Link T0: 2 Pass
        self.assertEqual(summary["tests"]["link"]["t0"]["passed"], 2)

        # ExitEVT (Link EV): 2 Pass
        self.assertEqual(summary["tests"]["link"]["ev"]["passed"], 2)
        
        # Global: 8 Pass (2+2+2+2), 0 Fail
        self.assertEqual(summary["all_tests"]["passed"], 8)
        self.assertEqual(summary["all_tests"]["failed"], 0)

import io
if __name__ == '__main__':
    unittest.main()
