# AWS Bedrock Monitoring System - Project Structure

## Overview

This document describes the project structure and testing framework setup for the AWS Bedrock monitoring system. The project follows Python best practices with comprehensive testing using both unit tests and property-based testing.

## Directory Structure

```
aws-bedrock-monitoring/
├── src/                          # Source code modules
│   ├── __init__.py              # Package initialization
│   ├── config.py                # Configuration management
│   └── utils.py                 # Shared utility functions
├── tests/                       # Test suite
│   ├── __init__.py              # Test package initialization
│   ├── conftest.py              # Pytest configuration and fixtures
│   ├── test_config.py           # Unit tests for configuration
│   ├── test_iam_role.py         # Unit tests for IAM role
│   ├── test_integration.py      # Unit tests for integration
│   ├── test_utils.py            # Unit tests for utilities
│   └── test_properties.py       # Property-based tests
├── scripts/                     # Deployment scripts (existing)
│   ├── 0-setup-all.sh
│   ├── 1-setup-iam-role.sh
│   ├── 2-create-s3-bucket.sh
│   ├── 3-enable-bedrock-logging.sh
│   ├── 4-create-cloudwatch-dashboard.sh
│   ├── 5-create-cloudwatch-alarms.sh
│   ├── 6-usage-report.py
│   └── 7-cleanup-resources.sh
├── requirements.txt             # Python dependencies
├── pytest.ini                  # Pytest configuration
├── run_tests.py                 # Test runner script
└── README.md                    # Main documentation
```

## Key Components

### Configuration Management (`src/config.py`)

Provides centralized configuration for all monitoring components:

- **IAMConfig**: IAM role and permissions settings
- **StorageConfig**: S3 and CloudWatch log storage configuration
- **AlertingConfig**: CloudWatch alarms and SNS notification settings
- **DashboardConfig**: CloudWatch dashboard configuration
- **MonitoringConfiguration**: Complete system configuration

Features:
- Environment variable support
- Account-specific resource naming
- Type-safe configuration with dataclasses
- JSON serialization for external tools

### Utility Functions (`src/utils.py`)

Common utilities for AWS operations and validation:

- **AWS CLI Integration**: Execute AWS commands with error handling
- **Validation Functions**: Validate AWS account IDs, regions, and resource names
- **Resource Management**: Check resource existence and handle conflicts
- **JSON Utilities**: Safe parsing and formatting
- **Error Handling**: Custom exceptions and logging

### Testing Framework

#### Unit Tests
- **test_config.py**: Tests configuration classes and environment handling
- **test_utils.py**: Tests validation functions and utilities
- Comprehensive coverage of edge cases and error conditions

#### Property-Based Tests (`test_properties.py`)
Uses Hypothesis framework to test universal properties:

- **Configuration Integrity**: Ensures configurations are always valid
- **Validation Consistency**: Tests validation functions across all inputs
- **JSON Round-trip**: Verifies JSON serialization/deserialization
- **Naming Conventions**: Tests AWS resource naming patterns

## Testing Configuration

### Pytest Setup (`pytest.ini`)
- Configured for verbose output and coverage reporting
- Custom markers for different test types (unit, property, integration, slow)
- Hypothesis integration with statistics reporting
- HTML coverage reports generated in `htmlcov/`

### Test Fixtures (`tests/conftest.py`)
Provides reusable test data:
- Sample AWS account IDs and regions
- Pre-configured configuration objects
- Mock AWS responses for testing

### Hypothesis Configuration
- Default: 100 examples per property test
- CI profile: 1000 examples for thorough testing
- Dev profile: 10 examples for fast development

## Dependencies

### Core Dependencies
- **hypothesis**: Property-based testing framework
- **pytest**: Test runner and framework
- **pytest-cov**: Coverage reporting

### Optional Dependencies
- **boto3**: AWS SDK for enhanced testing (optional)

## Running Tests

### Using the Test Runner
```bash
# Run all tests
python run_tests.py

# Run specific test types
python run_tests.py --type unit
python run_tests.py --type property
python run_tests.py --type integration

# Run with coverage
python run_tests.py --coverage --verbose
```

### Using Pytest Directly
```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_config.py
pytest tests/test_properties.py

# Run with markers
pytest -m unit
pytest -m property

# Run with coverage
pytest --cov=src --cov-report=html
```

## Development Workflow

1. **Add New Functionality**: Create modules in `src/`
2. **Write Unit Tests**: Add specific test cases in `tests/test_*.py`
3. **Write Property Tests**: Add universal properties in `tests/test_properties.py`
4. **Run Tests**: Use `python run_tests.py` to verify implementation
5. **Check Coverage**: Review HTML coverage report in `htmlcov/`

## Configuration Examples

### Environment Variables
```bash
export AWS_ACCOUNT_ID="123456789012"
export AWS_DEFAULT_REGION="us-east-1"
export BEDROCK_IAM_ROLE_NAME="CustomBedrockRole"
export BEDROCK_S3_BUCKET_PREFIX="custom-bedrock-logs"
```

### Loading Configuration
```python
from src.config import load_config_from_env, get_default_config

# Load from environment
config = load_config_from_env()

# Use defaults
config = get_default_config()

# Convert to dictionary for JSON output
config_dict = config.to_dict()
```

## Next Steps

This project structure provides the foundation for implementing the remaining monitoring system components. Each script implementation should:

1. Import shared configuration and utilities
2. Include comprehensive unit tests
3. Add property-based tests for universal behaviors
4. Follow the established error handling patterns
5. Use the logging utilities for consistent output

The testing framework ensures that all components work correctly across different AWS environments and configurations.