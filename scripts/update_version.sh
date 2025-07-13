#!/bin/bash

# Script to update version information during build
# Usage: ./scripts/update_version.sh <version> <build_time>

set -e

VERSION=${1:-latest}
BUILD_TIME=${2:-$(date -u +"%Y-%m-%dT%H:%M:%SZ")}

echo "Updating version information:"
echo "  Version: $VERSION"
echo "  Build Time: $BUILD_TIME"

# Update VERSION file
echo "$VERSION" > VERSION

# Create version info for frontend
mkdir -p web/frontend/public
echo "$VERSION" > web/frontend/public/version.txt

# Create version info for backend
mkdir -p src
echo "VERSION = '$VERSION'" > src/version.py
echo "BUILD_TIME = '$BUILD_TIME'" >> src/version.py

echo "Version information updated successfully" 