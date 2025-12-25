"""
Unit tests for configuration module.

Tests the configuration classes and functions to ensure proper initialization,
validation, and environment variable handling.
"""

import os
import pytest
from src.config import (
    IAMConfig, StorageConfig, AlertingConfig, DashboardConfig,
    MonitoringConfiguration, get_default_config, load_config_from_env
)


class TestIAMConfig:
    """Test IAM configuration class."""
    
    def test_default_initialization(self):
        """Test IAM config with default values."""
        config = IAMConfig()
        assert config.role_name == "BedrockCloudWatchLoggingRole"
        assert config.account_id == ""  # Empty when not set
    
    def test_custom_initialization(self):
        """Test IAM config with custom values."""
        config = IAMConfig(role_name="CustomRole", account_id="123456789012")
        assert config.role_name == "CustomRole"
        assert config.account_id == "123456789012"
    
    def test_environment_account_id(self, monkeypatch):
        """Test account ID loading from environment."""
        monkeypatch.setenv("AWS_ACCOUNT_ID", "987654321098")
        config = IAMConfig()
        assert config.account_id == "987654321098"


class TestStorageConfig:
    """Test storage configuration class."""
    
    def test_default_values(self):
        """Test storage config default values."""
        config = StorageConfig()
        assert config.s3_bucket_prefix == "bedrock-logs"
        assert config.cloudwatch_log_group == "/aws/bedrock/modelinvocations"
        assert config.cloudwatch_retention_days == 30
        assert config.s3_lifecycle_days == 90
    
    def test_s3_bucket_name_generation(self):
        """Test S3 bucket name generation with account ID."""
        config = StorageConfig()
        bucket_name = config.get_s3_bucket_name("123456789012")
        assert bucket_name == "bedrock-logs-123456789012"
    
    def test_custom_prefix(self):
        """Test custom S3 bucket prefix."""
        config = StorageConfig(s3_bucket_prefix="custom-logs")
        bucket_name = config.get_s3_bucket_name("123456789012")
        assert bucket_name == "custom-logs-123456789012"


class TestAlertingConfig:
    """Test alerting configuration class."""
    
    def test_default_thresholds(self):
        """Test default alerting thresholds."""
        config = AlertingConfig()
        assert config.sns_topic_name == "bedrock-monitoring-alerts"
        assert config.high_token_threshold == 100000
        assert config.error_rate_threshold == 10
        assert config.invocation_spike_threshold == 1000
        assert config.high_latency_threshold == 10


class TestDashboardConfig:
    """Test dashboard configuration class."""
    
    def test_default_values(self):
        """Test dashboard config default values."""
        config = DashboardConfig()
        assert config.dashboard_name == "BedrockUsageMonitoring"
        assert config.region == "us-east-1"
    
    def test_custom_region(self):
        """Test custom region setting."""
        config = DashboardConfig(region="eu-west-1")
        assert config.region == "eu-west-1"


class TestMonitoringConfiguration:
    """Test complete monitoring configuration."""
    
    def test_default_initialization(self):
        """Test monitoring config with defaults."""
        config = MonitoringConfiguration()
        assert isinstance(config.iam, IAMConfig)
        assert isinstance(config.storage, StorageConfig)
        assert isinstance(config.alerting, AlertingConfig)
        assert isinstance(config.dashboard, DashboardConfig)
    
    def test_custom_initialization(self):
        """Test monitoring config with custom values."""
        config = MonitoringConfiguration(account_id="123456789012", region="eu-west-1")
        assert config.iam.account_id == "123456789012"
        assert config.dashboard.region == "eu-west-1"
    
    def test_to_dict_conversion(self):
        """Test configuration conversion to dictionary."""
        config = MonitoringConfiguration(account_id="123456789012", region="us-west-2")
        config_dict = config.to_dict()
        
        assert config_dict['iam']['accountId'] == "123456789012"
        assert config_dict['storage']['s3BucketName'] == "bedrock-logs-123456789012"
        assert config_dict['dashboard']['region'] == "us-west-2"
        assert config_dict['alerting']['thresholds']['highTokenUsage'] == 100000


class TestConfigurationFunctions:
    """Test configuration utility functions."""
    
    def test_get_default_config(self):
        """Test default configuration creation."""
        config = get_default_config()
        assert isinstance(config, MonitoringConfiguration)
        assert config.dashboard.region == "us-east-1"
    
    def test_load_config_from_env_defaults(self, monkeypatch):
        """Test loading config from environment with defaults."""
        # Clear any existing environment variables
        monkeypatch.delenv("AWS_ACCOUNT_ID", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
        
        config = load_config_from_env()
        assert config.dashboard.region == "us-east-1"  # Default region
    
    def test_load_config_from_env_custom(self, monkeypatch):
        """Test loading config from environment with custom values."""
        monkeypatch.setenv("AWS_ACCOUNT_ID", "987654321098")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
        monkeypatch.setenv("BEDROCK_IAM_ROLE_NAME", "CustomBedrockRole")
        monkeypatch.setenv("BEDROCK_S3_BUCKET_PREFIX", "custom-bedrock-logs")
        monkeypatch.setenv("BEDROCK_SNS_TOPIC_NAME", "custom-alerts")
        
        config = load_config_from_env()
        assert config.iam.account_id == "987654321098"
        assert config.dashboard.region == "eu-central-1"
        assert config.iam.role_name == "CustomBedrockRole"
        assert config.storage.s3_bucket_prefix == "custom-bedrock-logs"
        assert config.alerting.sns_topic_name == "custom-alerts"