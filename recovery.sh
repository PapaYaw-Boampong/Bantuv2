#!/bin/bash

# Stop any running servers
pkill -f "uvicorn main:app"
pkill -f "vite"

# Restore from backup
if [ -d "backups/pre-major-change-2025-05-06" ]; then
    echo "Restoring from backup..."
    rm -rf * .[!.]*
    cp -r backups/pre-major-change-2025-05-06/* .
    cp -r backups/pre-major-change-2025-05-06/.[!.]* .
    echo "Backup restored successfully"
else
    echo "Backup directory not found. Aborting recovery."
    exit 1
fi

# Reset git state
git reset --hard

echo "Recovery complete. You can now restart the servers."
