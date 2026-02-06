# Phase 1 Infrastructure - Test Plan

## Overview

This document outlines the testing strategy for Phase 1 infrastructure components:
- Configuration Management
- Logging Infrastructure  
- Input Validators
- Rate Limiting Middleware

---

## Quick Self-Test

For quick validation without pytest:

```bash
python run_self_tests.py
```

This runs lightweight self-tests for all modules and provides immediate feedback.

---

## Full Test Suite

### Installation

```bash
pip install -r requirements.txt
```

### Running Tests

**Run all tests:**
```bash
pytest
```

**Run with coverage:**
```bash
pytest --cov=config --cov=middleware --cov=utils --cov-report=html --cov-report=term
```

**Run specific test file:**
```bash
pytest tests/test_validators.py
pytest tests/test_config.py
pytest tests/test_logging.py
```

**Run tests by marker:**
```bash
pytest -m unit          # Only unit tests
pytest -m security      # Only security tests
```

**Verbose output:**
```bash
pytest -v
```

---

## Test Coverage

### Target Coverage: 80%+

| Module | Coverage Target | Priority |
|--------|----------------|----------|
| `utils/validators.py` | 90%+ | HIGH |
| `config/settings.py` | 85%+ | HIGH |
| `config/logging_config.py` | 80%+ | MEDIUM |
| `middleware/rate_limit.py` | 75%+ | MEDIUM |

---

## Test Structure

```
tests/
├── __init__.py
├── test_validators.py      # Input validation tests
├── test_config.py          # Configuration tests
├── test_logging.py         # Logging setup tests
└── conftest.py            # Shared fixtures (future)
```

---

## Test Categories

### 1. Unit Tests

**Purpose:** Test individual functions in isolation

**Files:**
- `test_validators.py` - 40+ test cases
- `test_config.py` - 15+ test cases
- `test_logging.py` - 10+ test cases

**Examples:**
```python
def test_validate_platform():
    assert validate_platform('MINIPACK3BA') == True
    assert validate_platform('INVALID') == False

def test_path_traversal_prevention():
    result = sanitize_path('../../etc/passwd', base_dir='/home')
    assert result is None
```

### 2. Security Tests

**Purpose:** Verify security controls

**Test Cases:**
- Path traversal prevention
- Command injection prevention
- Null byte injection
- Special character filtering
- Whitelist validation

**Examples:**
```python
def test_path_traversal_attack():
    # Should reject paths outside base directory
    result = sanitize_path('../../../etc/passwd', base_dir='/home/NUI')
    assert result is None

def test_command_injection():
    # Should remove dangerous shell characters
    result = sanitize_command_arg('test;rm -rf /')
    assert ';' not in result
```

### 3. Integration Tests (Future)

**Purpose:** Test component interactions

**Planned:**
- Flask app with rate limiter
- Logging with real file I/O
- Config with environment variables

---

## Manual Testing Procedures

### 1. Validators Module

```python
# Test in Python REPL
from utils import validate_platform, sanitize_path

# Should pass
validate_platform('MINIPACK3BA')  # True
sanitize_path('/home/NUI/test')   # Returns absolute path

# Should fail
validate_platform('HACKER')       # False
sanitize_path('../../etc/passwd', '/home/NUI')  # None
```

### 2. Configuration Module

```bash
# Test environment variable override
export FLASK_PORT=8080
python -c "from config import get_config; print(get_config().PORT)"
# Should output: 8080

# Test different environments
export FLASK_ENV=production
python -c "from config import get_config; print(get_config().DEBUG)"
# Should output: False
```

### 3. Logging Module

```python
# Test logging output
from config import setup_logging

logger = setup_logging()
logger.info('Test message')
logger.warning('Warning message')
logger.error('Error message')

# Check logs/nui.log file for output
```

---

## Test Data

### Valid Test Inputs

**Platforms:**
- MINIPACK3BA
- MINIPACK3N
- WEDGE800BACT
- WEDGE800CACT

**Dates:**
- 2026-02-03
- 2025-12-31
- 2026-01-01

**Test Items:**
```json
{
  "sai": true,
  "link": false,
  "agent_hw": true,
  "prbs": true
}
```

### Invalid/Malicious Test Inputs

**Path Traversal:**
- `../../etc/passwd`
- `../../../root/.ssh/id_rsa`
- `..\..\..\windows\system32`

**Command Injection:**
- `test;rm -rf /`
- `file|malicious`
- `cmd & whoami`

**Null Bytes:**
- `file\x00.txt`
- `/path\x00/to/file`

---

## Continuous Integration (Future)

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v2
```

---

## Test Maintenance

### Adding New Tests

1. Create test file in `tests/` directory
2. Follow naming convention: `test_*.py`
3. Use descriptive test names: `test_function_behavior`
4. Add docstrings explaining test purpose
5. Update this TEST_PLAN.md

### Test Review Checklist

- [ ] Tests cover happy path
- [ ] Tests cover error cases
- [ ] Tests cover edge cases
- [ ] Tests include security scenarios
- [ ] Tests are independent (no shared state)
- [ ] Tests have clear assertions
- [ ] Tests have descriptive names

---

## Known Issues / Limitations

1. **Rate Limiter Tests:** Currently use in-memory storage. Production should use Redis.
2. **Log File Cleanup:** Tests don't clean up log files automatically
3. **Environment Variables:** Some tests may interfere with each other if run in parallel

---

## Performance Benchmarks

### Expected Test Execution Times

| Test Suite | Target Time | Notes |
|------------|-------------|-------|
| Self-tests | < 5 seconds | Quick validation |
| Unit tests | < 30 seconds | All unit tests |
| Full suite | < 1 minute | Including coverage |

---

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Make sure you're in the NUI directory
cd d:\Accton_Projects\DIAG\META\FBOSS_INFO\3BA\NUI_v0.0.0.59\NUI
python -m pytest tests/
```

**Permission Errors (logs/):**
```bash
# Ensure logs directory is writable
chmod 755 logs/
```

**Pytest Not Found:**
```bash
pip install pytest pytest-cov pytest-mock
```

---

## Success Criteria

Phase 1 infrastructure tests are considered successful when:

- ✅ All unit tests pass
- ✅ Code coverage > 80%
- ✅ Self-tests complete without errors
- ✅ All security tests pass
- ✅ No critical vulnerabilities detected
- ✅ Tests run in < 1 minute

---

## Next Steps

After tests pass:
1. Integrate infrastructure into app.py
2. Add integration tests for Flask app
3. Set up CI/CD pipeline
4. Add mutation testing for robustness
5. Performance testing under load

---

**Last Updated:** 2026-02-03  
**Test Suite Version:** 1.0  
**Coverage Target:** 80%+
