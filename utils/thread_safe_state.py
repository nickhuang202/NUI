"""
Thread-safe state management for shared application state.

This module provides thread-safe wrappers for mutable state that can be
accessed by multiple request threads concurrently.
"""

import threading
from typing import Any, Dict, Optional
from datetime import datetime


class ThreadSafeDict:
    """Thread-safe dictionary wrapper using a lock."""
    
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        """Initialize with optional initial data."""
        self._lock = threading.RLock()  # Reentrant lock
        self._data = initial_data.copy() if initial_data else {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the dictionary."""
        with self._lock:
            return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the dictionary."""
        with self._lock:
            self._data[key] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple key-value pairs atomically."""
        with self._lock:
            self._data.update(updates)
    
    def delete(self, key: str) -> None:
        """Delete a key from the dictionary."""
        with self._lock:
            self._data.pop(key, None)
    
    def keys(self):
        """Return a copy of all keys."""
        with self._lock:
            return list(self._data.keys())
    
    def values(self):
        """Return a copy of all values."""
        with self._lock:
            return list(self._data.values())
    
    def items(self):
        """Return a copy of all items."""
        with self._lock:
            return list(self._data.items())
    
    def copy(self) -> Dict[str, Any]:
        """Return a copy of the entire dictionary."""
        with self._lock:
            return self._data.copy()
    
    def clear(self) -> None:
        """Clear all data."""
        with self._lock:
            self._data.clear()
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        with self._lock:
            return key in self._data
    
    def __len__(self) -> int:
        """Return the number of items."""
        with self._lock:
            return len(self._data)
    
    def __repr__(self) -> str:
        """String representation."""
        with self._lock:
            return f"ThreadSafeDict({self._data})"


class ServiceStatusManager:
    """Thread-safe manager for service status monitoring."""
    
    def __init__(self):
        """Initialize service status with default values."""
        self._state = ThreadSafeDict({
            'qsfp_service': False,
            'sai_mono_link_test-sai_impl': False,
            'sai_mono_link_test-sai_impl_cmd': None,
            'sai_mono_link_test-sai_impl_filter': None,
            'sai_mono_link_test-sai_impl_message': None
        })
    
    def get_status(self, service: str) -> Any:
        """Get the status of a service."""
        return self._state.get(service)
    
    def set_status(self, service: str, status: Any) -> None:
        """Set the status of a service."""
        self._state.set(service, status)
    
    def update_status(self, updates: Dict[str, Any]) -> None:
        """Update multiple service statuses atomically."""
        self._state.update(updates)
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get a copy of all service statuses."""
        return self._state.copy()
    
    def is_service_running(self, service: str) -> bool:
        """Check if a service is running."""
        return bool(self._state.get(service, False))


class TestExecutionManager:
    """Thread-safe manager for test execution state."""
    
    def __init__(self):
        """Initialize test execution state."""
        self._state = ThreadSafeDict({
            'running': False,
            'script': None,
            'bin': None,
            'topology': None,
            'topology_file': None,
            'pid': None,
            'start_time': None
        })
    
    def is_running(self) -> bool:
        """Check if a test is currently running."""
        return bool(self._state.get('running', False))
    
    def get_pid(self) -> Optional[int]:
        """Get the PID of the running test."""
        return self._state.get('pid')
    
    def get_script(self) -> Optional[str]:
        """Get the script name."""
        return self._state.get('script')
    
    def get_bin(self) -> Optional[str]:
        """Get the binary name."""
        return self._state.get('bin')
    
    def get_topology(self) -> Optional[str]:
        """Get the topology name."""
        return self._state.get('topology')
    
    def get_topology_file(self) -> Optional[str]:
        """Get the topology file path."""
        return self._state.get('topology_file')
    
    def get_start_time(self) -> Optional[str]:
        """Get the test start time."""
        return self._state.get('start_time')
    
    def start_test(self, script: str, pid: int, **kwargs) -> None:
        """Start a new test execution."""
        updates = {
            'running': True,
            'script': script,
            'pid': pid,
            'start_time': datetime.now().isoformat(),
            **kwargs
        }
        self._state.update(updates)
    
    def stop_test(self) -> None:
        """Stop the current test execution."""
        self._state.update({
            'running': False,
            'pid': None
        })
    
    def reset(self) -> None:
        """Reset all test execution state."""
        self._state.update({
            'running': False,
            'script': None,
            'bin': None,
            'topology': None,
            'topology_file': None,
            'pid': None,
            'start_time': None
        })
    
    def get_state(self) -> Dict[str, Any]:
        """Get a copy of the entire test execution state."""
        return self._state.copy()
    
    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update test execution state with multiple values."""
        self._state.update(updates)


# Global singleton instances
_service_status_manager = ServiceStatusManager()
_test_execution_manager = TestExecutionManager()


def get_service_status_manager() -> ServiceStatusManager:
    """Get the global service status manager instance."""
    return _service_status_manager


def get_test_execution_manager() -> TestExecutionManager:
    """Get the global test execution manager instance."""
    return _test_execution_manager
