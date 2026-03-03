#!/bin/bash
set -e

PKG_DIR=python_crontab_offline

echo "[1/2] 離線安裝 python-crontab"
python3 -m pip install \
  --no-index \
  --no-deps \
  --find-links=${PKG_DIR} \
  six python-dateutil python-crontab

echo "[2/2] 驗證"
python3 - <<EOF
from crontab import CronTab
print("python-crontab install OK")
EOF

echo "✅ python-crontab 離線安裝完成"
