# NUI Release Scripts

This directory contains scripts to create versioned release archives of the NUI project.

## Available Scripts

### 1. create_release.py (Recommended - Cross-platform)
**Python-based release creator**
- ✓ Works on Windows, Linux, and macOS
- ✓ No external dependencies
- ✓ Pure Python implementation

**Usage:**
```bash
python create_release.py
```

### 2. create_release.sh (Linux/Unix/macOS)
**Bash script for Unix-like systems**
- Requires: bash, rsync, tar
- Best for Linux servers and CI/CD pipelines

**Usage:**
```bash
chmod +x create_release.sh
./create_release.sh
```

### 3. create_release.bat (Windows)
**Windows batch script**
- Requires: Windows 10+ (includes tar by default)
- Alternative: Git Bash or WSL

**Usage:**
```cmd
create_release.bat
```

## Output

All scripts create a versioned archive in the parent directory:
```
NUI_v0.0.0.1.tar.gz
```

## Archive Contents

The archive includes:
- ✓ All Python scripts (app.py, convert.py, reconvert.py, etc.)
- ✓ HTML frontend (NUI.html)
- ✓ Documentation (docs/)
- ✓ Topology files (Topology/)
- ✓ Link test configs (link_test_configs/)
- ✓ FBOSS source files (fboss_src/)
- ✓ Requirements (requirements.txt)
- ✓ VERSION file
- ✓ RELEASE_INFO.txt

## Excluded Files

The following are automatically excluded:
- `__pycache__/` - Python cache directories
- `*.pyc, *.pyo, *.pyd` - Python compiled files
- `.git/` - Git repository data
- `.vscode/, .idea/` - IDE configurations
- `*.log, *.tmp` - Temporary and log files
- `venv/, .venv/, env/` - Virtual environments
- Swap files and system files

## Version Control

The current version is defined at the top of each script:
```bash
VERSION = "v0.0.0.1"    # Python
VERSION="v0.0.0.1"      # Bash
SET VERSION=v0.0.0.1    # Batch
```

**To create a new release:**
1. Update the VERSION in all three scripts
2. Update docs/SPEC.md and docs/convert_reconvert_SPEC.md version history
3. Run the appropriate release script for your platform
4. Distribute the generated .tar.gz file

## Installation from Archive

Recipients can install the release as follows:

```bash
# Extract archive
tar -xzf NUI_v0.0.0.1.tar.gz

# Navigate to directory
cd NUI_v0.0.0.1

# Install dependencies
pip install -r requirements.txt

# Run application
python app.py
```

## Verification

After creating the archive, you can verify its contents:

```bash
# List all files
tar -tzf NUI_v0.0.0.1.tar.gz

# Extract to temporary location for testing
tar -xzf NUI_v0.0.0.1.tar.gz -C /tmp/
```

## Notes

- Archives are created in the parent directory (one level up from NUI/)
- VERSION and RELEASE_INFO.txt files are automatically generated
- All scripts produce the same archive format
- The Python script (create_release.py) is recommended for maximum compatibility

## Troubleshooting

### "tar command not found" (Windows)
- Use Windows 10 or later (includes tar)
- Or use Git Bash / WSL
- Or use the Python script instead

### "rsync: command not found" (Unix)
- Install rsync: `sudo apt-get install rsync` (Ubuntu/Debian)
- Or use the Python script instead

### Permission denied (Linux/Mac)
```bash
chmod +x create_release.sh
```

---

**Last Updated:** 2025-12-25  
**Version:** v0.0.0.1
