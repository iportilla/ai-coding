#!/usr/bin/env python3
"""
Test runner for AWS Bedrock monitoring system.

This script provides a convenient way to run all tests with proper configuration
and reporting. It supports different test types and verbosity levels.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, check=True, cwd=Path(__file__).parent)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"✗ Command not found: {command[0]}")
        print("Please ensure pytest is installed: pip install -r requirements.txt")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run AWS Bedrock monitoring tests")
    parser.add_argument(
        "--type", 
        choices=["unit", "property", "integration", "all"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test type filter
    if args.type != "all":
        cmd.extend(["-m", args.type])
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage
    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])
    
    # Run tests
    success = run_command(cmd, f"Running {args.type} tests")
    
    if not success:
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("All tests completed successfully! ✓")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()