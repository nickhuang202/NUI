"""Tests for schedule profile auto-start behavior on save."""

import os
import tempfile
from unittest.mock import patch

import pytest

from app import app as main_app


@pytest.fixture
def client():
    main_app.config['TESTING'] = True
    with main_app.test_client() as client:
        yield client


@patch('routes.schedule._start_today_runner', return_value=(True, 99999, 'started'))
@patch('routes.schedule.cron_service.sync_profile', return_value=True)
def test_save_profile_daily_auto_starts_runner(mock_sync, mock_start_runner, client):
    payload = {
        'profile_name': 'AUTO_START_DAILY',
        'cron_rule': {
            'type': 'daily',
            'preview': 'Every Day (Daily)'
        },
        'tests': [
            {
                'title': 'Env_Test',
                'type': 'cron',
                'startOffsetMinutes': 600,
                'durationMinutes': 60
            }
        ]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('routes.schedule.SCHEDULES_DIR', tmpdir):
            response = client.post('/api/schedule/profiles', json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['today_runner_started'] is True
    assert data['today_runner_pid'] == 99999
    assert data['today_runner_reason'] == 'started'
    mock_sync.assert_called_once()
    mock_start_runner.assert_called_once_with('AUTO_START_DAILY')


@patch('routes.schedule._start_today_runner')
@patch('routes.schedule.cron_service.sync_profile', return_value=True)
def test_save_profile_single_does_not_auto_start_runner(mock_sync, mock_start_runner, client):
    payload = {
        'profile_name': 'SINGLE_RULE_PROFILE',
        'cron_rule': {
            'type': 'single',
            'preview': 'Single Run (Today Only)'
        },
        'tests': [
            {
                'title': 'Env_Test',
                'type': 'cron',
                'startOffsetMinutes': 600,
                'durationMinutes': 60
            }
        ]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('routes.schedule.SCHEDULES_DIR', tmpdir):
            response = client.post('/api/schedule/profiles', json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['today_runner_started'] is False
    assert data['today_runner_pid'] is None
    assert data['today_runner_reason'] == 'not-repeating-rule'
    mock_sync.assert_called_once()
    mock_start_runner.assert_not_called()
