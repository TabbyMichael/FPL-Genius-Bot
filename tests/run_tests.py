#!/usr/bin/env python3
"""
Script to run all tests for the FPL bot
"""

import subprocess
import sys
import os

def run_tests():
    """Run all tests with pytest"""
    print("Running FPL Bot Tests")
    print("=" * 30)
    
    # Change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Run pytest with coverage
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--cov=services",
            "--cov-report=term-missing"
        ], cwd=project_dir)
        
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: pytest not found. Please install test dependencies:")
        print("pip install -r requirements-dev.txt")
        return False
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

def run_linting():
    """Run code linting"""
    print("\nRunning Code Linting")
    print("=" * 30)
    
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Run flake8
    try:
        result = subprocess.run([
            sys.executable, "-m", "flake8",
            "services/",
            "config/",
            "utils/",
            "tests/"
        ], cwd=project_dir)
        
        return result.returncode == 0
    except FileNotFoundError:
        print("Warning: flake8 not found. Skipping linting.")
        return True
    except Exception as e:
        print(f"Error running linting: {e}")
        return False

def main():
    """Main function"""
    print("FPL Bot Test Suite")
    print("=" * 50)
    
    # Run tests
    tests_passed = run_tests()
    
    # Run linting
    linting_passed = run_linting()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Suite Summary")
    print("=" * 50)
    print(f"Tests: {'PASSED' if tests_passed else 'FAILED'}")
    print(f"Linting: {'PASSED' if linting_passed else 'SKIPPED/WARNING'}")
    
    if tests_passed:
        print("\nAll tests passed! ✓")
        return 0
    else:
        print("\nSome tests failed! ✗")
        return 1

if __name__ == "__main__":
    sys.exit(main())