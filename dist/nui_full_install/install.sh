#!/bin/bash
set -e

# Installer for NUI Offline Bundle

echo "=========================================="
echo "    NUI Offline Installer"
echo "=========================================="

# 1. Unpack everything
echo "[1/3] Unpacking bundles..."

for tarball in *.tar.gz; do
    echo "  -> Extracting $tarball..."
    tar -xzf "$tarball"
done

echo "Unpacking complete."

# 2. Install RPMs (LLDPCLI and dependencies)
if [ -d "lldpcli_offline_rpm" ]; then
    echo "[2/3] Installing RPMs (lldpcli)..."
    cd lldpcli_offline_rpm
    # Using rpm -Uvh --force --nodeps as requested/standard for offline bundles with potential circular deps
    # Ideally should use 'yum localinstall' or 'dnf install' if available, but rpm is safer if repo not set up.
    # Using dnf with --disablerepo=* to ensure no network access. 
    # Fallback to rpm if dnf fails (e.g. due to missing dependencies in the bundle).
    if command -v dnf &> /dev/null; then
         echo "  -> Found dnf. Attempting offline install..."
         sudo dnf install -y --disablerepo=* ./*.rpm || sudo rpm -Uvh *.rpm --force --nodeps
    else
         echo "  -> dnf not found. Using rpm..."
         sudo rpm -Uvh *.rpm --force --nodeps
    fi
    cd ..
    echo "RPM installation complete."
else
    echo "Warning: lldpcli_offline_rpm directory not found after extraction."
fi

# 3. Install Python Packages
echo "[3/3] Installing Python Packages..."

# Helper function to install from a directory
install_wheels() {
    local dir=$1
    local pkg_name=$2
    
    if [ -d "$dir" ]; then
        echo "  -> Installing $pkg_name from $dir..."
        # If requirements.txt exists, use it
        if [ -f "$dir/requirements.txt" ]; then
            sudo python3 -m pip install --no-index --find-links="$dir" -r "$dir/requirements.txt"
        elif [ -f "$dir/wheels" ]; then
             # Some bundles might have a 'wheels' subdir (like flask-offline-install saw earlier)
             sudo python3 -m pip install --no-index --find-links="$dir/wheels" $pkg_name
        else
            # Try to install everything in the dir or specific package
            # Since we don't know exact package name for 'pandas_offline_pkg' if it differs,
            # we rely on pip finding the package in the dir. 
            # If no requirements file, we might assume the package name matches the dir prefix or just point to dir.
            # Best is to point --find-links to the dir and specify the package name if known, OR install all whl files.
            sudo python3 -m pip install --no-index --find-links="$dir" $pkg_name
        fi
    else
        echo "Warning: Directory $dir not found."
    fi
}

# Install Pandas
install_wheels "pandas_offline_pkg" "pandas"

# Install Flask (flask-offline-install might have a wheels subdir, based on previous ls)
if [ -d "flask-offline-install/wheels" ]; then
    echo "  -> Installing Flask dependencies..."
    sudo python3 -m pip install --no-index --find-links="flask-offline-install/wheels" Flask
elif [ -d "flask-offline-install" ]; then
     install_wheels "flask-offline-install" "Flask"
fi

# Install Requests
install_wheels "requests_offline_pkg" "requests"

# Install XlsxWriter
install_wheels "xlsxwriter_offline_pkg" "XlsxWriter"

# Install NUI Bundle (custom bundle)
if [ -d "nui_offline_bundle" ]; then
    echo "  -> Installing NUI Bundle..."
    if [ -f "nui_offline_bundle/requirements.txt" ]; then
         sudo python3 -m pip install --no-index --find-links="nui_offline_bundle/pkgs" -r "nui_offline_bundle/requirements.txt"
    elif [ -f "nui_offline_bundle/install.sh" ]; then
         # If it has its own install script, maybe use it? But better to control here.
         # Let's trust the structure we saw in fask-lmiter.sh: pkgs dir and requirements.txt
         if [ -d "nui_offline_bundle/pkgs" ]; then
             sudo python3 -m pip install --no-index --find-links="nui_offline_bundle/pkgs" Flask Flask-Limiter psutil
         fi
    fi
fi


# 4. Cleanup
echo "[4/4] Cleaning up..."
rm -rf lldpcli_offline_rpm
rm -rf pandas_offline_pkg
rm -rf flask-offline-install
rm -rf requests_offline_pkg
rm -rf xlsxwriter_offline_pkg
rm -rf nui_offline_bundle

echo "=========================================="
echo "    Installation Complete!"
echo "=========================================="
