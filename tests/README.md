# Integration Tests

This directory contains integration tests for the CARLA Driving Simulator Client.

## Overview

Integration tests verify the interaction between different components of the system:

- **Database Integration**: Tests database models and operations
- **Configuration Integration**: Tests config loading and validation
- **Web Backend Integration**: Tests API endpoints and services
- **CLI Integration**: Tests command-line interface
- **Simulation Integration**: Tests simulation runner
- **Docker Integration**: Tests container management
- **API Integration**: Tests HTTP endpoints
- **End-to-End Integration**: Tests complete workflows

## Test Structure

```
tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Test configuration and fixtures
├── test_integration.py         # Main integration test suite
├── run_integration_tests.py    # Test runner script
└── README.md                   # This file
```

## Running Integration Tests

### Using pytest directly:
```bash
# Run all integration tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=tests --cov-report=html

# Run specific test class
pytest tests/test_integration.py::TestDatabaseIntegration

# Run specific test method
pytest tests/test_integration.py::TestDatabaseIntegration::test_database_user_tenant_integration
```

### Using the test runner script:
```bash
# Run all integration tests
python tests/run_integration_tests.py

# Run with verbose output
python tests/run_integration_tests.py -v

# Run with coverage
python tests/run_integration_tests.py --coverage

# Run specific test file
python tests/run_integration_tests.py --test-path tests/test_integration.py
```

## Test Categories

### 1. Database Integration Tests
- User and tenant creation/association
- Configuration storage and retrieval
- Database connection management

### 2. Configuration Integration Tests
- Config loader with database integration
- Configuration validation across components
- Environment variable handling

### 3. Web Backend Integration Tests
- Runner registry operations
- CARLA pool management
- API endpoint testing

### 4. CLI Integration Tests
- Command-line interface with configuration
- CLI with database integration
- Error handling

### 5. Simulation Integration Tests
- Simulation runner with configuration
- Component initialization and cleanup
- Resource management

### 6. End-to-End Integration Tests
- Complete workflow testing
- Error handling across components
- System resilience

### 7. Docker Integration Tests
- Container lifecycle management
- Docker Compose integration
- Resource cleanup

### 8. API Integration Tests
- Health check endpoints
- Configuration endpoints
- HTTP response validation

## Test Fixtures

The `conftest.py` file provides several fixtures:

- `test_config`: Standard test configuration
- `mock_database`: Mock database manager
- `mock_config_loader`: Mock configuration loader
- `mock_simulation_runner`: Mock simulation runner
- `temp_test_dir`: Temporary directory for test files
- `clean_environment`: Clean environment variables
- `integration_test_data`: Test data for integration scenarios

## Environment Variables

Integration tests use the following environment variables:

- `TESTING=true`: Enables test mode
- `DATABASE_URL=sqlite:///:memory:`: Uses in-memory database
- `CONFIG_TENANT_ID=1`: Sets default tenant ID
- `WEB_FILE_LOGS_ENABLED=false`: Disables file logging
- `DISABLE_AUTH_FOR_TESTING=true`: Disables authentication

## Mocking Strategy

Integration tests use extensive mocking to:

1. **Isolate Components**: Test component interactions without external dependencies
2. **Control Behavior**: Simulate various scenarios (success, failure, errors)
3. **Speed Up Tests**: Avoid slow external operations
4. **Ensure Reliability**: Make tests deterministic

## Coverage

Integration tests aim to cover:

- ✅ Component interactions
- ✅ Data flow between modules
- ✅ Error handling across boundaries
- ✅ Configuration propagation
- ✅ Resource management
- ✅ API contract validation

## Best Practices

1. **Use Descriptive Test Names**: Test names should clearly describe what is being tested
2. **Test Both Success and Failure**: Include positive and negative test cases
3. **Mock External Dependencies**: Don't rely on external services
4. **Clean Up Resources**: Ensure proper cleanup in test teardown
5. **Use Fixtures**: Leverage pytest fixtures for common setup
6. **Test Realistic Scenarios**: Focus on realistic integration scenarios

## Troubleshooting

### Common Issues:

1. **Import Errors**: Ensure all required packages are installed
2. **Mock Issues**: Check that mocks are properly configured
3. **Environment Issues**: Verify environment variables are set correctly
4. **Resource Cleanup**: Ensure tests clean up after themselves

### Debug Mode:

Run tests with verbose output to see detailed information:

```bash
pytest tests/ -v -s --tb=long
```

## Contributing

When adding new integration tests:

1. Follow the existing test structure
2. Use appropriate mocking
3. Add descriptive docstrings
4. Include both success and failure cases
5. Update this README if adding new test categories
