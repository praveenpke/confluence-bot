#!/bin/bash

# Clean Local Directory Script
# Removes unnecessary files from the local project directory

echo "🧹 Cleaning local directory..."

# Remove Python cache files
echo "🗑️ Removing Python cache files..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Remove OS files
echo "🗑️ Removing OS files..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true

# Remove temporary files
echo "🗑️ Removing temporary files..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
find . -name "*.log" -delete 2>/dev/null || true

# Remove archive files
echo "🗑️ Removing archive files..."
find . -name "*.tar.gz" -delete 2>/dev/null || true
find . -name "*.zip" -delete 2>/dev/null || true
find . -name "*.rar" -delete 2>/dev/null || true

# Remove deployment artifacts
echo "🗑️ Removing deployment artifacts..."
rm -rf deploy_package/ 2>/dev/null || true

echo "✅ Local directory cleaned!"
echo ""
echo "📁 Current files:"
ls -la | grep -E "^-" | wc -l | xargs echo "   Files: "
ls -la | grep -E "^d" | wc -l | xargs echo "   Directories: " 