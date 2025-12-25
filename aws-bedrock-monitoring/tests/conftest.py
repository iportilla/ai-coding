"""
Pytest configuration and shared fixtures for AWS Bedrock monitoring tests.

This module provides common test fixtures and configuration for both unit tests
and property-based tests across the monitoring system.
"""

import pytest
from hypothesis import settings, Verbosity
from src.config import MonitoringConfiguration, IAMConfig, StorageConfig, AlertingConfig, DashboardConfig


# Configure Hypothesis for property-based testing
settings.register_profile("default", max_examples=100, verbosity=Verbosity.normal)
settings.register_profile("ci", max_examples=1000, verbosity=Verbosity.verbose)
settings.register_profile("dev", max_examples=10, verbosity=Verbosity.verbose)

# Load profile based on environment
settings.load_profile("default")


@pytest.fixture
def sample_account_id():
    """Provide a sample AWS account ID for testing."""
    return "123456789012"


@pytest.fixture
def sample_region():
    """Provide a sample AWS region for testing."""
    return "us-east-1"


@pytest.fixture
def iam_config(sample_account_id):
    """Provide a sample IAM configuration."""
    return IAMConfig(account_id=sample_account_id)


@pytest.fixture
def storage_config():
    """Provide a sample storage configuration."""
    return StorageConfig()


@pytest.fixture
def alerting_config():
    """Provide a sample alerting configuration."""
    return AlertingConfig()


@pytest.fixture
def dashboard_config(sample_region):
    """Provide a sample dashboard configuration."""
    return DashboardConfig(region=sample_region)


@pytest.fixture
def monitoring_config(sample_account_id, sample_region):
    """Provide a complete monitoring configuration."""
    return MonitoringConfiguration(account_id=sample_account_id, region=sample_region)


@pytest.fixture
def mock_aws_responses():
    """Provide mock AWS CLI responses for testing."""
    return {
        'get_caller_identity': '123456789012',
        'get_region': 'us-east-1',
        'iam_role_exists': True,
        's3_bucket_exists': False,
        'log_group_exists': False
    }