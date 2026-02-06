#!/usr/bin/env python3
"""
Unit tests for organize_test_reports.py

Tests the parsing, categorization, and organization logic.
"""

import unittest
import os
import sys
import tempfile
import shutil
import tarfile
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from organize_test_reports import (
    parse_archive_info,
    get_file_category,
    extract_and_organize_archive,
    organize_test_reports
)


class TestParseArchiveInfo(unittest.TestCase):
    """Test archive filename parsing"""
    
    def test_parse_sai_t0_archive(self):
        """Test parsing SAI T0 archive filename"""
        result = parse_archive_info('SAI_t0_WEDGE800BACT_2026-01-22.tar.gz')
        self.assertEqual(result['category'], 'SAI_Test')
        self.assertEqual(result['level'], 'T0')
        self.assertEqual(result['date'], '2026-01-22')
        self.assertIsNone(result['topology'])
    
    def test_parse_sai_t1_archive(self):
        """Test parsing SAI T1 archive filename"""
        result = parse_archive_info('SAI_t1_WEDGE800BACT_2026-01-22.tar.gz')
        self.assertEqual(result['category'], 'SAI_Test')
        self.assertEqual(result['level'], 'T1')
        self.assertEqual(result['date'], '2026-01-22')
    
    def test_parse_sai_t2_archive(self):
        """Test parsing SAI T2 archive filename"""
        result = parse_archive_info('SAI_t2_WEDGE800BACT_2026-01-22.tar.gz')
        self.assertEqual(result['category'], 'SAI_Test')
        self.assertEqual(result['level'], 'T2')
        self.assertEqual(result['date'], '2026-01-22')
    
    def test_parse_agent_hw_t0_archive(self):
        """Test parsing Agent HW T0 archive filename"""
        result = parse_archive_info('AGENT_HW_t0_WEDGE800BACT_2026-01-22.tar.gz')
        self.assertEqual(result['category'], 'Agent_HW_test')
        self.assertEqual(result['level'], 'T0')
        self.assertEqual(result['date'], '2026-01-22')
    
    def test_parse_agent_hw_t2_archive(self):
        """Test parsing Agent HW T2 archive filename"""
        result = parse_archive_info('AGENT_HW_t2_WEDGE800BACT_2026-01-22.tar.gz')
        self.assertEqual(result['category'], 'Agent_HW_test')
        self.assertEqual(result['level'], 'T2')
        self.assertEqual(result['date'], '2026-01-22')
    
    def test_parse_link_t0_optic_one(self):
        """Test parsing Link T0 optic_one archive"""
        result = parse_archive_info('LINK_t0_WEDGE800BACT_optic_one_2026-01-22.tar.gz')
        self.assertEqual(result['category'], 'Link_Test')
        self.assertEqual(result['level'], 'T0')
        self.assertEqual(result['topology'], 'optic_one')
        self.assertEqual(result['date'], '2026-01-22')
    
    def test_parse_link_t0_optic_two(self):
        """Test parsing Link T0 optic_two archive"""
        result = parse_archive_info('LINK_t0_WEDGE800BACT_optic_two_2026-01-22.tar.gz')
        self.assertEqual(result['category'], 'Link_Test')
        self.assertEqual(result['level'], 'T0')
        self.assertEqual(result['topology'], 'optic_two')
        self.assertEqual(result['date'], '2026-01-22')
    
    def test_parse_link_t0_copper(self):
        """Test parsing Link T0 copper archive"""
        result = parse_archive_info('LINK_t0_WEDGE800BACT_copper_2026-01-22.tar.gz')
        self.assertEqual(result['category'], 'Link_Test')
        self.assertEqual(result['level'], 'T0')
        self.assertEqual(result['topology'], 'copper')
        self.assertEqual(result['date'], '2026-01-22')
    
    def test_parse_exitevt_optic_one(self):
        """Test parsing ExitEVT optic_one archive"""
        result = parse_archive_info('ExitEVT_WEDGE800BACT_optic_one_2026-01-22.tar.gz')
        self.assertEqual(result['category'], 'ExitEVT')
        self.assertEqual(result['level'], 'full_EVT+')
        self.assertEqual(result['topology'], 'optic_one')
        self.assertEqual(result['date'], '2026-01-22')
    
    def test_parse_exitevt_optic_two(self):
        """Test parsing ExitEVT optic_two archive"""
        result = parse_archive_info('ExitEVT_WEDGE800BACT_optic_two_2026-01-22.tar.gz')
        self.assertEqual(result['category'], 'ExitEVT')
        self.assertEqual(result['level'], 'full_EVT+')
        self.assertEqual(result['topology'], 'optic_two')
        self.assertEqual(result['date'], '2026-01-22')
    
    def test_parse_exitevt_copper(self):
        """Test parsing ExitEVT copper archive"""
        result = parse_archive_info('ExitEVT_WEDGE800BACT_copper_2026-01-22.tar.gz')
        self.assertEqual(result['category'], 'ExitEVT')
        self.assertEqual(result['level'], 'full_EVT+')
        self.assertEqual(result['topology'], 'copper')
        self.assertEqual(result['date'], '2026-01-22')
    
    def test_parse_unknown_archive(self):
        """Test parsing unknown archive type"""
        result = parse_archive_info('UNKNOWN_test_2026-01-22.tar.gz')
        self.assertIsNone(result['category'])
        self.assertIsNone(result['level'])
        self.assertEqual(result['date'], '2026-01-22')
    
    def test_parse_archive_without_date(self):
        """Test parsing archive without date"""
        result = parse_archive_info('SAI_t0_WEDGE800BACT.tar.gz')
        self.assertEqual(result['category'], 'SAI_Test')
        self.assertEqual(result['level'], 'T0')
        self.assertIsNone(result['date'])
    
    def test_parse_case_insensitive(self):
        """Test that parsing is case insensitive"""
        result1 = parse_archive_info('sai_t0_wedge800bact_2026-01-22.tar.gz')
        result2 = parse_archive_info('SAI_T0_WEDGE800BACT_2026-01-22.tar.gz')
        self.assertEqual(result1['category'], result2['category'])
        self.assertEqual(result1['level'], result2['level'])


class TestGetFileCategory(unittest.TestCase):
    """Test file categorization"""
    
    def test_version_file(self):
        """Test Version_Info.txt categorization"""
        self.assertEqual(get_file_category('Version_Info.txt'), 'version')
    
    def test_fruid_config_files(self):
        """Test fruid*.json files"""
        self.assertEqual(get_file_category('fruid.json'), 'config')
        self.assertEqual(get_file_category('fruidInfo.json'), 'config')
        self.assertEqual(get_file_category('FRUID_data.json'), 'config')
    
    def test_platform_mapping_config(self):
        """Test platform_mapping.json"""
        self.assertEqual(get_file_category('platform_mapping.json'), 'config')
        self.assertEqual(get_file_category('wedge_platform_mapping.json'), 'config')
    
    def test_materialized_json_config(self):
        """Test materialized_JSON files"""
        self.assertEqual(get_file_category('wedge800bact.materialized_JSON'), 'config')
        self.assertEqual(get_file_category('config.materialized_json'), 'config')
    
    def test_log_tar_gz_files(self):
        """Test .log.tar.gz files"""
        self.assertEqual(get_file_category('test.log.tar.gz'), 'log')
        self.assertEqual(get_file_category('agent_test.log.tar.gz'), 'log')
    
    def test_log_files(self):
        """Test .log files"""
        self.assertEqual(get_file_category('test.log'), 'log')
        self.assertEqual(get_file_category('agent_hw_test.log'), 'log')
    
    def test_csv_files(self):
        """Test .csv files"""
        self.assertEqual(get_file_category('results.csv'), 'csv')
        self.assertEqual(get_file_category('test_results.csv'), 'csv')
    
    def test_xlsx_files(self):
        """Test .xlsx files"""
        self.assertEqual(get_file_category('results.xlsx'), 'xlsx')
        self.assertEqual(get_file_category('test_report.xlsx'), 'xlsx')
    
    def test_fboss2_show_files(self):
        """Test fboss2_show*.txt files"""
        self.assertEqual(get_file_category('fboss2_show_port.txt'), 'log')
        self.assertEqual(get_file_category('fboss2_show_interface.txt'), 'log')
    
    def test_unknown_files(self):
        """Test unknown file types"""
        self.assertIsNone(get_file_category('random.txt'))
        self.assertIsNone(get_file_category('data.bin'))
        self.assertIsNone(get_file_category('script.sh'))
    
    def test_case_insensitive_categorization(self):
        """Test case insensitive file categorization"""
        self.assertEqual(get_file_category('TEST.LOG'), 'log')
        self.assertEqual(get_file_category('Results.CSV'), 'csv')
        self.assertEqual(get_file_category('FRUID.JSON'), 'config')


class TestExtractAndOrganize(unittest.TestCase):
    """Test archive extraction and organization"""
    
    def setUp(self):
        """Create temporary directories for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.temp_dir, 'output')
        self.archive_dir = os.path.join(self.temp_dir, 'archives')
        os.makedirs(self.archive_dir)
    
    def tearDown(self):
        """Clean up temporary directories"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_archive(self, archive_name, files):
        """Helper to create a test tar.gz archive with specified files"""
        archive_path = os.path.join(self.archive_dir, archive_name)
        
        # Create temporary directory for archive contents
        temp_content_dir = os.path.join(self.temp_dir, 'content')
        os.makedirs(temp_content_dir, exist_ok=True)
        
        # Create files
        for filename, content in files.items():
            filepath = os.path.join(temp_content_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(content)
        
        # Create tar.gz archive
        with tarfile.open(archive_path, 'w:gz') as tar:
            for filename in files.keys():
                filepath = os.path.join(temp_content_dir, filename)
                tar.add(filepath, arcname=filename)
        
        # Clean up temp content
        shutil.rmtree(temp_content_dir)
        
        return archive_path
    
    def test_extract_sai_t0_archive(self):
        """Test extracting and organizing SAI T0 archive"""
        files = {
            'Version_Info.txt': 'Version 1.0',
            'fruid.json': '{"test": "config"}',
            'platform_mapping.json': '{"mapping": "data"}',
            'test.log.tar.gz': 'log content',
            'results.csv': 'test,result\ntest1,pass',
            'report.xlsx': 'excel data'
        }
        
        archive_path = self.create_test_archive('SAI_t0_WEDGE800BACT_2026-01-22.tar.gz', files)
        extract_and_organize_archive(archive_path, self.output_dir)
        
        # Verify directory structure
        date_dir = os.path.join(self.output_dir, 'T0', '20260122')
        category_dir = os.path.join(date_dir, 'SAI_Test')
        
        self.assertTrue(os.path.exists(os.path.join(date_dir, 'Version_Info.txt')))
        self.assertTrue(os.path.exists(os.path.join(category_dir, 'Configs', 'fruid.json')))
        self.assertTrue(os.path.exists(os.path.join(category_dir, 'Configs', 'platform_mapping.json')))
        self.assertTrue(os.path.exists(os.path.join(category_dir, 'Logs', 'test.log.tar.gz')))
        self.assertTrue(os.path.exists(os.path.join(category_dir, 'results.csv')))
        self.assertTrue(os.path.exists(os.path.join(category_dir, 'report.xlsx')))
    
    def test_extract_agent_hw_t2_archive(self):
        """Test extracting and organizing Agent HW T2 archive"""
        files = {
            'Version_Info.txt': 'Version 2.0',
            'fruidInfo.json': '{"hw": "info"}',
            'test.log': 'agent hw log',
            'hw_results.csv': 'test,status\ntest1,pass'
        }
        
        archive_path = self.create_test_archive('AGENT_HW_t2_WEDGE800BACT_2026-01-22.tar.gz', files)
        extract_and_organize_archive(archive_path, self.output_dir)
        
        # Verify directory structure
        date_dir = os.path.join(self.output_dir, 'T2', '20260122')
        category_dir = os.path.join(date_dir, 'Agent_HW_test')
        
        self.assertTrue(os.path.exists(os.path.join(date_dir, 'Version_Info.txt')))
        self.assertTrue(os.path.exists(os.path.join(category_dir, 'Configs', 'fruidInfo.json')))
        self.assertTrue(os.path.exists(os.path.join(category_dir, 'Logs', 'test.log')))
        self.assertTrue(os.path.exists(os.path.join(category_dir, 'hw_results.csv')))
    
    def test_extract_link_t0_optic_one_archive(self):
        """Test extracting and organizing Link T0 optic_one archive"""
        files = {
            'Version_Info.txt': 'Version 3.0',
            'wedge800bact.materialized_JSON': '{"switch": "config"}',
            'qsfp_test_configs/qsfp.materialized_JSON': '{"qsfp": "config"}',
            'link_test.log.tar.gz': 'link log',
            'fboss2_show_port.txt': 'port status',
            'link_results.csv': 'port,status\nport1,up',
            'link_report.xlsx': 'excel report'
        }
        
        archive_path = self.create_test_archive('LINK_t0_WEDGE800BACT_optic_one_2026-01-22.tar.gz', files)
        extract_and_organize_archive(archive_path, self.output_dir)
        
        # Verify directory structure
        date_dir = os.path.join(self.output_dir, 'T0', '20260122')
        link_dir = os.path.join(date_dir, 'Link_Test')
        topology_dir = os.path.join(link_dir, 'optic_one')
        
        self.assertTrue(os.path.exists(os.path.join(date_dir, 'Version_Info.txt')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'Configs', 'wedge800bact.materialized_JSON')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'Configs', 'qsfp_test_configs', 'qsfp.materialized_JSON')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'Logs', 'link_test.log.tar.gz')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'Logs', 'fboss2_show_port.txt')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'link_results.csv')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'link_report.xlsx')))
    
    def test_extract_exitevt_optic_two_archive(self):
        """Test extracting and organizing ExitEVT optic_two archive"""
        files = {
            'Version_Info.txt': 'Version 4.0',
            'fruid.json': '{"evt": "data"}',
            'platform_mapping.json': '{"platform": "map"}',
            'wedge.materialized_JSON': '{"config": "data"}',
            'qsfp_test_configs/optic.materialized_JSON': '{"optic": "config"}',
            'evt_test.log.tar.gz': 'evt log',
            'fboss2_show_interface.txt': 'interface info',
            'evt_results.csv': 'test,result\nevt1,pass',
            'evt_report.xlsx': 'evt excel'
        }
        
        archive_path = self.create_test_archive('ExitEVT_WEDGE800BACT_optic_two_2026-01-22.tar.gz', files)
        extract_and_organize_archive(archive_path, self.output_dir)
        
        # Verify directory structure
        base_dir = os.path.join(self.output_dir, 'full_EVT+')
        date_dir = os.path.join(base_dir, '20260122')
        topology_dir = os.path.join(date_dir, 'optic_two')
        
        self.assertTrue(os.path.exists(os.path.join(date_dir, 'Version_Info.txt')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'Configs', 'fruid.json')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'Configs', 'platform_mapping.json')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'Configs', 'wedge.materialized_JSON')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'Configs', 'qsfp_test_configs', 'optic.materialized_JSON')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'Logs', 'evt_test.log.tar.gz')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'evt_results.csv')))
        self.assertTrue(os.path.exists(os.path.join(topology_dir, 'evt_report.xlsx')))


class TestOrganizeTestReports(unittest.TestCase):
    """Test the main organize_test_reports function"""
    
    def setUp(self):
        """Create temporary directories for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.temp_dir, 'source')
        self.output_dir = os.path.join(self.temp_dir, 'output')
        os.makedirs(self.source_dir)
    
    def tearDown(self):
        """Clean up temporary directories"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_archive(self, archive_name, files):
        """Helper to create a test tar.gz archive"""
        archive_path = os.path.join(self.source_dir, archive_name)
        
        temp_content_dir = os.path.join(self.temp_dir, 'content_' + archive_name)
        os.makedirs(temp_content_dir, exist_ok=True)
        
        for filename, content in files.items():
            filepath = os.path.join(temp_content_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(content)
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            for filename in files.keys():
                filepath = os.path.join(temp_content_dir, filename)
                tar.add(filepath, arcname=filename)
        
        shutil.rmtree(temp_content_dir)
        return archive_path
    
    def test_organize_multiple_archives(self):
        """Test organizing multiple archives at once"""
        # Create multiple test archives
        self.create_test_archive('SAI_t0_WEDGE800BACT_2026-01-22.tar.gz', {
            'Version_Info.txt': 'SAI T0 Version',
            'sai_test.log': 'sai log',
            'results.csv': 'test,result'
        })
        
        self.create_test_archive('AGENT_HW_t2_WEDGE800BACT_2026-01-22.tar.gz', {
            'Version_Info.txt': 'Agent HW Version',
            'hw_test.log.tar.gz': 'hw log',
            'hw_results.csv': 'test,status'
        })
        
        self.create_test_archive('ExitEVT_WEDGE800BACT_optic_one_2026-01-22.tar.gz', {
            'Version_Info.txt': 'EVT Version',
            'evt_test.log': 'evt log',
            'evt.csv': 'result'
        })
        
        # Run organize function
        organize_test_reports(self.source_dir, self.output_dir)
        
        # Verify all archives were processed
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, 'T0', '20260122', 'SAI_Test')))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, 'T2', '20260122', 'Agent_HW_test')))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, 'full_EVT+', '20260122', 'optic_one')))
    
    def test_organize_empty_directory(self):
        """Test organizing when source directory is empty"""
        # Should not crash on empty directory
        organize_test_reports(self.source_dir, self.output_dir)
        # Output directory might not be created if no archives found
    
    def test_organize_nonexistent_directory(self):
        """Test organizing with non-existent source directory"""
        non_existent = os.path.join(self.temp_dir, 'nonexistent')
        # Should handle gracefully
        organize_test_reports(non_existent, self.output_dir)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
