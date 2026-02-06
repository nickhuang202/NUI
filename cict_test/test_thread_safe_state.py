"""
Tests for thread-safe state management utilities.
"""

import pytest
import threading
import time
from utils.thread_safe_state import (
    ThreadSafeDict,
    ServiceStatusManager,
    TestExecutionManager,
    get_service_status_manager,
    get_test_execution_manager
)


class TestThreadSafeDict:
    """Test the ThreadSafeDict implementation."""
    
    def test_basic_operations(self):
        """Test basic get/set/delete operations."""
        d = ThreadSafeDict()
        
        # Test set and get
        d.set('key1', 'value1')
        assert d.get('key1') == 'value1'
        
        # Test default value
        assert d.get('nonexistent', 'default') == 'default'
        
        # Test delete
        d.delete('key1')
        assert d.get('key1') is None
    
    def test_update_multiple(self):
        """Test updating multiple keys atomically."""
        d = ThreadSafeDict({'a': 1, 'b': 2})
        d.update({'b': 3, 'c': 4})
        
        assert d.get('a') == 1
        assert d.get('b') == 3
        assert d.get('c') == 4
    
    def test_copy(self):
        """Test copying the dictionary."""
        d = ThreadSafeDict({'key1': 'value1', 'key2': 'value2'})
        copy = d.copy()
        
        assert copy == {'key1': 'value1', 'key2': 'value2'}
        
        # Modify copy shouldn't affect original
        copy['key1'] = 'modified'
        assert d.get('key1') == 'value1'
    
    def test_contains(self):
        """Test __contains__ operator."""
        d = ThreadSafeDict({'key1': 'value1'})
        assert 'key1' in d
        assert 'key2' not in d
    
    def test_len(self):
        """Test __len__ operator."""
        d = ThreadSafeDict()
        assert len(d) == 0
        
        d.set('key1', 'value1')
        d.set('key2', 'value2')
        assert len(d) == 2
    
    def test_keys_values_items(self):
        """Test keys, values, and items methods."""
        d = ThreadSafeDict({'a': 1, 'b': 2})
        
        assert set(d.keys()) == {'a', 'b'}
        assert set(d.values()) == {1, 2}
        assert set(d.items()) == {('a', 1), ('b', 2)}
    
    def test_clear(self):
        """Test clearing all data."""
        d = ThreadSafeDict({'a': 1, 'b': 2})
        d.clear()
        assert len(d) == 0
        assert d.copy() == {}
    
    def test_concurrent_access(self):
        """Test thread-safety with concurrent access."""
        d = ThreadSafeDict()
        errors = []
        
        def writer(thread_id):
            """Write values in a loop."""
            try:
                for i in range(100):
                    d.set(f'key_{thread_id}_{i}', i)
            except Exception as e:
                errors.append(e)
        
        def reader(thread_id):
            """Read values in a loop."""
            try:
                for i in range(100):
                    d.get(f'key_{thread_id}_{i}', 0)
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=writer, args=(i,)))
            threads.append(threading.Thread(target=reader, args=(i,)))
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # No errors should occur
        assert len(errors) == 0
        # Should have 500 keys (5 threads * 100 keys each)
        assert len(d) == 500


class TestServiceStatusManager:
    """Test the ServiceStatusManager implementation."""
    
    def test_initialization(self):
        """Test manager initialization with default values."""
        manager = ServiceStatusManager()
        
        assert manager.get_status('qsfp_service') is False
        assert manager.get_status('sai_mono_link_test-sai_impl') is False
        assert manager.get_status('sai_mono_link_test-sai_impl_cmd') is None
    
    def test_set_status(self):
        """Test setting individual service status."""
        manager = ServiceStatusManager()
        manager.set_status('qsfp_service', True)
        
        assert manager.is_service_running('qsfp_service') is True
        assert manager.get_status('qsfp_service') is True
    
    def test_update_status(self):
        """Test updating multiple statuses atomically."""
        manager = ServiceStatusManager()
        manager.update_status({
            'qsfp_service': True,
            'sai_mono_link_test-sai_impl': True,
            'sai_mono_link_test-sai_impl_cmd': 'test command'
        })
        
        assert manager.is_service_running('qsfp_service') is True
        assert manager.is_service_running('sai_mono_link_test-sai_impl') is True
        assert manager.get_status('sai_mono_link_test-sai_impl_cmd') == 'test command'
    
    def test_get_all_status(self):
        """Test getting all statuses as a dict."""
        manager = ServiceStatusManager()
        manager.set_status('qsfp_service', True)
        
        all_status = manager.get_all_status()
        assert isinstance(all_status, dict)
        assert all_status['qsfp_service'] is True
        
        # Modifying returned dict shouldn't affect manager
        all_status['qsfp_service'] = False
        assert manager.get_status('qsfp_service') is True


class TestTestExecutionManager:
    """Test the TestExecutionManager implementation."""
    
    def test_initialization(self):
        """Test manager initialization."""
        manager = TestExecutionManager()
        
        assert manager.is_running() is False
        assert manager.get_pid() is None
        assert manager.get_script() is None
    
    def test_start_test(self):
        """Test starting a test execution."""
        manager = TestExecutionManager()
        manager.start_test(
            script='test_script.sh',
            pid=12345,
            bin='test_binary',
            topology='test_topology'
        )
        
        assert manager.is_running() is True
        assert manager.get_pid() == 12345
        assert manager.get_script() == 'test_script.sh'
        assert manager.get_bin() == 'test_binary'
        assert manager.get_topology() == 'test_topology'
        assert manager.get_start_time() is not None
    
    def test_stop_test(self):
        """Test stopping a test execution."""
        manager = TestExecutionManager()
        manager.start_test(script='test.sh', pid=123)
        
        assert manager.is_running() is True
        
        manager.stop_test()
        assert manager.is_running() is False
        assert manager.get_pid() is None
    
    def test_reset(self):
        """Test resetting all state."""
        manager = TestExecutionManager()
        manager.start_test(script='test.sh', pid=123, bin='test_bin')
        
        manager.reset()
        
        assert manager.is_running() is False
        assert manager.get_pid() is None
        assert manager.get_script() is None
        assert manager.get_bin() is None
    
    def test_get_state(self):
        """Test getting full state as dict."""
        manager = TestExecutionManager()
        manager.start_test(script='test.sh', pid=123)
        
        state = manager.get_state()
        assert isinstance(state, dict)
        assert state['running'] is True
        assert state['script'] == 'test.sh'
        assert state['pid'] == 123
    
    def test_update_state(self):
        """Test updating state with multiple values."""
        manager = TestExecutionManager()
        manager.update_state({
            'running': True,
            'script': 'new_test.sh',
            'pid': 999,
            'topology': 'new_topology'
        })
        
        assert manager.is_running() is True
        assert manager.get_script() == 'new_test.sh'
        assert manager.get_pid() == 999
        assert manager.get_topology() == 'new_topology'


class TestSingletonManagers:
    """Test global singleton instances."""
    
    def test_service_status_singleton(self):
        """Test that get_service_status_manager returns the same instance."""
        manager1 = get_service_status_manager()
        manager2 = get_service_status_manager()
        
        assert manager1 is manager2
        
        # Changes in one should reflect in the other
        manager1.set_status('test_service', True)
        assert manager2.get_status('test_service') is True
    
    def test_test_execution_singleton(self):
        """Test that get_test_execution_manager returns the same instance."""
        manager1 = get_test_execution_manager()
        manager2 = get_test_execution_manager()
        
        assert manager1 is manager2
        
        # Changes in one should reflect in the other
        manager1.start_test(script='test.sh', pid=123)
        assert manager2.is_running() is True
        assert manager2.get_pid() == 123


class TestConcurrentModifications:
    """Test thread-safety under concurrent modifications."""
    
    def test_service_status_concurrent(self):
        """Test concurrent modifications to service status."""
        manager = ServiceStatusManager()
        errors = []
        
        def toggle_status(service_name):
            """Toggle service status multiple times."""
            try:
                for _ in range(50):
                    manager.set_status(service_name, True)
                    time.sleep(0.001)
                    manager.set_status(service_name, False)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=toggle_status, args=(f'service_{i}',))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # No errors should occur
        assert len(errors) == 0
    
    def test_test_execution_concurrent(self):
        """Test concurrent start/stop operations."""
        manager = TestExecutionManager()
        errors = []
        counter = {'value': 0}
        
        def start_stop_test(thread_id):
            """Start and stop test multiple times."""
            try:
                for i in range(20):
                    manager.start_test(
                        script=f'test_{thread_id}.sh',
                        pid=thread_id * 1000 + i
                    )
                    time.sleep(0.001)
                    manager.stop_test()
                    counter['value'] += 1
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=start_stop_test, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # No errors should occur
        assert len(errors) == 0
        # All operations should complete
        assert counter['value'] == 60  # 3 threads * 20 iterations
