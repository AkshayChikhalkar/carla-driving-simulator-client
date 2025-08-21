# GitHub Actions Workflows

This directory contains the GitHub Actions workflows for the CARLA Driving Simulator Client project.

## Workflow Overview

### 1. `test-comprehensive.yml` - Comprehensive Test Suite
**Purpose**: Runs all tests in parallel for comprehensive validation
**Triggers**: 
- Pull requests to `master` or `develop` branches
- Manual dispatch

**Features**:
- ✅ **Parallel Execution**: All test suites run simultaneously for faster feedback
- ✅ **Comprehensive Coverage**: Tests all components (Carla Simulator, Web Backend, Frontend, Integration)
- ✅ **Detailed Reporting**: HTML test reports and coverage metrics
- ✅ **Artifact Management**: Test results and coverage reports saved as artifacts
- ✅ **Test Summary**: Consolidated summary of all test results

**Jobs**:
1. `test-carla-simulator` - Tests for Carla Simulator components
2. `test-web-backend` - Tests for Web Backend components  
3. `test-frontend` - Tests for Frontend components
4. `test-integration` - Integration tests (if any)
5. `test-summary` - Generates comprehensive test summary

### 2. `test-frontend.yml` - Frontend Tests (Quick)
**Purpose**: Quick frontend-only testing for frontend-specific changes
**Triggers**:
- Pull requests with changes only in `web/frontend/**`
- Manual dispatch

**Features**:
- ⚡ **Fast Execution**: Only runs frontend tests
- 🎯 **Targeted**: Triggers only on frontend changes
- 📊 **Coverage**: Includes test coverage reporting

### 3. `build-publish-release.yml` - Production CI/CD Pipeline
**Purpose**: Production build, test, and release pipeline
**Triggers**:
- Push to `master` branch (Production)
- Manual dispatch with configurable options

### 4. `build-dev.yml` - Development CI/CD Pipeline
**Purpose**: Development build and test pipeline
**Triggers**:
- Push to `develop` branch (Development)
- Manual dispatch with configurable options

**Features**:
- 🧪 **Testing First**: All tests must pass before any build/publish steps
- 📦 **Multi-Platform Publishing**: Docker images and PyPI packages
- 🏷️ **Version Management**: Automated version bumping and tagging
- 🚀 **Release Management**: Automated GitHub releases

**Production Phases**:
1. **Testing Phase**: Comprehensive test execution
2. **Version Bump Phase**: Automated version management
3. **Build Phase**: Documentation and Docker build validation
4. **Publish Phase**: PyPI and Docker Hub publishing
5. **Release Phase**: GitHub release creation with documentation

**Development Phases**:
1. **Testing Phase**: Comprehensive test execution
2. **Build Phase**: Documentation and Docker build validation
3. **Publish Phase**: Docker Hub publishing (development images)

### 5. `build-docs.yml` - Documentation Build
**Purpose**: Builds comprehensive documentation with automated generation
**Triggers**:
- Pull requests with changes in `docs/**`, `carla_simulator/**`, `web/**`, or Python files
- Manual dispatch

**Features**:
- 📚 **Automated Generation**: Uses `docs/auto_generate_docs.py` for comprehensive docs
- 🎨 **Mermaid Diagrams**: Converts .mmd files to PNG images
- 🔧 **API Documentation**: Auto-generates API reference from code
- 📖 **Sphinx Build**: Creates HTML documentation
- 🌐 **GitHub Pages**: Optional deployment to GitHub Pages
- 📦 **Artifact Management**: Documentation available as artifacts

**Jobs**:
1. `build-documentation` - Builds comprehensive documentation
2. `deploy-to-pages` - Deploys to GitHub Pages (optional)

### 6. `deploy-carla-server.yml` - CARLA Server Deployment
**Purpose**: Deploys CARLA simulator server to remote infrastructure
**Triggers**:
- Push to `gui` branch
- Manual dispatch

**Features**:
- 🔐 **Secure Deployment**: VPN-based secure deployment
- 🐳 **Docker-Based**: Uses Docker Compose for deployment
- 🏥 **Health Checks**: Validates server health after deployment

## Workflow Trigger Strategy

### **No Duplicate Triggers - Hierarchical Approach**

To prevent duplicate workflow execution, we use a **hierarchical trigger strategy**:

| Event | Primary Workflow | Secondary Workflows | Purpose |
|-------|------------------|-------------------|---------|
| **Pull Request Created/Updated** | `test-comprehensive.yml` | `test-frontend.yml` (if frontend changes)<br>`build-docs.yml` (if docs changes) | **Validation only** |
| **PR Merged to `master`** | `build-publish-release.yml` | None | **Production build + release** |
| **Direct Push to `master`** | `build-publish-release.yml` | None | **Production build + release** |
| **Push to `develop`** | `build-dev.yml` | None | **Development build** |
| **Manual Dispatch** | Any workflow | None | **On-demand execution** |

### **Key Principles:**

1. **Pull Request Events**: Trigger validation workflows only
   - `test-comprehensive.yml` (always)
   - `test-frontend.yml` (only if frontend files changed)
   - `build-docs.yml` (only if docs/code files changed)

2. **Merge/Push Events**: Trigger production/development builds
   - PR merged to `master` → `build-publish-release.yml` (includes testing)
   - Direct push to `master` → `build-publish-release.yml` (includes testing)
   - Push to `develop` → `build-dev.yml` (includes testing)

3. **No Duplicate Testing**: Each event triggers exactly one comprehensive test suite

### **Benefits:**
- ✅ **No Duplicate Testing**: Each event triggers only one comprehensive test suite
- ✅ **Faster Feedback**: No competing workflows consuming resources
- ✅ **Clear Separation**: PR validation vs. production/development builds
- ✅ **Efficient Resource Usage**: Prevents GitHub Actions runner conflicts

### **Workflow Execution Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW EXECUTION FLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔵 PULL REQUEST CREATED/UPDATED                               │
│  └─→ test-comprehensive.yml (validation only)                  │
│     ├─→ test-frontend.yml (if frontend changes)                │
│     └─→ build-docs.yml (if docs/code changes)                  │
│                                                                 │
│  🟢 PR MERGED TO MASTER                                        │
│  └─→ build-publish-release.yml (production build + release)    │
│     ├─→ Tests → Version Bump → Build → Publish → Release       │
│     └─→ (includes all testing and documentation)               │
│                                                                 │
│  🟡 DIRECT PUSH TO MASTER                                      │
│  └─→ build-publish-release.yml (production build + release)    │
│     ├─→ Tests → Version Bump → Build → Publish → Release       │
│     └─→ (includes all testing and documentation)               │
│                                                                 │
│  🟠 PUSH TO DEVELOP                                           │
│  └─→ build-dev.yml (development build)                         │
│     ├─→ Tests → Build → Publish (Docker only)                  │
│     └─→ (includes all testing and documentation)               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Branch-Based Strategy

### **Production vs Development Workflows**

| Branch | Workflow | Purpose | Docker Tags | Release |
|--------|----------|---------|-------------|---------|
| `master` | `build-publish-release.yml` | Production builds | `latest`, `v1.2.3`, `prod-abc123` | ✅ Full release |
| `develop` | `build-dev.yml` | Development builds | `dev`, `dev-abc123`, `develop` | ❌ No release |

### **Key Differences**

**Production (`master` branch)**:
- ✅ **Version Bumping**: Automated semantic versioning
- ✅ **PyPI Publishing**: Python packages published to PyPI
- ✅ **GitHub Releases**: Complete release with assets
- ✅ **Production Tags**: `latest`, version tags, production-specific tags
- ✅ **Full Documentation**: Complete documentation build and release

**Development (`develop` branch)**:
- ❌ **No Version Bumping**: Uses git commit hashes
- ❌ **No PyPI Publishing**: Only Docker images
- ❌ **No GitHub Releases**: No formal releases
- ✅ **Development Tags**: `dev`, `develop`, development-specific tags
- ✅ **Documentation**: Builds but doesn't release

## Test Structure

The test suites are organized by component:

```
carla_simulator/tests/          # Carla Simulator tests
├── test_carla_core.py         # Core simulation tests
├── test_database_models.py    # Database model tests
├── test_utils.py              # Utility function tests
├── test_core.py               # Core functionality tests
├── test_scenarios.py          # Scenario tests
└── conftest.py                # Test configuration

web/backend/tests/              # Web Backend tests
├── test_web_backend.py        # Backend API tests
└── conftest.py                # Test configuration
```

## Parallel Execution Benefits

### Before (Sequential)
```
Test Backend → Test Frontend → Build → Publish
     ↓              ↓           ↓        ↓
   30s           45s         60s     30s
Total: ~165 seconds
```

### After (Parallel)
```
Test Backend ─┐
Test Frontend ─┼─→ Build → Publish
Test Integration ┘
     ↓              ↓        ↓
   30s           60s     30s
Total: ~120 seconds (27% faster)
```

## Configuration

### Environment Variables
- `PYTHON_VERSION`: "3.11"
- `NODE_VERSION`: "18"
- `DOCKER_IMAGE`: "akshaychikhalkar/carla-driving-simulator-client"

### Required Secrets
- `CODECOV_TOKEN`: For test coverage reporting
- `DOCKER_USERNAME` & `DOCKER_PASSWORD`: For Docker Hub publishing
- `PYPI_USERNAME` & `PYPI_PASSWORD`: For PyPI publishing
- `GITHUB_TOKEN`: For GitHub operations (auto-provided)

## Usage

### For Developers
1. **Frontend Changes**: Only `test-frontend.yml` will run
2. **Backend Changes**: `test-comprehensive.yml` will run
3. **Full Pipeline**: Push to `master` triggers complete CI/CD

### For Maintainers
1. **Manual Testing**: Use workflow dispatch for specific test suites
2. **Release Management**: Automated on master branch pushes
3. **Deployment**: Manual trigger for CARLA server deployment

## Best Practices

1. **Test First**: All workflows ensure tests pass before any build/publish steps
2. **Parallel Execution**: Maximize efficiency with parallel job execution
3. **Artifact Management**: Test results and reports are preserved as artifacts
4. **Comprehensive Coverage**: Multiple test types ensure quality
5. **Fail Fast**: Early failure detection prevents wasted resources

## Monitoring

- **Test Results**: Available in workflow artifacts
- **Coverage Reports**: Uploaded to Codecov
- **Build Status**: Visible in GitHub Actions tab
- **Release Notes**: Automatically generated for releases
