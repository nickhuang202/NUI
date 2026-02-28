#!/usr/bin/env python3
"""Tests for run_scheduled_profile.py."""

import os
import sys
import unittest
import tempfile
import importlib.util
from datetime import datetime
from unittest.mock import patch


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(ROOT_DIR, 'run_scheduled_profile.py')


def load_scheduler_module():
    spec = importlib.util.spec_from_file_location('run_scheduled_profile', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRunScheduledProfileDryRun(unittest.TestCase):
    """Validate dry-run mode and scheduling execution wiring."""

    @classmethod
    def setUpClass(cls):
        cls.scheduler = load_scheduler_module()

    def test_run_test_item_dry_run_does_not_spawn_process(self):
        test_item = {'title': 'Env_Test'}
        procedure = {
            'script': 'run_all_test.sh',
            'bin': 'demo.tar.zst',
            'topology': 'default',
            'test_items': {'evt_exit': True}
        }

        with patch.object(self.scheduler, 'load_test_procedure', return_value=procedure):
            with patch('os.path.exists', return_value=True):
                with patch.object(self.scheduler.subprocess, 'Popen') as mock_popen:
                    ok = self.scheduler.run_test_item(test_item, 'P1', dry_run=True)

        self.assertTrue(ok)
        mock_popen.assert_not_called()

    def test_main_dry_run_skips_sleep_and_executes_virtual_dispatch(self):
        profile_data = {
            'tests': [
                {
                    'title': 'Env_Test',
                    'startOffsetMinutes': 60,
                    'durationMinutes': 30
                }
            ]
        }

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 1, 1, 0, 0, 0, tzinfo=tz)

        with patch.object(self.scheduler, 'datetime', FixedDateTime):
            with patch.object(self.scheduler, 'load_profile', return_value=profile_data):
                with patch.object(self.scheduler, 'run_test_item', return_value=True) as mock_run_test:
                    with patch.object(self.scheduler.time, 'sleep') as mock_sleep:
                        with patch.object(sys, 'argv', ['run_scheduled_profile.py', 'P1', '--dry-run']):
                            self.scheduler.main()

        mock_sleep.assert_not_called()
        mock_run_test.assert_called_once()
        call_args = mock_run_test.call_args
        self.assertEqual(call_args[0][0]['title'], 'Env_Test')
        self.assertEqual(call_args[0][1], 'P1')
        self.assertTrue(call_args[1]['dry_run'])

    def test_build_test_items_string_flat_format(self):
        test_items = {
            'sai_t0': True,
            'sai_t1': False,
            'agent_t2': True,
            'link_t1': True,
            'evt_exit': True
        }

        result = self.scheduler.build_test_items_string(test_items)
        self.assertEqual(result, 'SAI_T0,AGENT_T2,LINK_T1,EVT_EXIT')

    def test_main_non_dry_run_calls_sleep_and_executes(self):
        profile_data = {
            'tests': [
                {
                    'title': 'Env_Test',
                    'startOffsetMinutes': 1,
                    'durationMinutes': 30
                }
            ]
        }

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 1, 1, 0, 0, 0, tzinfo=tz)

        with patch.object(self.scheduler, 'datetime', FixedDateTime):
            with patch.object(self.scheduler, 'load_profile', return_value=profile_data):
                with patch.object(self.scheduler, 'run_test_item', return_value=True) as mock_run_test:
                    with patch.object(self.scheduler.time, 'sleep') as mock_sleep:
                        with patch.object(sys, 'argv', ['run_scheduled_profile.py', 'P1']):
                            self.scheduler.main()

        mock_sleep.assert_called_once_with(60.0)
        mock_run_test.assert_called_once()
        call_args = mock_run_test.call_args
        self.assertEqual(call_args[0][0]['title'], 'Env_Test')
        self.assertEqual(call_args[0][1], 'P1')
        self.assertFalse(call_args[1]['dry_run'])

    def test_main_non_dry_run_past_schedule_no_sleep_but_executes(self):
        profile_data = {
            'tests': [
                {
                    'title': 'Env_Test',
                    'startOffsetMinutes': 1,
                    'durationMinutes': 30
                }
            ]
        }

        class FixedDateTime(datetime):
            call_count = 0

            @classmethod
            def now(cls, tz=None):
                # 1st now(): intended_time calc baseline -> 00:00
                # 2nd now(): wait calc baseline -> 00:02 (already past 00:01)
                if cls.call_count == 0:
                    value = cls(2026, 1, 1, 0, 0, 0, tzinfo=tz)
                else:
                    value = cls(2026, 1, 1, 0, 2, 0, tzinfo=tz)
                cls.call_count += 1
                return value

        with patch.object(self.scheduler, 'datetime', FixedDateTime):
            with patch.object(self.scheduler, 'load_profile', return_value=profile_data):
                with patch.object(self.scheduler, 'run_test_item', return_value=True) as mock_run_test:
                    with patch.object(self.scheduler.time, 'sleep') as mock_sleep:
                        with patch.object(sys, 'argv', ['run_scheduled_profile.py', 'P1']):
                            self.scheduler.main()

        mock_sleep.assert_not_called()
        mock_run_test.assert_called_once()
        call_args = mock_run_test.call_args
        self.assertEqual(call_args[0][0]['title'], 'Env_Test')
        self.assertEqual(call_args[0][1], 'P1')
        self.assertFalse(call_args[1]['dry_run'])

    def test_write_execution_status_persists_profile_and_title(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            status_file = os.path.join(tmpdir, 'status.json')
            with patch.object(self.scheduler, 'EXECUTION_STATUS_FILE', status_file):
                self.scheduler.write_execution_status({
                    'running': True,
                    'profile_name': 'P1',
                    'current_test_title': 'Env_Test',
                    'pid': 12345
                })

            with open(status_file, 'r', encoding='utf-8') as f:
                payload = self.scheduler.json.load(f)

        self.assertTrue(payload['running'])
        self.assertEqual(payload['profile_name'], 'P1')
        self.assertEqual(payload['current_test_title'], 'Env_Test')
        self.assertEqual(payload['pid'], 12345)
        self.assertIn('updated_at', payload)

    def test_load_profile_supports_slash_in_profile_name_via_sanitized_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_file = os.path.join(tmpdir, 'Profile 2282026.json')
            with open(profile_file, 'w', encoding='utf-8') as f:
                self.scheduler.json.dump({'profile_name': 'Profile 2/28/2026', 'tests': []}, f)

            with patch.object(self.scheduler, 'SCHEDULES_DIR', tmpdir):
                data = self.scheduler.load_profile('Profile 2/28/2026')

        self.assertIsNotNone(data)
        self.assertEqual(data['profile_name'], 'Profile 2/28/2026')


if __name__ == '__main__':
    unittest.main()
