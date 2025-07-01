#!/bin/bash
# Project cleanup script

echo "======================================"
echo "Project Cleanup Script"
echo "======================================"
echo ""

# Function to calculate directory size
get_size() {
    du -sh "$1" 2>/dev/null | cut -f1
}

# Current project size
TOTAL_SIZE=$(get_size ".")
echo "Current project size: $TOTAL_SIZE"
echo ""

# Basic cleanup (always safe)
echo "1. Basic cleanup (safe to run anytime):"
echo "======================================="
find . -name "*.pyc" -delete 2>/dev/null
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name ".DS_Store" -delete 2>/dev/null
find . -name "*.log" -not -path "./logs/*" -delete 2>/dev/null
echo "✓ Removed Python cache files"
echo "✓ Removed OS-specific files"
echo "✓ Removed stray log files"
echo ""

# Optional cleanup
echo "2. Optional cleanup (you can choose):"
echo "====================================="

# Check exports
if [ -d "exports" ] && [ "$(ls -A exports/)" ]; then
    EXPORT_SIZE=$(get_size "exports")
    echo ""
    echo "Old database exports found: $EXPORT_SIZE"
    read -p "Remove old exports? (can be regenerated with export_database.py) [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf exports/json/*.json exports/csv/*.csv
        echo "✓ Removed old exports"
    fi
fi

# Check dashboard build files
if [ -d "dashboard/.next" ]; then
    NEXT_SIZE=$(get_size "dashboard/.next")
    echo ""
    echo "Dashboard build cache found: $NEXT_SIZE"
    read -p "Remove Next.js build cache? (will be regenerated on next build) [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf dashboard/.next
        echo "✓ Removed Next.js cache"
    fi
fi

# Check node_modules (biggest space saver)
if [ -d "dashboard/node_modules" ]; then
    NODE_SIZE=$(get_size "dashboard/node_modules")
    echo ""
    echo "Node modules found: $NODE_SIZE"
    read -p "Remove node_modules? (run 'npm install' in dashboard/ to restore) [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf dashboard/node_modules
        echo "✓ Removed node_modules"
        echo "  To restore: cd dashboard && npm install"
    fi
fi

# Check old database backups
if ls db/*.backup_* 1> /dev/null 2>&1; then
    BACKUP_COUNT=$(ls -1 db/*.backup_* 2>/dev/null | wc -l | tr -d ' ')
    echo ""
    echo "Found $BACKUP_COUNT database backup(s)"
    read -p "Remove old database backups? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f db/*.backup_*
        echo "✓ Removed database backups"
    fi
fi

# Final size
echo ""
echo "======================================"
NEW_SIZE=$(get_size ".")
echo "Project size after cleanup: $NEW_SIZE"
echo "Space saved: (was $TOTAL_SIZE)"
echo ""

# Summary of what's kept
echo "Important files preserved:"
echo "- All scripts in scripts/"
echo "- All documentation in docs/"
echo "- Configuration files and examples"
echo "- Current database (db/branch_wise_location.db)"
echo "- Data files (data/)"
echo "- Branch reports (branch_reports/)"
echo ""

echo "To further reduce size, you can:"
echo "1. Archive old branch reports"
echo "2. Compress the JSONL data file"
echo "3. Move database backups to external storage" 