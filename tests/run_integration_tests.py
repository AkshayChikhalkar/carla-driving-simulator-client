#!/usr/bin/env python3
"""
Integration test runner for CARLA Driving Simulator Client.

This script runs integration tests with proper setup and teardown.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def setup_test_environment():
    """Setup the test environment."""
    print("🔧 Setting up test environment...")
    
    # Set test environment variables
    os.environ.update({
        "TESTING": "true",
        "DATABASE_URL": "sqlite:///:memory:",
        "CONFIG_TENANT_ID": "1",
        "WEB_FILE_LOGS_ENABLED": "false",
        "DISABLE_AUTH_FOR_TESTING": "true",
        "PYTHONPATH": str(Path(__file__).parent.parent)
    })
    
    print("✅ Test environment setup complete")


def run_integration_tests(test_path=None, verbose=False, coverage=False):
    """Run integration tests."""
    print("🚀 Running integration tests...")
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "--tb=short",
        "--strict-markers"
    ]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=tests",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    # Add test path
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/test_integration.py")
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Run tests
    try:
        result = subprocess.run(cmd, check=True, capture_output=not verbose)
        print("✅ Integration tests completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Integration tests failed with exit code {e.returncode}")
        if not verbose and e.stdout:
            print("STDOUT:", e.stdout.decode())
        if not verbose and e.stderr:
            print("STDERR:", e.stderr.decode())
        return False


def cleanup_test_environment():
    """Cleanup the test environment."""
    print("🧹 Cleaning up test environment...")
    
    # Remove test artifacts
    test_artifacts = [
        "test_integration.log",
        "htmlcov/",
        ".coverage",
        "reports/"
    ]
    
    for artifact in test_artifacts:
        if os.path.exists(artifact):
            if os.path.isdir(artifact):
                import shutil
                shutil.rmtree(artifact)
            else:
                os.remove(artifact)
    
    print("✅ Test environment cleanup complete")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument(
        "--test-path", 
        help="Path to specific test file or directory"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true", 
        help="Generate coverage report"
    )
    parser.add_argument(
        "--no-cleanup", 
        action="store_true", 
        help="Skip cleanup after tests"
    )
    
    args = parser.parse_args()
    
    try:
        # Setup
        setup_test_environment()
        
        # Run tests
        success = run_integration_tests(
            test_path=args.test_path,
            verbose=args.verbose,
            coverage=args.coverage
        )
        
        # Cleanup
        if not args.no_cleanup:
            cleanup_test_environment()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        cleanup_test_environment()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        cleanup_test_environment()
        sys.exit(1)


if __name__ == "__main__":
    main()
