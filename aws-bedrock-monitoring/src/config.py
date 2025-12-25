"""
Shared configuration module for AWS Bedrock monitoring system.

This module provides centralized configuration management for all monitoring
components including IAM roles, S3 buckets, CloudWatch settings, and alerting thresholds.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class IAMConfig:
    """Configuration for IAM role and permissions."""
    role_name: str = "BedrockCloudWatchLoggingRole"
    account_id: Optional[str] = None
    
    def __post_init__(self):
        if self.account_id is None:
            # Will be populated from AWS CLI or environment
            self.account_id = os.environ.get('AWS_ACCOUNT_ID', '')


@dataclass
class StorageConfig:
    """Configuration for S3 and CloudWatch log storage."""
    s3_bucket_prefix: str = "bedrock-logs"
    cloudwatch_log_group: str = "/aws/bedrock/modelinvocations"
    cloudwatch_retention_days: int = 30
    s3_lifecycle_days: int = 90
    
    def get_s3_bucket_name(self, account_id: str) -> str:
        """Generate account-specific S3 bucket name."""
        return f"{self.s3_bucket_prefix}-{account_id}"


@dataclass
class AlertingConfig:
    """Configuration for CloudWatch alarms and SNS notifications."""
    sns_topic_name: str = "bedrock-monitoring-alerts"
    high_token_threshold: int = 100000  # tokens per hour
    error_rate_threshold: int = 10      # errors per 5 minutes
    invocation_spike_threshold: int = 1000  # invocations per hour
    high_latency_threshold: int = 10    # seconds
    
    
@dataclass
class DashboardConfig:
    """Configuration for CloudWatch dashboard."""
    dashboard_name: str = "BedrockUsageMonitoring"
    region: str = "us-east-1"


@dataclass
class MonitoringConfiguration:
    """Complete monitoring system configuration."""
    iam: IAMConfig
    storage: StorageConfig
    alerting: AlertingConfig
    dashboard: DashboardConfig
    
    def __init__(self, account_id: Optional[str] = None, region: str = "us-east-1"):
        self.iam = IAMConfig(account_id=account_id)
        self.storage = StorageConfig()
        self.alerting = AlertingConfig()
        self.dashboard = DashboardConfig(region=region)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            'iam': {
                'roleName': self.iam.role_name,
                'accountId': self.iam.account_id
            },
            'storage': {
                's3BucketName': self.storage.get_s3_bucket_name(self.iam.account_id or ''),
                'cloudwatchLogGroup': self.storage.cloudwatch_log_group,
                'retentionDays': self.storage.cloudwatch_retention_days,
                'lifecycleDays': self.storage.s3_lifecycle_days
            },
            'alerting': {
                'snsTopicName': self.alerting.sns_topic_name,
                'thresholds': {
                    'highTokenUsage': self.alerting.high_token_threshold,
                    'errorRate': self.alerting.error_rate_threshold,
                    'invocationSpike': self.alerting.invocation_spike_threshold,
                    'highLatency': self.alerting.high_latency_threshold
                }
            },
            'dashboard': {
                'name': self.dashboard.dashboard_name,
                'region': self.dashboard.region
            }
        }


def get_default_config() -> MonitoringConfiguration:
    """Get default monitoring configuration."""
    return MonitoringConfiguration()


def load_config_from_env() -> MonitoringConfiguration:
    """Load configuration from environment variables."""
    account_id = os.environ.get('AWS_ACCOUNT_ID')
    region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
    
    config = MonitoringConfiguration(account_id=account_id, region=region)
    
    # Override defaults with environment variables if present
    if os.environ.get('BEDROCK_IAM_ROLE_NAME'):
        config.iam.role_name = os.environ['BEDROCK_IAM_ROLE_NAME']
    
    if os.environ.get('BEDROCK_S3_BUCKET_PREFIX'):
        config.storage.s3_bucket_prefix = os.environ['BEDROCK_S3_BUCKET_PREFIX']
    
    if os.environ.get('BEDROCK_SNS_TOPIC_NAME'):
        config.alerting.sns_topic_name = os.environ['BEDROCK_SNS_TOPIC_NAME']
    
    return config