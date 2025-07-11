# Versioning Strategy

This project uses **Git tags as the source of truth** for versioning, following semantic versioning principles. **Versioning is now fully automatic** - no manual intervention required.

## 🏷️ Version Format

Versions follow the format: `vX.Y.Z` (e.g., `v1.2.3`)

- **Major (X)**: Breaking changes, incompatible API changes
- **Minor (Y)**: New features, backward-compatible additions
- **Patch (Z)**: Bug fixes, backward-compatible changes

## 🚀 Current Version

**Current version: `v1.0.7`**

The next version will be determined by your commit message when you push to the CI/CD branch.

## 🔄 Version Detection Priority

The system detects versions in this order:

1. **Environment Variable**: `PACKAGE_VERSION` (set by CI/CD)
2. **Git Tags**: Latest semantic version tag (e.g., `v1.2.3`)
3. **Fallback**: `1.0.0` if no tags exist

## 🚀 Automatic Versioning

### How It Works

1. **Push to CI/CD branch** triggers automatic version bump
2. **Version is incremented** according to commit messages:
   - `feat:` → Minor version bump (1.0.7 → 1.1.0)
   - `fix:` → Patch version bump (1.0.7 → 1.0.8)
   - `BREAKING CHANGE:` → Major version bump (1.0.7 → 2.0.0)
   - Other commits → Patch version bump (1.0.7 → 1.0.8)
3. **New tag is created** and pushed automatically
4. **Single version is published** to all platforms

### Commit Message Examples

| Commit Message | Version Bump | New Version |
|----------------|--------------|-------------|
| `feat: add new dashboard` | Minor | 1.0.7 → 1.1.0 |
| `fix: resolve login bug` | Patch | 1.0.7 → 1.0.8 |
| `BREAKING CHANGE: API redesign` | Major | 1.0.7 → 2.0.0 |
| `docs: update README` | Patch | 1.0.7 → 1.0.8 |

### No Manual Versioning Required

- ❌ No manual `git tag` commands needed
- ❌ No manual version file updates
- ❌ No manual bump script usage
- ✅ Just push to CI/CD branch and versioning happens automatically

## 📦 Package Versioning

### Python Package

The Python package version is automatically extracted from Git tags:

```python
from src import __version__
print(__version__)  # e.g., "1.0.7"
```

### Docker Images

Only **one production image** is published per version:

```bash
# Latest version
docker pull akshaychikhalkar/carla-driving-simulator-client:latest

# Specific version
docker pull akshaychikhalkar/carla-driving-simulator-client:1.0.7
```

## 🔧 CI/CD Integration

The GitHub Actions workflow:

1. **Automatically bumps versions** on every CI/CD branch push
2. **Creates single version** for each release
3. **Prevents duplicate publishing** - checks if version already exists
4. **Publishes to all platforms** with the same version
5. **Creates GitHub releases** automatically

## 🛡️ Duplicate Prevention

The workflow includes checks to prevent duplicate publishing:

- **Docker Hub**: Checks if image version already exists
- **PyPI**: Uses `--skip-existing` flag to skip duplicates
- **GitHub Releases**: Checks if release already exists

## 📋 Version Management Commands

```bash
# List all version tags
git tag --list "v*"

# Show current version
git describe --tags --match "v[0-9]*" --abbrev=0

# Check if a version exists
git tag -l v1.0.7
```

## 🎯 Best Practices

1. **Use conventional commits** for automatic version bumping:
   - `feat: add new feature` → Minor version bump
   - `fix: resolve bug` → Patch version bump
   - `BREAKING CHANGE: major change` → Major version bump

2. **Push to CI/CD branch** to trigger automatic release

3. **No manual versioning** - let the system handle it

4. **Test thoroughly** before pushing to CI/CD branch

## 🔍 Version History

View version history:
- [GitHub Releases](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/releases)
- [PyPI Package](https://pypi.org/project/carla-driving-simulator-client/)
- [Docker Hub](https://hub.docker.com/r/akshaychikhalkar/carla-driving-simulator-client)

## 🚫 What's No Longer Needed

- ❌ Manual `git tag` commands
- ❌ VERSION file maintenance
- ❌ Manual version bumping scripts
- ❌ Manual release creation
- ❌ Multiple Docker image tags per version 