"""Tests for service layer components."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.base_service import BaseService, ServiceResult
from services.health_service import HealthCheckService


class TestServiceResult:
    """Test cases for ServiceResult dataclass."""
    
    def test_success_creation(self):
        """Test creating a successful result."""
        result = ServiceResult.ok(data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
    
    def test_success_with_status_code(self):
        """Test creating a successful result with custom status code."""
        result = ServiceResult.ok(data="test", status_code=201)
        assert result.success is True
        assert result.data == "test"
        assert result.status_code == 201
    
    def test_failure_creation(self):
        """Test creating a failure result."""
        result = ServiceResult.fail(error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None
    
    def test_failure_with_status_code(self):
        """Test creating a failure result with custom status code."""
        result = ServiceResult.fail(error="Server error", status_code=500)
        assert result.success is False
        assert result.error == "Server error"
        assert result.status_code == 500
    
    def test_to_dict_success(self):
        """Test converting successful result to dict."""
        result = ServiceResult.ok(data={"test": 123})
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["data"] == {"test": 123}
        assert "error" not in result_dict
    
    def test_to_dict_failure(self):
        """Test converting failure result to dict."""
        result = ServiceResult.fail(error="Error occurred", status_code=500)
        result_dict = result.to_dict()
        
        assert result_dict["success"] is False
        assert result_dict["error"] == "Error occurred"


class TestBaseService:
    """Test cases for BaseService class."""
    
    def test_initialization(self):
        """Test service initialization."""
        service = BaseService()
        assert service.logger is not None
        assert service.logger.name == "BaseService"
    
    def test_log_operation(self):
        """Test log_operation method."""
        service = BaseService()
        with patch.object(service.logger, 'info') as mock_info:
            service.log_operation("test_op", detail="test details")
            mock_info.assert_called_once_with("[test_op] detail=test details")
    
    def test_log_error(self):
        """Test log_error method."""
        service = BaseService()
        with patch.object(service.logger, 'error') as mock_error:
            error = Exception("error details")
            service.log_error("test_error", error)
            mock_error.assert_called_once_with("[test_error] Error: error details | Context: ")
    
    def test_subclass_logger_name(self):
        """Test that subclasses get their own logger name."""
        class CustomService(BaseService):
            pass
        
        service = CustomService()
        assert service.logger.name == "CustomService"


class TestHealthCheckService:
    """Test cases for HealthCheckService."""
    
    @pytest.fixture
    def health_service(self):
        """Create a HealthCheckService instance."""
        return HealthCheckService()
    
    @pytest.fixture
    def mock_version_file(self, tmp_path):
        """Create a mock VERSION file."""
        version_file = tmp_path / "VERSION"
        version_file.write_text("0.0.0.59")
        return str(tmp_path)
    
    def test_initialization(self, health_service):
        """Test service initialization."""
        assert health_service.logger is not None
        assert health_service.logger.name == "HealthCheckService"
    
    @patch('services.health_service.psutil')
    @patch('services.health_service.Path')
    def test_get_health_status_healthy(self, mock_path, mock_psutil, health_service):
        """Test get_health_status when system is healthy."""
        # Mock psutil
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.virtual_memory.return_value = Mock(percent=50.0, total=8000000000, used=4000000000)
        mock_psutil.disk_usage.return_value = Mock(percent=40.0, total=500000000000, used=200000000000)
        mock_psutil.process_iter.return_value = []
        
        # Mock Path for dependencies
        mock_path_instance = Mock()
        mock_path_instance.parent.parent = Mock()
        mock_path_instance.parent.parent.__truediv__ = Mock(return_value=Mock(exists=Mock(return_value=True)))
        mock_path.__file__ = mock_path_instance
        
        # Mock VERSION file
        version_file = Mock()
        version_file.exists.return_value = True
        version_file.read_text.return_value = "0.0.0.59"
        
        with patch.object(health_service, '_get_version', return_value="0.0.0.59"):
            with patch.object(health_service, '_check_services', return_value={'qsfp_service': True, 'sai_service': True, 'fboss2': True, 'all_healthy': True}):
                with patch.object(health_service, '_check_dependencies', return_value={'test_report_dir': True, 'all_available': True}):
                    result = health_service.get_health_status()
        
        # Verify result structure
        assert result.success is True
        assert result.data is not None
        assert result.data["status"] in ["healthy", "degraded"]
        assert "timestamp" in result.data
        assert "system" in result.data
        assert "services" in result.data
        assert "dependencies" in result.data
    
    def test_get_health_status_degraded(self, health_service):
        """Test get_health_status when system is degraded."""
        with patch.object(health_service, '_get_version', return_value="0.0.0.59"):
            with patch.object(health_service, '_get_system_info', return_value={'cpu_percent': 15.0}):
                with patch.object(health_service, '_check_services', return_value={'qsfp_service': False, 'sai_service': True, 'fboss2': True, 'all_healthy': False}):
                    with patch.object(health_service, '_check_dependencies', return_value={'test_report_dir': True, 'test_scripts_dir': False, 'all_available': False}):
                        result = health_service.get_health_status()
        
        # Should be degraded due to services not all healthy
        assert result.success is True
        assert result.data["status"] == "degraded"
        assert result.data["services"]["all_healthy"] is False
    
    def test_get_health_status_error_handling(self, health_service):
        """Test error handling in get_health_status."""
        # Mock to raise exception
        with patch.object(health_service, '_get_version', side_effect=Exception("Version error")):
            result = health_service.get_health_status()
        
        assert result.success is False
        assert result.error is not None
    
    def test_check_dependencies(self, health_service):
        """Test _check_dependencies method."""
        mock_base = Mock()
        mock_dirs = {
            'test_report': Mock(exists=Mock(return_value=True)),
            'test_script': Mock(exists=Mock(return_value=True)),
            'Topology': Mock(exists=Mock(return_value=False)),
            'logs': Mock(exists=Mock(return_value=True)),
            '.cache': Mock(exists=Mock(return_value=False))
        }
        
        def truediv_side_effect(name):
            return mock_dirs.get(name, Mock(exists=Mock(return_value=False)))
        
        mock_base.__truediv__ = Mock(side_effect=truediv_side_effect)
        
        with patch('services.health_service.Path') as mock_path:
            mock_path.__file__ = Mock()
            mock_path.__file__.parent.parent = mock_base
            mock_path.return_value.parent.parent = mock_base
            
            result = health_service._check_dependencies()
        
        assert result["test_report_dir"] is True
        assert result["test_scripts_dir"] is True
        assert result["topology_dir"] is False
        assert result["logs_dir"] is True
        assert result["cache_dir"] is False
        assert result["all_available"] is False
    
    @patch('services.health_service.psutil.process_iter')
    @patch('shutil.which')
    def test_check_services_all_running(self, mock_which, mock_process_iter, health_service):
        """Test _check_services when all services are running."""
        # Mock running processes
        mock_process_iter.return_value = [
            Mock(info={'name': 'qsfp_service'}),
            Mock(info={'name': 'wedge_agent'})
        ]
        mock_which.return_value = '/usr/bin/fboss2'
        
        result = health_service._check_services()
        
        assert result["qsfp_service"] is True
        assert result["sai_service"] is True
        assert result["fboss2"] is True
        assert result["all_healthy"] is True
    
    @patch('services.health_service.psutil.process_iter')
    @patch('shutil.which')
    def test_check_services_none_running(self, mock_which, mock_process_iter, health_service):
        """Test _check_services when no services are running."""
        mock_process_iter.return_value = []
        mock_which.return_value = None
        
        result = health_service._check_services()
        
        assert result["qsfp_service"] is False
        assert result["sai_service"] is False
        assert result["fboss2"] is False
        assert result["all_healthy"] is False
    
    @patch('services.health_service.psutil.process_iter')
    @patch('shutil.which')
    def test_check_services_exception_handling(self, mock_which, mock_process_iter, health_service):
        """Test _check_services exception handling."""
        mock_process_iter.side_effect = Exception("Process iteration failed")
        mock_which.return_value = None
        
        result = health_service._check_services()
        
        # Should return False for all services on error
        assert result["qsfp_service"] is False
        assert result["sai_service"] is False
        assert result["all_healthy"] is False
    
    @patch('services.health_service.psutil')
    def test_get_system_info(self, mock_psutil, health_service):
        """Test _get_system_info method."""
        mock_psutil.cpu_percent.return_value = 35.2
        mock_psutil.cpu_count.return_value = 8
        mock_psutil.virtual_memory.return_value = Mock(
            percent=65.5,
            total=16000000000,
            used=10000000000
        )
        mock_psutil.disk_usage.return_value = Mock(
            percent=55.8,
            total=1000000000000,
            used=558000000000
        )
        
        result = health_service._get_system_info()
        
        assert result["cpu_percent"] == 35.2
        assert result["cpu_count"] == 8
        assert result["memory_percent"] == 65.5
        assert result["disk_percent"] == 55.8
        assert "python_version" in result
        assert "platform" in result
    
    def test_get_version_file_exists(self, health_service):
        """Test _get_version when VERSION file exists."""
        mock_version_file = Mock()
        mock_version_file.exists.return_value = True
        mock_version_file.read_text.return_value = "1.2.3\n"
        
        with patch('services.health_service.Path') as mock_path:
            mock_path.__file__ = Mock()
            mock_path.__file__.parent.parent.__truediv__ = Mock(return_value=mock_version_file)
            mock_path.return_value.parent.parent.__truediv__ = Mock(return_value=mock_version_file)
            
            version = health_service._get_version()
            assert version == "1.2.3"
    
    def test_get_version_file_missing(self, health_service):
        """Test _get_version when VERSION file is missing."""
        mock_version_file = Mock()
        mock_version_file.exists.return_value = False
        
        with patch('services.health_service.Path') as mock_path:
            mock_path.__file__ = Mock()
            mock_path.__file__.parent.parent.__truediv__ = Mock(return_value=mock_version_file)
            mock_path.return_value.parent.parent.__truediv__ = Mock(return_value=mock_version_file)
            
            version = health_service._get_version()
            assert version == "unknown"
    
    def test_get_version_read_error(self, health_service):
        """Test _get_version with read error."""
        mock_version_file = Mock()
        mock_version_file.exists.return_value = True
        mock_version_file.read_text.side_effect = IOError("Read error")
        
        with patch('services.health_service.Path') as mock_path:
            mock_path.__file__ = Mock()
            mock_path.__file__.parent.parent.__truediv__ = Mock(return_value=mock_version_file)
            mock_path.return_value.parent.parent.__truediv__ = Mock(return_value=mock_version_file)
            
            version = health_service._get_version()
            assert version == "unknown"
