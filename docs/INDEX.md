# NUI Documentation Index

**Network Unit Interface (NUI)** - A comprehensive Flask-based network testing and monitoring platform.

**Last Updated:** February 3, 2026  
**Version:** 0.0.0.59  
**Status:** Phase 4 Refactoring (50% Complete)

---

## 📚 Core Documentation

### Architecture & Design

- **[REFACTORING_PLAN.md](REFACTORING_PLAN.md)** - Complete refactoring roadmap and progress tracker
  - Phases 1-3: 100% Complete (Security, Blueprints, Services)
  - Phase 4: 50% Complete (Coverage, Thread-safety, Cross-platform)
  - Technical debt analysis and solutions

- **[PHASE3_COMPLETION_REPORT.md](PHASE3_COMPLETION_REPORT.md)** - Phase 3 detailed completion report
  - Service layer implementation
  - Repository pattern implementation
  - Health check system
  - API versioning strategy

### Deployment & Operations

- **[CROSS_PLATFORM_DEPLOYMENT.md](CROSS_PLATFORM_DEPLOYMENT.md)** - Production deployment guide
  - Linux deployment (Ubuntu/RHEL with systemd)
  - Windows deployment (Windows Server with NSSM)
  - Environment configuration
  - Service management
  - Security best practices

- **[LINUX_COMPATIBILITY.md](LINUX_COMPATIBILITY.md)** - Cross-platform compatibility verification
  - Platform-specific code handling
  - Test results (Windows & Linux)
  - Known issues and solutions

### Feature Documentation

- **[THREAD_SAFE_STATE.md](THREAD_SAFE_STATE.md)** - Thread-safe state management
  - ThreadSafeDict implementation
  - ServiceStatusManager usage
  - TestExecutionManager usage
  - Concurrent access patterns

- **[TOPOLOGY_UPDATE.md](TOPOLOGY_UPDATE.md)** - Topology management features
  - Dynamic topology updates
  - Auto-save functionality
  - LLDP discovery integration

- **[TOPOLOGY_AUTO_SAVE.md](TOPOLOGY_AUTO_SAVE.md)** - Topology auto-save implementation
  - Automatic topology persistence
  - Recovery mechanisms

- **[TRANSCEIVER_INFO.md](TRANSCEIVER_INFO.md)** - Transceiver monitoring
  - QSFP service integration
  - Real-time monitoring
  - Data collection strategies

### Workflows & Procedures

- **[RUN_ALL_TEST_WORKFLOW.md](RUN_ALL_TEST_WORKFLOW.md)** - Complete test execution workflow
  - Test script organization
  - Execution procedures
  - Result collection

- **[WORKFLOW.md](WORKFLOW.md)** - General application workflows
  - User workflows
  - System workflows
  - Integration points

- **[SAI_TEST_STATUS_FEATURES.md](SAI_TEST_STATUS_FEATURES.md)** - SAI test status monitoring
  - Service status tracking
  - Test execution monitoring
  - Real-time updates

### Conversion & Configuration

- **[convert_reconvert_SPEC.md](convert_reconvert_SPEC.md)** - Configuration conversion specification
  - FBOSS config conversion
  - Bidirectional conversion rules
  - Validation procedures

- **[WEDGE800BACT_CONVERSION_RULES.md](WEDGE800BACT_CONVERSION_RULES.md)** - Platform-specific rules
  - WEDGE800BACT conversion
  - Port mapping
  - Profile configurations

- **[SPEC.md](SPEC.md)** - Original technical specifications
  - System requirements
  - API specifications
  - Data formats

### Testing & Quality

- **[TEST_INFO.md](TEST_INFO.md)** - Testing infrastructure information
  - Test organization
  - Test types
  - Coverage metrics

- **[G_REPORT_VERIFICATION.md](G_REPORT_VERIFICATION.md)** - G-Report verification procedures
  - Report validation
  - Data integrity checks

- **[G_REPORT_LOG_SPLITTING.md](G_REPORT_LOG_SPLITTING.md)** - Log processing for G-Reports
  - Log splitting algorithms
  - Report generation

### Release Management

- **[RELEASE_SCRIPTS.md](RELEASE_SCRIPTS.md)** - Release automation scripts
  - Build procedures
  - Version management
  - Distribution packages

- **[USAGE_REPORT.md](USAGE_REPORT.md)** - Usage tracking and reporting
  - Metrics collection
  - Report generation
  - Analytics

---

## 🏗️ Current Architecture (Post-Refactoring)

### Application Structure

```
NUI/
├── app.py                    # Main Flask application (5,212 lines)
├── config/                   # Configuration management
│   ├── settings.py          # Environment-based configuration
│   └── logging_config.py    # Logging setup
├── middleware/              # Request/response middleware
│   ├── rate_limit.py       # Rate limiting
│   ├── request_id.py       # Request ID tracing
│   └── request_logging.py  # Request logging
├── services/               # Business logic layer
│   ├── base_service.py    # Base service class
│   └── health_service.py  # Health check service
├── repositories/           # Data access layer
│   ├── file_repository.py    # File operations
│   └── cache_repository.py   # Caching operations
├── routes/                # Blueprint-based routes (6 blueprints)
│   ├── dashboard.py       # Dashboard routes (12 routes)
│   ├── test.py           # Test execution routes (13 routes)
│   ├── topology.py       # Topology management (4 routes)
│   ├── lab_monitor.py    # Lab monitoring (32 routes)
│   ├── ports.py          # Port management (4 routes)
│   ├── health.py         # Health endpoints (3 routes)
│   └── error_handlers.py # Error handling
├── utils/                 # Utility functions
│   ├── validators.py      # Input validation (96.67% coverage)
│   ├── thread_safe_state.py # Thread-safe state (98.85% coverage)
│   └── versioning.py      # API versioning
└── tests/                 # Test suite (168 tests, 156 passing)
    ├── test_services.py      # Service tests (22/22 passing)
    ├── test_repositories.py  # Repository tests (40/40 passing)
    ├── test_thread_safe_state.py # Thread-safety tests (22/22 passing)
    └── test_cross_platform.py   # Cross-platform tests (6/6 passing)
```

### Technology Stack

- **Framework:** Flask 2.0+
- **Python:** 3.10+ (tested on 3.10.11)
- **Testing:** pytest 9.0.2 with pytest-cov 7.0.0
- **Monitoring:** psutil for system metrics
- **Platforms:** Windows 10/11, Linux (Ubuntu/RHEL)

### API Endpoints

- **Total Routes:** 219 (65 v1 versioned + 154 legacy)
- **Blueprints:** 6 modular blueprints
- **Health Checks:** 3 endpoints (`/api/v1/health`, `/api/health`, `/health`)
- **Versioning:** Dual registration pattern (v1 + legacy compatibility)

---

## 📊 Quality Metrics

### Test Coverage

- **Total Tests:** 168 tests
- **Passing:** 156 (92.86%)
- **Overall Coverage:** 14.66%
- **Key Modules:**
  - `validators.py`: 96.67% coverage
  - `base_service.py`: 100% coverage
  - `health_service.py`: 91.80% coverage
  - `thread_safe_state.py`: 98.85% coverage

### Refactoring Progress

- ✅ **Phase 1:** Security & Infrastructure (100%)
- ✅ **Phase 2:** Blueprint Architecture (100%)
- ✅ **Phase 3:** Service Layer & Quality (100%)
- ⏳ **Phase 4:** Advanced Features (50%)
  - ✅ pytest-cov setup
  - ✅ Cross-platform compatibility
  - ✅ Thread-safe state management
  - ⏳ Test API alignment (73% complete)
  - ⏳ CORS configuration
  - ⏳ CI/CD pipeline

---

## 🚀 Quick Start

### Development Setup

```bash
# Clone and navigate
cd NUI

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run with coverage
pytest --cov

# Run application
python app.py
```

### Configuration

```bash
# Copy example config
cp lab_config.example.json lab_config.json

# Set environment
export FLASK_ENV=development  # Linux
$env:FLASK_ENV='development'  # Windows

# Configure logging level
export LOG_LEVEL=INFO
```

### Accessing the Application

- **Dashboard:** http://localhost:5000
- **Health Check:** http://localhost:5000/api/v1/health
- **API Documentation:** See [SPEC.md](SPEC.md)

---

## 🔧 Development Guidelines

### Code Style

- Follow PEP 8 conventions
- Use type hints for function signatures
- Document all public methods with docstrings
- Keep functions under 50 lines when possible
- Use meaningful variable names

### Testing Requirements

- Write tests for all new features
- Maintain >90% coverage for new code
- Use pytest fixtures for setup
- Mock external dependencies
- Test both success and failure paths

### Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Ensure all tests pass (`pytest`)
4. Update relevant documentation
5. Submit PR with clear description

---

## 📝 Documentation Standards

### When to Update Documentation

- **Feature Addition:** Update relevant feature docs + README
- **API Changes:** Update SPEC.md and relevant workflow docs
- **Architecture Changes:** Update REFACTORING_PLAN.md
- **Deployment Changes:** Update CROSS_PLATFORM_DEPLOYMENT.md
- **Bug Fixes:** Add notes to known issues sections

### Documentation Format

- Use Markdown (.md) for all documentation
- Include table of contents for docs >200 lines
- Use code blocks with language hints
- Include examples for complex concepts
- Keep line length under 120 characters

---

## 🐛 Known Issues

See individual documents for specific known issues:

- [CROSS_PLATFORM_DEPLOYMENT.md](CROSS_PLATFORM_DEPLOYMENT.md#known-issues) - Deployment issues
- [LINUX_COMPATIBILITY.md](LINUX_COMPATIBILITY.md#known-issues) - Compatibility issues
- [REFACTORING_PLAN.md](REFACTORING_PLAN.md) - Technical debt items

---

## 📞 Support & Contact

- **Issues:** File issues in project issue tracker
- **Questions:** Refer to specific documentation files
- **Updates:** Check REFACTORING_PLAN.md for latest progress

---

## 📋 Legacy Documentation

Outdated or superseded documentation has been moved to [legacy/](legacy/) directory:

- `app_script.txt` - Original app script notes
- `AVARUNTAR.md` - Early architecture notes
- `test_report.pdf` - Old test reports

**Note:** Legacy documents are kept for historical reference but may not reflect the current implementation.

---

## 🗺️ Roadmap

### Immediate (Phase 4 - 2 weeks)

- [ ] Complete test API alignment (12 tests remaining)
- [ ] Implement CORS configuration
- [ ] Set up CI/CD pipeline
- [ ] Complete helper function extraction

### Short-term (1-2 months)

- [ ] Increase test coverage to >70%
- [ ] Add JWT authentication (optional)
- [ ] Performance optimization
- [ ] User documentation

### Long-term (3-6 months)

- [ ] Microservices architecture evaluation
- [ ] GraphQL API consideration
- [ ] Advanced monitoring & alerting
- [ ] Multi-tenancy support

---

**Last Updated:** February 3, 2026  
**Maintained By:** NUI Development Team  
**Version:** 0.0.0.59
