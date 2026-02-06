# NUI Documentation

This directory contains comprehensive documentation for the **Network Unit Interface (NUI)** application - a Flask-based network testing and monitoring platform.

**Version:** 0.0.0.59  
**Status:** Phase 4 Refactoring (50% Complete)  
**Last Updated:** February 3, 2026

---

## 📑 Quick Navigation

### Start Here
- **[INDEX.md](INDEX.md)** - Complete documentation index with roadmap and quality metrics
- **[REFACTORING_PLAN.md](REFACTORING_PLAN.md)** - Refactoring progress and architecture evolution

### Key Documents

#### Deployment & Operations
- **[CROSS_PLATFORM_DEPLOYMENT.md](CROSS_PLATFORM_DEPLOYMENT.md)** - Linux and Windows deployment guide
- **[LINUX_COMPATIBILITY.md](LINUX_COMPATIBILITY.md)** - Cross-platform compatibility verification

#### Architecture & Implementation
- **[PHASE3_COMPLETION_REPORT.md](PHASE3_COMPLETION_REPORT.md)** - Service layer and quality improvements
- **[THREAD_SAFE_STATE.md](THREAD_SAFE_STATE.md)** - Thread-safe state management implementation

#### Feature Documentation
- **[TOPOLOGY_UPDATE.md](TOPOLOGY_UPDATE.md)** - Topology management and LLDP discovery
- **[TOPOLOGY_AUTO_SAVE.md](TOPOLOGY_AUTO_SAVE.md)** - Automatic topology persistence
- **[TRANSCEIVER_INFO.md](TRANSCEIVER_INFO.md)** - QSFP transceiver monitoring

#### Configuration & Conversion
- **[convert_reconvert_SPEC.md](convert_reconvert_SPEC.md)** - FBOSS configuration conversion
- **[WEDGE800BACT_CONVERSION_RULES.md](WEDGE800BACT_CONVERSION_RULES.md)** - Platform-specific rules

---

## 📊 Current Status

### Architecture

**Pre-Refactoring (v0.0.0.1):**
- Monolithic `app.py` (5,000+ lines)
- 95 routes in single file
- Global mutable state
- No test coverage
- Windows-only paths

**Current (v0.0.0.59):**
- Modular architecture with 6 blueprints
- 219 API routes (65 v1 + 154 legacy)
- Service layer + repositories
- 168 tests (156 passing - 93% pass rate)
- 14.66% test coverage
- Cross-platform support (Windows/Linux)
- Thread-safe state management

### Test Coverage by Module

| Module | Coverage | Tests | Status |
|--------|----------|-------|--------|
| `validators.py` | 96.67% | 18 | ✅ |
| `thread_safe_state.py` | 98.85% | 22 | ✅ |
| `base_service.py` | 100% | 10 | ✅ |
| `health_service.py` | 91.80% | 12 | ✅ |
| `file_repository.py` | 85.42% | 20 | ✅ |
| `cache_repository.py` | 92.31% | 20 | ✅ |
| **Overall** | **14.66%** | **156** | ⏳ |

### Refactoring Progress

- ✅ **Phase 1:** Security & Infrastructure (100%)
- ✅ **Phase 2:** Blueprint Migration (100%)
- ✅ **Phase 3:** Service Layer & Quality (100%)
- ⏳ **Phase 4:** Advanced Features (50%)
  - ✅ pytest-cov setup
  - ✅ Thread-safe state management
  - ✅ Cross-platform compatibility
  - ⏳ Test API alignment (93% complete)
  - ⏳ CORS configuration
  - ⏳ CI/CD pipeline

---

## 🏗️ Architecture Overview

### Directory Structure

```
NUI/
├── app.py (5,212 lines)         # Main Flask application
├── config/                       # Configuration management
│   ├── settings.py              # Environment-based config
│   └── logging_config.py        # Logging setup
├── middleware/                   # Request/response middleware
│   ├── rate_limit.py           # Rate limiting
│   ├── request_id.py           # Request ID tracing
│   └── request_logging.py      # Request logging
├── services/                     # Business logic layer
│   ├── base_service.py         # Base service class
│   └── health_service.py       # Health check service
├── repositories/                 # Data access layer
│   ├── file_repository.py      # File operations
│   └── cache_repository.py     # Caching operations
├── routes/                       # Blueprint-based routes
│   ├── dashboard.py            # Dashboard (12 routes)
│   ├── test.py                 # Test execution (13 routes)
│   ├── topology.py             # Topology (4 routes)
│   ├── lab_monitor.py          # Lab monitoring (32 routes)
│   ├── ports.py                # Port management (4 routes)
│   └── health.py               # Health endpoints (3 routes)
├── utils/                        # Utility functions
│   ├── validators.py           # Input validation
│   ├── thread_safe_state.py   # Thread-safe state
│   └── versioning.py           # API versioning
└── tests/                        # Test suite (168 tests)
```

### Technology Stack

- **Framework:** Flask 2.0+
- **Python:** 3.10+ (tested on 3.10.11)
- **Testing:** pytest 9.0.2 + pytest-cov 7.0.0
- **Monitoring:** psutil for system metrics
- **Platforms:** Windows 10/11, Linux (Ubuntu/RHEL)

---

## 🚀 Quick Start

### Installation

```bash
# Navigate to project
cd NUI

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Development mode
python app.py

# Production (Linux - gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Production (Windows - waitress)
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_services.py

# Run with verbose output
pytest -v
```

### Accessing Endpoints

- **Dashboard:** http://localhost:5000
- **Health Check:** http://localhost:5000/api/v1/health
- **Lab Monitor:** http://localhost:5000/lab_monitor

---

## 📖 Documentation Guide

### For New Developers

Start here in order:

1. [INDEX.md](INDEX.md) - Get overview of project and documentation
2. [REFACTORING_PLAN.md](REFACTORING_PLAN.md) - Understand architecture evolution
3. [THREAD_SAFE_STATE.md](THREAD_SAFE_STATE.md) - Learn thread-safety patterns
4. [CROSS_PLATFORM_DEPLOYMENT.md](CROSS_PLATFORM_DEPLOYMENT.md) - Set up development environment

### For Deployment

1. [CROSS_PLATFORM_DEPLOYMENT.md](CROSS_PLATFORM_DEPLOYMENT.md) - Full deployment guide
2. [LINUX_COMPATIBILITY.md](LINUX_COMPATIBILITY.md) - Platform-specific notes
3. [TOPOLOGY_UPDATE.md](TOPOLOGY_UPDATE.md) - Configure topology management

### For Feature Development

1. [PHASE3_COMPLETION_REPORT.md](PHASE3_COMPLETION_REPORT.md) - Service layer patterns
2. [THREAD_SAFE_STATE.md](THREAD_SAFE_STATE.md) - State management patterns
3. [convert_reconvert_SPEC.md](convert_reconvert_SPEC.md) - Configuration conversion

### For Testing

1. Check `tests/` directory for existing test patterns
2. Review [INDEX.md](INDEX.md#quality-metrics) for coverage goals
3. See [REFACTORING_PLAN.md](REFACTORING_PLAN.md#phase-4) for testing roadmap

---

## 🗂️ Legacy Documentation

Outdated or superseded documentation has been moved to [legacy/](legacy/) directory:

| File | Reason | Replacement |
|------|--------|-------------|
| `README_old.md` | Pre-refactoring README | This README.md |
| `app_script.txt` | Pre-refactoring notes | [REFACTORING_PLAN.md](REFACTORING_PLAN.md) |
| `AVARUNTAR.md` | Early architecture | [INDEX.md](INDEX.md) |
| `test_report.pdf` | Old test reports | [INDEX.md](INDEX.md#quality-metrics) |
| `G_REPORT_*.md` | Old reporting system | Modern test infrastructure |
| `RELEASE_SCRIPTS.md` | Old release process | To be updated |
| `SPEC.md` | Original spec | [convert_reconvert_SPEC.md](convert_reconvert_SPEC.md) |
| `WORKFLOW.md` | Old workflows | [RUN_ALL_TEST_WORKFLOW.md](RUN_ALL_TEST_WORKFLOW.md) |
| `TEST_INFO.md` | Old test info | [INDEX.md](INDEX.md#testing--quality) |
| `USAGE_REPORT.md` | Old usage tracking | To be modernized |
| `SAI_TEST_STATUS_FEATURES.md` | Old status tracking | Thread-safe state management |
| `RUN_ALL_TEST_WORKFLOW.md` | May need updates | Review for current accuracy |

**Note:** Legacy documents are kept for historical reference only and do not reflect the current implementation.

---

## 🔄 Keeping Documentation Updated

### When to Update

- **Feature Addition:** Update relevant feature docs + [INDEX.md](INDEX.md)
- **API Changes:** Update affected workflow/specification docs
- **Architecture Changes:** Update [REFACTORING_PLAN.md](REFACTORING_PLAN.md)
- **Deployment Changes:** Update [CROSS_PLATFORM_DEPLOYMENT.md](CROSS_PLATFORM_DEPLOYMENT.md)
- **Test Improvements:** Update [INDEX.md](INDEX.md#quality-metrics)

### Documentation Standards

- Use Markdown (.md) format
- Include table of contents for docs >200 lines
- Use code blocks with language hints (```python, ```bash)
- Keep line length under 120 characters
- Add examples for complex concepts
- Update "Last Updated" dates

---

## 📞 Support

- **Technical Questions:** Refer to specific documentation files
- **Bug Reports:** Include steps to reproduce + system info
- **Feature Requests:** Review [REFACTORING_PLAN.md](REFACTORING_PLAN.md) roadmap first

---

## 📈 Next Steps (Phase 4 Completion)

### Immediate Priorities

1. ⏳ Complete test API alignment (12 tests remaining)
2. ⏳ Implement CORS configuration
3. ⏳ Set up CI/CD pipeline (GitHub Actions)
4. ⏳ Extract helper functions to services

### Target Metrics

- **Test Pass Rate:** 98%+ (165/168 tests)
- **Test Coverage:** 70%+ overall
- **Documentation:** 100% current APIs documented
- **Platform Support:** Full Windows + Linux compatibility

---

**Maintained By:** NUI Development Team  
**Version:** 0.0.0.59  
**Last Updated:** February 3, 2026
