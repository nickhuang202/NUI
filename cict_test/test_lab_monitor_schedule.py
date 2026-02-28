"""Tests for DUT schedule settings in lab_monitor module."""

import os
import tempfile
from unittest.mock import patch

import lab_monitor


def _seed_config(tmpdir):
    config = {
        'labs': [
            {
                'id': 'lab1',
                'name': 'Lab1',
                'platforms': [
                    {
                        'id': 'pf1',
                        'name': 'Platform1',
                        'duts': [
                            {
                                'id': 'dut1',
                                'name': 'DUT-1',
                                'ip_address': '172.17.9.199'
                            }
                        ]
                    }
                ]
            }
        ],
        'version': '1.0'
    }
    config_path = os.path.join(tmpdir, 'lab_config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        import json
        json.dump(config, f)


def test_set_and_get_dut_schedule():
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_config(tmpdir)
        with patch('lab_monitor.os.getcwd', return_value=tmpdir):
            set_result = lab_monitor.set_dut_schedule('dut1', True, 'SAI_T0_TEST')
            assert set_result['success'] is True
            assert set_result['schedule']['enabled'] is True
            assert set_result['schedule']['profile_name'] == 'SAI_T0_TEST'

            get_result = lab_monitor.get_dut_schedule('dut1')
            assert get_result['success'] is True
            assert get_result['schedule']['enabled'] is True
            assert get_result['schedule']['profile_name'] == 'SAI_T0_TEST'


def test_get_all_dut_schedules_returns_map():
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_config(tmpdir)
        with patch('lab_monitor.os.getcwd', return_value=tmpdir):
            lab_monitor.set_dut_schedule('dut1', True, 'ENV_TEST_PROFILE')
            all_result = lab_monitor.get_all_dut_schedules()

            assert all_result['success'] is True
            assert 'dut1' in all_result['schedules']
            assert all_result['schedules']['dut1']['enabled'] is True
            assert all_result['schedules']['dut1']['profile_name'] == 'ENV_TEST_PROFILE'


def test_disable_dut_schedule_clears_profile():
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_config(tmpdir)
        with patch('lab_monitor.os.getcwd', return_value=tmpdir):
            lab_monitor.set_dut_schedule('dut1', True, 'ENV_TEST_PROFILE')
            disable_result = lab_monitor.set_dut_schedule('dut1', False, 'ENV_TEST_PROFILE')

            assert disable_result['success'] is True
            assert disable_result['schedule']['enabled'] is False
            assert disable_result['schedule']['profile_name'] == ''
