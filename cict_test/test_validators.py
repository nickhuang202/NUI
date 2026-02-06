"""Unit tests for utils.validators module."""
import pytest
import os
import tempfile
from pathlib import Path
from utils.validators import (
    sanitize_path,
    is_safe_filename,
    validate_platform,
    validate_date,
    validate_test_items,
    sanitize_command_arg,
    validate_port_number,
    validate_ip_address
)


class TestSanitizePath:
    """Test path sanitization functionality."""
    
    def test_sanitize_valid_path(self):
        """Test sanitization of valid path."""
        path = "/home/NUI/test_report"
        result = sanitize_path(path)
        assert result is not None
        assert os.path.isabs(result)
    
    def test_sanitize_relative_path(self):
        """Test conversion of relative to absolute path."""
        path = "test_report"
        result = sanitize_path(path)
        assert result is not None
        assert os.path.isabs(result)
    
    def test_path_traversal_attack(self):
        """Test prevention of path traversal attack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Try to escape base directory
            result = sanitize_path("../../etc/passwd", base_dir=tmpdir)
            assert result is None
    
    def test_null_byte_injection(self):
        """Test prevention of null byte injection."""
        path = "/home/NUI/test\x00/report"
        result = sanitize_path(path)
        # Should remove null bytes
        assert '\x00' not in result if result else True
    
    def test_empty_path(self):
        """Test handling of empty path."""
        assert sanitize_path("") is None
        assert sanitize_path(None) is None
    
    def test_path_within_base_dir(self):
        """Test path validation within base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir, exist_ok=True)
            
            # Valid path within base
            result = sanitize_path(subdir, base_dir=tmpdir)
            assert result is not None
            assert tmpdir in result


class TestIsSafeFilename:
    """Test filename safety validation."""
    
    def test_safe_filename(self):
        """Test valid safe filenames."""
        assert is_safe_filename("report.txt") is True
        assert is_safe_filename("test_report_2026-02-03.tar.gz") is True
        assert is_safe_filename("data-file_123.json") is True
    
    def test_path_traversal_in_filename(self):
        """Test rejection of path traversal attempts."""
        assert is_safe_filename("../etc/passwd") is False
        assert is_safe_filename("..\\windows\\system32") is False
        assert is_safe_filename("test/../etc/passwd") is False
    
    def test_directory_separators(self):
        """Test rejection of directory separators."""
        assert is_safe_filename("dir/file.txt") is False
        assert is_safe_filename("dir\\file.txt") is False
    
    def test_null_bytes(self):
        """Test rejection of null bytes."""
        assert is_safe_filename("file\x00.txt") is False
    
    def test_special_characters(self):
        """Test rejection of special characters."""
        assert is_safe_filename("file;rm -rf.txt") is False
        assert is_safe_filename("file|cmd.txt") is False
        assert is_safe_filename("file&test.txt") is False
    
    def test_empty_filename(self):
        """Test rejection of empty filename."""
        assert is_safe_filename("") is False
        assert is_safe_filename(None) is False


class TestValidatePlatform:
    """Test platform validation."""
    
    def test_valid_platforms(self):
        """Test validation of valid platform names."""
        assert validate_platform("MINIPACK3BA") is True
        assert validate_platform("MINIPACK3N") is True
        assert validate_platform("WEDGE800BACT") is True
        assert validate_platform("WEDGE800CACT") is True
    
    def test_case_insensitive(self):
        """Test case-insensitive validation."""
        assert validate_platform("minipack3ba") is True
        assert validate_platform("MiniPack3BA") is True
    
    def test_invalid_platforms(self):
        """Test rejection of invalid platforms."""
        assert validate_platform("INVALID") is False
        assert validate_platform("HACKER") is False
        assert validate_platform("") is False
        assert validate_platform(None) is False


class TestValidateDate:
    """Test date validation."""
    
    def test_valid_dates(self):
        """Test validation of valid date strings."""
        assert validate_date("2026-02-03") is True
        assert validate_date("2025-12-31") is True
        assert validate_date("2026-01-01") is True
    
    def test_invalid_date_format(self):
        """Test rejection of invalid date formats."""
        assert validate_date("02-03-2026") is False  # Wrong format
        assert validate_date("2026/02/03") is False  # Wrong separator
        assert validate_date("2026-2-3") is False    # Missing leading zeros
    
    def test_invalid_dates(self):
        """Test rejection of invalid dates."""
        assert validate_date("2026-13-01") is False  # Invalid month
        assert validate_date("2026-02-30") is False  # Invalid day
        assert validate_date("not-a-date") is False
        assert validate_date("") is False
        assert validate_date(None) is False


class TestValidateTestItems:
    """Test test items validation."""
    
    def test_valid_test_items(self):
        """Test validation of valid test items."""
        items = {"sai": True, "link": False, "prbs": True}
        result = validate_test_items(items)
        assert result == items
    
    def test_unknown_test_types(self):
        """Test filtering of unknown test types."""
        items = {"sai": True, "unknown": True, "link": False}
        result = validate_test_items(items)
        assert "sai" in result
        assert "link" in result
        assert "unknown" not in result
    
    def test_invalid_values(self):
        """Test rejection of non-boolean values."""
        items = {"sai": "yes", "link": 1, "prbs": True}
        result = validate_test_items(items)
        # Only prbs should pass
        assert result == {"prbs": True}
    
    def test_non_dict_input(self):
        """Test handling of non-dict input."""
        assert validate_test_items("not a dict") == {}
        assert validate_test_items([]) == {}
        assert validate_test_items(None) == {}
    
    def test_empty_dict(self):
        """Test handling of empty dict."""
        result = validate_test_items({})
        assert result == {}


class TestSanitizeCommandArg:
    """Test command argument sanitization."""
    
    def test_safe_arguments(self):
        """Test that safe arguments pass through."""
        assert sanitize_command_arg("test123") == "test123"
        assert sanitize_command_arg("file.txt") == "file.txt"
    
    def test_remove_dangerous_chars(self):
        """Test removal of dangerous characters."""
        assert ";" not in sanitize_command_arg("test;rm -rf /")
        assert "|" not in sanitize_command_arg("test|malicious")
        assert "&" not in sanitize_command_arg("test&cmd")
        assert "$" not in sanitize_command_arg("test$var")
        assert "`" not in sanitize_command_arg("test`cmd`")
    
    def test_empty_input(self):
        """Test handling of empty input."""
        assert sanitize_command_arg("") == ""
        assert sanitize_command_arg(None) == ""


class TestValidatePortNumber:
    """Test port number validation."""
    
    def test_valid_ports(self):
        """Test validation of valid port numbers."""
        assert validate_port_number(80) is True
        assert validate_port_number(443) is True
        assert validate_port_number(5000) is True
        assert validate_port_number(65535) is True
    
    def test_port_as_string(self):
        """Test validation with string input."""
        assert validate_port_number("8080") is True
        assert validate_port_number("443") is True
    
    def test_invalid_ports(self):
        """Test rejection of invalid port numbers."""
        assert validate_port_number(0) is False
        assert validate_port_number(-1) is False
        assert validate_port_number(65536) is False
        assert validate_port_number(999999) is False
    
    def test_invalid_input(self):
        """Test handling of invalid input."""
        assert validate_port_number("not a number") is False
        assert validate_port_number(None) is False
        assert validate_port_number([]) is False


class TestValidateIpAddress:
    """Test IP address validation."""
    
    def test_valid_ips(self):
        """Test validation of valid IP addresses."""
        assert validate_ip_address("192.168.1.1") is True
        assert validate_ip_address("10.0.0.1") is True
        assert validate_ip_address("172.16.0.1") is True
        assert validate_ip_address("0.0.0.0") is True
        assert validate_ip_address("255.255.255.255") is True
    
    def test_invalid_ip_format(self):
        """Test rejection of invalid IP formats."""
        assert validate_ip_address("192.168.1") is False      # Too few octets
        assert validate_ip_address("192.168.1.1.1") is False  # Too many octets
        assert validate_ip_address("192.168.1") is False
    
    def test_invalid_octet_values(self):
        """Test rejection of invalid octet values."""
        assert validate_ip_address("256.1.1.1") is False
        assert validate_ip_address("192.256.1.1") is False
        assert validate_ip_address("192.168.256.1") is False
        assert validate_ip_address("192.168.1.256") is False
    
    def test_invalid_input(self):
        """Test handling of invalid input."""
        assert validate_ip_address("not an ip") is False
        assert validate_ip_address("") is False
        assert validate_ip_address(None) is False


# Self-test function for quick validation
def self_test():
    """Run quick self-test of validators module."""
    print("Running validators self-test...")
    
    tests = [
        ("Platform validation", validate_platform("MINIPACK3BA"), True),
        ("Invalid platform", validate_platform("INVALID"), False),
        ("Date validation", validate_date("2026-02-03"), True),
        ("Invalid date", validate_date("invalid"), False),
        ("Safe filename", is_safe_filename("test.txt"), True),
        ("Unsafe filename", is_safe_filename("../etc/passwd"), False),
        ("Valid IP", validate_ip_address("192.168.1.1"), True),
        ("Invalid IP", validate_ip_address("999.999.999.999"), False),
        ("Valid port", validate_port_number(8080), True),
        ("Invalid port", validate_port_number(99999), False),
    ]
    
    passed = 0
    failed = 0
    
    for name, result, expected in tests:
        if result == expected:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name} (expected {expected}, got {result})")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    # Run self-test
    success = self_test()
    exit(0 if success else 1)
