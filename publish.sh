#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if version argument is provided
if [ -z "$1" ]; then
    print_error "Please provide a version number (e.g., ./publish.sh 1.0.1)"
    exit 1
fi

NEW_VERSION=$1

# Validate version format (x.y.z)
if ! [[ $NEW_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    print_error "Invalid version format. Please use x.y.z format (e.g., 1.0.1)"
    exit 1
fi

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "git is not installed"
    exit 1
fi

# Check if twine is installed
if ! command -v twine &> /dev/null; then
    print_warning "twine is not installed. Installing..."
    pip install twine
fi

# Check if build is installed
if ! command -v python -m pip show build &> /dev/null; then
    print_warning "build is not installed. Installing..."
    pip install build
fi

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree &> /dev/null; then
    print_error "Not a git repository"
    exit 1
fi

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    print_warning "You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Update VERSION file
print_message "Updating VERSION file to $NEW_VERSION"
echo $NEW_VERSION > VERSION

# Commit version change
print_message "Committing version change"
git add VERSION
git commit -m "Bump version to $NEW_VERSION"

# Create git tag
print_message "Creating git tag v$NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"

# Build package
print_message "Building package"
python -m build

# Upload to PyPI
print_message "Uploading to PyPI"
twine upload dist/*

# Push changes and tag to remote
print_message "Pushing changes and tag to remote"
git push origin master
git push origin "v$NEW_VERSION"

print_message "Release $NEW_VERSION completed successfully!"
print_message "Don't forget to create a release on GitHub with release notes." 