# Cross-Platform Deployment Guide

This guide covers deploying the NUI application on both Windows and Linux environments.

## System Requirements

### Common Requirements
- Python 3.10 or higher
- pip (Python package manager)
- 2GB RAM minimum
- 1GB free disk space

### Platform-Specific Requirements

**Linux (Ubuntu/Debian):**
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

# Install system monitoring tools (for psutil)
sudo apt-get install -y python3-dev gcc
```

**Linux (RHEL/CentOS):**
```bash
# Install system dependencies
sudo yum install -y python3 python3-pip python3-devel gcc
```

**Windows:**
- Python 3.10+ from Microsoft Store or python.org
- No additional system packages required

---

## Installation

### 1. Clone Repository
```bash
# Linux/macOS
git clone <repository-url>
cd NUI

# Windows
git clone <repository-url>
cd NUI
```

### 2. Create Virtual Environment

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### 3. Install Dependencies

**All Platforms:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If `requirements.txt` doesn't exist, install manually:
```bash
pip install flask flask-limiter pyjwt psutil pytest pytest-cov
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

**Linux/macOS:**
```bash
# .env
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False

# Paths (use forward slashes)
TEST_REPORT_BASE=/opt/nui/test_report
TOPOLOGY_DIR=/opt/nui/Topology
LOG_DIR=/var/log/nui

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here
```

**Windows:**
```powershell
# .env
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False

# Paths (use forward slashes or escaped backslashes)
TEST_REPORT_BASE=D:/NUI/test_report
TOPOLOGY_DIR=D:/NUI/Topology
LOG_DIR=D:/NUI/logs

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here
```

**Note:** The application uses `pathlib.Path` internally, so paths work with forward slashes on all platforms.

---

## Running the Application

### Development Mode

**Linux/macOS:**
```bash
export FLASK_ENV=development
python app.py
```

**Windows (PowerShell):**
```powershell
$env:FLASK_ENV='development'
python app.py
```

### Production Mode

**Linux (systemd service):**

Create `/etc/systemd/system/nui.service`:
```ini
[Unit]
Description=NUI Flask Application
After=network.target

[Service]
Type=simple
User=nui
WorkingDirectory=/opt/nui
Environment="FLASK_ENV=production"
ExecStart=/opt/nui/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nui
sudo systemctl start nui
sudo systemctl status nui
```

**Windows (NSSM - Non-Sucking Service Manager):**

Download NSSM from https://nssm.cc/, then:
```powershell
nssm install NUI "C:\Python310\python.exe" "D:\NUI\app.py"
nssm set NUI AppDirectory "D:\NUI"
nssm set NUI AppEnvironmentExtra FLASK_ENV=production
nssm start NUI
```

---

## Testing

### Run All Tests

**All Platforms:**
```bash
# Run tests with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test file
pytest tests/test_services.py -v

# Run cross-platform compatibility test
python test_cross_platform.py
```

### Platform-Specific Test Results

The test suite should pass on both platforms. Some tests may behave differently:

- **Disk usage tests**: Use `C:\` on Windows, `/` on Linux
- **Service detection**: Process names differ between platforms
- **Path tests**: Automatically handle platform separators

---

## Platform-Specific Features

### Service Monitoring

The health check service adapts to the platform:

**Linux:**
- Monitors system services via `systemctl` or process names
- Checks `/opt/fboss/` directories
- Uses `/var/log/` for logs

**Windows:**
- Monitors Windows services and processes
- Checks local application directories
- Uses application-relative log directories

### File Paths

All file operations use `pathlib.Path` which automatically:
- Uses correct path separators (`/` on Linux, `\` on Windows)
- Handles absolute vs relative paths correctly
- Normalizes paths across platforms

**Example:**
```python
from repositories.file_repository import FileRepository

# Works on both platforms
repo = FileRepository("/opt/nui/data")  # Linux
repo = FileRepository("C:/NUI/data")    # Windows
repo = FileRepository("./data")         # Relative (both)
```

---

## Troubleshooting

### Permission Issues (Linux)

```bash
# Create required directories
sudo mkdir -p /opt/nui/{test_report,Topology,logs}
sudo chown -R nui:nui /opt/nui

# Fix permissions
chmod 755 /opt/nui
chmod -R 644 /opt/nui/logs
```

### Port Binding Issues

**Linux (port 80 requires root):**
```bash
# Option 1: Use port >1024 (e.g., 5000)
FLASK_PORT=5000 python app.py

# Option 2: Use authbind
sudo apt-get install authbind
sudo touch /etc/authbind/byport/80
sudo chmod 500 /etc/authbind/byport/80
sudo chown nui /etc/authbind/byport/80
authbind --deep python app.py
```

**Windows (firewall):**
```powershell
# Allow inbound connections
New-NetFirewallRule -DisplayName "NUI Flask App" -Direction Inbound -Port 5000 -Protocol TCP -Action Allow
```

### Module Import Errors

```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux
$env:PYTHONPATH="$PWD"                    # Windows
```

---

## Performance Tuning

### Linux (production)

Use gunicorn for better performance:
```bash
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# With systemd
ExecStart=/opt/nui/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Windows (production)

Use waitress for production:
```bash
pip install waitress

# In app.py, add:
# if __name__ == '__main__':
#     from waitress import serve
#     serve(app, host='0.0.0.0', port=5000)
```

---

## Monitoring

### Health Check Endpoints

All endpoints work identically on both platforms:

```bash
# Simple health check
curl http://localhost:5000/health

# Detailed health check
curl http://localhost:5000/api/v1/health

# Example response (both platforms)
{
  "status": "healthy",
  "timestamp": "2026-02-03T10:30:00",
  "version": "0.0.0.59",
  "system": {
    "platform": "linux",  # or "win32"
    "cpu_percent": 25.5,
    "memory_percent": 45.2,
    "disk_percent": 62.4
  },
  "services": {...},
  "dependencies": {...}
}
```

---

## Security Notes

### File Permissions (Linux)

```bash
# Restrict sensitive files
chmod 600 .env
chmod 600 config/*.json

# Logs should be readable by service user
chmod 755 logs
chmod 644 logs/*.log
```

### Windows ACLs

```powershell
# Restrict .env file to current user
icacls .env /inheritance:r /grant:r "$env:USERNAME:(R)"
```

---

## Deployment Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed from requirements.txt
- [ ] `.env` file configured with platform-specific paths
- [ ] SECRET_KEY and JWT_SECRET set to secure random values
- [ ] Required directories created with proper permissions
- [ ] Cross-platform compatibility test passed
- [ ] All pytest tests passing
- [ ] Health check endpoints responding
- [ ] Service configured to start on boot (systemd/NSSM)
- [ ] Firewall rules configured
- [ ] Log rotation configured
- [ ] Monitoring/alerting configured

---

## Additional Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **psutil Documentation**: https://psutil.readthedocs.io/
- **pytest Documentation**: https://docs.pytest.org/
- **Python Path Documentation**: https://docs.python.org/3/library/pathlib.html

---

## Support

For platform-specific issues:
- Check `test_cross_platform.py` output
- Review logs in `logs/nui.log`
- Verify health status at `/api/v1/health`
- Check system info in health response for platform detection
