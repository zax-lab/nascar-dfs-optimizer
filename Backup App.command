#!/bin/bash
cd "$(dirname "$0")"

# Create backup filename with date
BACKUP_NAME="NASCAR-DFS-Optimizer-$(date +%Y%m%d)"

echo "Creating backup: ${BACKUP_NAME}.zip"

# Create zip with all necessary files
zip -r "${BACKUP_NAME}.zip" \
    .venv/ \
    apps/native_mac/ \
    packages/ \
    "Launch App.command" \
    "Backup App.command" \
    "LAUNCH_SCRIPT_README.md" \
    -x "*.DS_Store" \
    -x "*__pycache__/*" \
    -x "*.pyc" \
    -x "*.log" \
    -x "*/dist/*" \
    -x "*/build/*" \
    -x "*/.eggs/*"

if [ $? -eq 0 ]; then
    echo "✅ Backup created: ${BACKUP_NAME}.zip"
    echo "Size: $(du -h "${BACKUP_NAME}.zip" | cut -f1)"
else
    echo "❌ Backup failed!"
fi

read -p "Press Enter to exit..."
