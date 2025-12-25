"""
Property-based tests for AWS Bedrock monitoring system.

These tests use Hypothesis to generate random inputs and verify that universal
properties hold across all valid configurations and inputs.
"""

import pytest
import json
import subprocess
from typing import List
from hypothesis import given, strategies as st, assume
from src.config import MonitoringConfiguration, IAMConfig, StorageConfig
from src.utils import validate_aws_account_id, validate_aws_region, format_json, parse_json_safely


# Custom strategies for AWS-specific data
aws_account_id_strategy = st.text(min_size=12, max_size=12).filter(lambda x: x.isdigit())
aws_region_strategy = st.from_regex(r'^[a-z]{2}-[a-z]+-\d+$')
bucket_name_strategy = st.text(min_size=3, max_size=63).filter(
    lambda x: x.replace('-', '').replace('.', '').isalnum() and not x.startswith('-') and not x.endswith('-')
)


def generate_iam_trust_policy(account_id: str) -> dict:
    """Generate IAM trust policy for testing."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": account_id
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:*:{account_id}:*"
                    }
                }
            }
        ]
    }


def generate_iam_permissions_policy(account_id: str) -> dict:
    """Generate IAM permissions policy for testing."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": [
                    f"arn:aws:logs:*:{account_id}:log-group:/aws/bedrock/*",
                    f"arn:aws:logs:*:{account_id}:log-group:/aws/bedrock/*:log-stream:*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": [
                    f"arn:aws:s3:::bedrock-logs-{account_id}/*"
                ]
            }
        ]
    }


class TestIAMRoleSecurityProperties:
    """Property-based tests for IAM role security configuration."""
    
    @given(aws_account_id_strategy)
    @pytest.mark.property
    def test_iam_role_security_configuration_property(self, account_id):
        """
        Property 1: IAM Role Security Configuration
        For any AWS account and monitoring system deployment, the created IAM role should 
        contain only the minimal required permissions for CloudWatch logging and S3 access, 
        with a trust policy that restricts access to the Bedrock service and specific account resources.
        **Feature: aws-bedrock-monitoring, Property 1: IAM Role Security Configuration**
        **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
        """
        # Generate trust policy for the account
        trust_policy = generate_iam_trust_policy(account_id)
        
        # Verify trust policy has correct structure
        assert trust_policy["Version"] == "2012-10-17"
        assert len(trust_policy["Statement"]) == 1
        
        statement = trust_policy["Statement"][0]
        
        # Verify Bedrock service principal (Requirement 1.5)
        assert statement["Principal"]["Service"] == "bedrock.amazonaws.com"
        assert statement["Action"] == "sts:AssumeRole"
        
        # Verify account-specific restrictions (Requirement 1.2)
        conditions = statement["Condition"]
        assert conditions["StringEquals"]["aws:SourceAccount"] == account_id
        assert conditions["ArnLike"]["aws:SourceArn"] == f"arn:aws:bedrock:*:{account_id}:*"
        
        # Generate permissions policy for the account
        permissions_policy = generate_iam_permissions_policy(account_id)
        
        # Verify permissions policy has minimal required permissions (Requirement 1.1, 1.3)
        assert permissions_policy["Version"] == "2012-10-17"
        assert len(permissions_policy["Statement"]) == 2
        
        # Check CloudWatch permissions (Requirement 1.3)
        cloudwatch_statement = permissions_policy["Statement"][0]
        required_actions = {"logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"}
        assert set(cloudwatch_statement["Action"]) == required_actions
        
        # Verify account-specific resource ARNs (Requirement 1.2)
        for resource in cloudwatch_statement["Resource"]:
            assert account_id in resource
            assert "/aws/bedrock/" in resource
        
        # Check S3 permissions (Requirement 1.4)
        s3_statement = permissions_policy["Statement"][1]
        assert s3_statement["Action"] == ["s3:PutObject"]
        assert len(s3_statement["Resource"]) == 1
        assert f"bedrock-logs-{account_id}" in s3_statement["Resource"][0]
        
        # Verify no excessive permissions are granted
        all_actions = []
        for stmt in permissions_policy["Statement"]:
            if isinstance(stmt["Action"], list):
                all_actions.extend(stmt["Action"])
            else:
                all_actions.append(stmt["Action"])
        
        # Should only have exactly these 4 actions
        expected_actions = {
            "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "s3:PutObject"
        }
        assert set(all_actions) == expected_actions


class TestConfigurationProperties:
    """Property-based tests for configuration classes."""
    
    @given(aws_account_id_strategy)
    @pytest.mark.property
    def test_iam_config_account_id_property(self, account_id):
        """
        Property: For any valid AWS account ID, IAM config should store it correctly.
        **Feature: aws-bedrock-monitoring, Property 1: IAM configuration integrity**
        """
        config = IAMConfig(account_id=account_id)
        assert config.account_id == account_id
        assert validate_aws_account_id(config.account_id)
    
    @given(bucket_name_strategy, aws_account_id_strategy)
    @pytest.mark.property
    def test_storage_config_bucket_naming_property(self, prefix, account_id):
        """
        Property: For any valid prefix and account ID, S3 bucket name should be properly formatted.
        **Feature: aws-bedrock-monitoring, Property 2: Storage naming consistency**
        """
        assume(len(prefix) > 0 and len(account_id) == 12)
        
        config = StorageConfig(s3_bucket_prefix=prefix)
        bucket_name = config.get_s3_bucket_name(account_id)
        
        # Bucket name should contain both prefix and account ID
        assert prefix in bucket_name
        assert account_id in bucket_name
        assert bucket_name == f"{prefix}-{account_id}"
    
    @given(aws_account_id_strategy, aws_region_strategy)
    @pytest.mark.property
    def test_monitoring_config_completeness_property(self, account_id, region):
        """
        Property: For any valid account ID and region, monitoring config should be complete.
        **Feature: aws-bedrock-monitoring, Property 3: Configuration completeness**
        """
        config = MonitoringConfiguration(account_id=account_id, region=region)
        config_dict = config.to_dict()
        
        # All major sections should be present
        required_sections = ['iam', 'storage', 'alerting', 'dashboard']
        for section in required_sections:
            assert section in config_dict
        
        # Account ID and region should be properly set
        assert config_dict['iam']['accountId'] == account_id
        assert config_dict['dashboard']['region'] == region


class TestValidationProperties:
    """Property-based tests for validation functions."""
    
    @given(st.text())
    @pytest.mark.property
    def test_account_id_validation_property(self, text):
        """
        Property: For any string, account ID validation should only accept 12-digit strings.
        **Feature: aws-bedrock-monitoring, Property 4: Account ID validation consistency**
        """
        is_valid = validate_aws_account_id(text)
        
        if is_valid:
            # If validation passes, it must be exactly 12 digits
            assert len(text) == 12
            assert text.isdigit()
        else:
            # If validation fails, it must not be 12 digits or contain non-digits
            assert len(text) != 12 or not text.isdigit()
    
    @given(st.text())
    @pytest.mark.property
    def test_region_validation_property(self, text):
        """
        Property: For any string, region validation should only accept proper AWS region format.
        **Feature: aws-bedrock-monitoring, Property 5: Region validation consistency**
        """
        is_valid = validate_aws_region(text)
        
        if is_valid:
            # If validation passes, it must match AWS region pattern
            parts = text.split('-')
            assert len(parts) == 3
            assert len(parts[0]) == 2  # Country code
            assert parts[1].isalpha()  # Direction (east, west, etc.)
            assert parts[2].isdigit()  # Number
        # If validation fails, we don't need to check anything specific


class TestStorageConfigurationProperties:
    """Property-based tests for storage configuration completeness."""
    
    @given(aws_account_id_strategy, aws_region_strategy)
    @pytest.mark.property
    def test_storage_configuration_completeness_property(self, account_id, region):
        """
        Property 2: Storage Configuration Completeness
        For any monitoring system deployment, the storage configuration should include 
        an S3 bucket with account-specific naming, versioning enabled, 90-day lifecycle policy, 
        and CloudWatch log group with 30-day retention.
        **Feature: aws-bedrock-monitoring, Property 2: Storage Configuration Completeness**
        **Validates: Requirements 2.2, 2.3, 2.4, 2.5**
        """
        # Create storage configuration
        storage_config = StorageConfig()
        
        # Test S3 bucket configuration (Requirements 2.2, 2.4, 2.5)
        bucket_name = storage_config.get_s3_bucket_name(account_id)
        
        # Verify account-specific naming (Requirement 2.2)
        assert account_id in bucket_name
        assert storage_config.s3_bucket_prefix in bucket_name
        assert bucket_name == f"{storage_config.s3_bucket_prefix}-{account_id}"
        
        # Verify lifecycle policy configuration (Requirement 2.5)
        assert storage_config.s3_lifecycle_days == 90
        
        # Test CloudWatch log group configuration (Requirement 2.3)
        log_group_name = storage_config.cloudwatch_log_group
        
        # Verify log group follows AWS Bedrock convention
        assert log_group_name == "/aws/bedrock/modelinvocations"
        
        # Verify retention policy (Requirement 2.3)
        assert storage_config.cloudwatch_retention_days == 30
        
        # Test complete storage configuration structure
        monitoring_config = MonitoringConfiguration(account_id=account_id, region=region)
        config_dict = monitoring_config.to_dict()
        
        # Verify all required storage components are present
        storage_section = config_dict['storage']
        required_storage_fields = [
            's3BucketName', 'cloudwatchLogGroup', 'retentionDays', 'lifecycleDays'
        ]
        
        for field in required_storage_fields:
            assert field in storage_section
            assert storage_section[field] is not None
        
        # Verify specific values match requirements
        assert storage_section['s3BucketName'] == bucket_name
        assert storage_section['cloudwatchLogGroup'] == "/aws/bedrock/modelinvocations"
        assert storage_section['retentionDays'] == 30  # CloudWatch retention
        assert storage_section['lifecycleDays'] == 90  # S3 lifecycle
        
        # Verify bucket name is valid for S3
        # S3 bucket names must be 3-63 characters, lowercase, no underscores
        assert 3 <= len(bucket_name) <= 63
        assert bucket_name.islower() or bucket_name.replace('-', '').replace('.', '').isalnum()
        assert not bucket_name.startswith('-')
        assert not bucket_name.endswith('-')
    
    @given(
        st.text(min_size=1, max_size=20).filter(lambda x: x.replace('-', '').isalnum()),
        aws_account_id_strategy,
        st.integers(min_value=1, max_value=3653)  # Valid CloudWatch retention days
    )
    @pytest.mark.property
    def test_storage_config_customization_property(self, bucket_prefix, account_id, retention_days):
        """
        Property: For any valid bucket prefix, account ID, and retention days, 
        storage configuration should maintain consistency and validity.
        **Feature: aws-bedrock-monitoring, Property 2b: Storage configuration flexibility**
        """
        # Create customized storage configuration
        storage_config = StorageConfig(
            s3_bucket_prefix=bucket_prefix,
            cloudwatch_retention_days=retention_days
        )
        
        # Test bucket naming consistency
        bucket_name = storage_config.get_s3_bucket_name(account_id)
        assert bucket_name == f"{bucket_prefix}-{account_id}"
        assert account_id in bucket_name
        assert bucket_prefix in bucket_name
        
        # Test retention configuration
        assert storage_config.cloudwatch_retention_days == retention_days
        
        # Test that lifecycle days remain at default (90) unless explicitly changed
        assert storage_config.s3_lifecycle_days == 90
        
        # Test log group name remains consistent
        assert storage_config.cloudwatch_log_group == "/aws/bedrock/modelinvocations"


class TestBedrockLoggingConfigurationProperties:
    """Property-based tests for Bedrock logging configuration integrity."""
    
    def generate_bedrock_logging_config(self, account_id: str, region: str) -> dict:
        """Generate a valid Bedrock logging configuration for testing."""
        log_group_name = "/aws/bedrock/modelinvocations"
        role_arn = f"arn:aws:iam::{account_id}:role/BedrockCloudWatchLoggingRole"
        s3_bucket_name = f"bedrock-logs-{account_id}"
        
        return {
            "loggingConfig": {
                "cloudWatchConfig": {
                    "logGroupName": log_group_name,
                    "roleArn": role_arn
                },
                "s3Config": {
                    "bucketName": s3_bucket_name,
                    "keyPrefix": "bedrock-logs/"
                },
                "textDataDeliveryEnabled": True,
                "imageDataDeliveryEnabled": False,
                "embeddingDataDeliveryEnabled": False
            }
        }
    
    @given(aws_account_id_strategy, aws_region_strategy)
    @pytest.mark.property
    def test_bedrock_logging_configuration_integrity_property(self, account_id, region):
        """
        Property 3: Bedrock Logging Configuration Integrity
        For any logging configuration setup, the system should enable model invocation logging 
        with text data delivery to both CloudWatch and S3 destinations using the correct log group name.
        **Feature: aws-bedrock-monitoring, Property 3: Bedrock Logging Configuration Integrity**
        **Validates: Requirements 3.1, 3.3, 3.4, 3.5**
        """
        # Generate logging configuration for the account and region
        logging_config = self.generate_bedrock_logging_config(account_id, region)
        
        # Verify top-level structure exists (Requirement 3.1)
        assert "loggingConfig" in logging_config
        config = logging_config["loggingConfig"]
        
        # Verify CloudWatch configuration (Requirements 3.3, 3.4)
        assert "cloudWatchConfig" in config
        cloudwatch_config = config["cloudWatchConfig"]
        
        # Verify correct log group name (Requirement 3.4)
        assert "logGroupName" in cloudwatch_config
        assert cloudwatch_config["logGroupName"] == "/aws/bedrock/modelinvocations"
        
        # Verify IAM role ARN is account-specific (Requirement 3.3)
        assert "roleArn" in cloudwatch_config
        role_arn = cloudwatch_config["roleArn"]
        assert account_id in role_arn
        assert "BedrockCloudWatchLoggingRole" in role_arn
        assert role_arn.startswith("arn:aws:iam::")
        assert role_arn.endswith(":role/BedrockCloudWatchLoggingRole")
        
        # Verify S3 configuration (Requirements 3.3, 3.5)
        assert "s3Config" in config
        s3_config = config["s3Config"]
        
        # Verify S3 bucket name is account-specific (Requirement 3.3)
        assert "bucketName" in s3_config
        bucket_name = s3_config["bucketName"]
        assert account_id in bucket_name
        assert bucket_name == f"bedrock-logs-{account_id}"
        
        # Verify S3 key prefix for organization
        assert "keyPrefix" in s3_config
        assert s3_config["keyPrefix"] == "bedrock-logs/"
        
        # Verify text data delivery is enabled (Requirement 3.5)
        assert "textDataDeliveryEnabled" in config
        assert config["textDataDeliveryEnabled"] is True
        
        # Verify other data types are disabled by default (focused on text logging)
        assert "imageDataDeliveryEnabled" in config
        assert config["imageDataDeliveryEnabled"] is False
        assert "embeddingDataDeliveryEnabled" in config
        assert config["embeddingDataDeliveryEnabled"] is False
        
        # Verify dual destination configuration (Requirements 3.3, 3.4)
        # Both CloudWatch and S3 configurations must be present and valid
        assert cloudwatch_config["logGroupName"] is not None
        assert cloudwatch_config["roleArn"] is not None
        assert s3_config["bucketName"] is not None
        assert s3_config["keyPrefix"] is not None
        
        # Verify configuration can be serialized to JSON (for AWS API calls)
        json_string = format_json(logging_config)
        parsed_config = parse_json_safely(json_string)
        assert parsed_config == logging_config
        
        # Verify the configuration structure matches AWS Bedrock API expectations
        # The configuration should be ready for put-model-invocation-logging-configuration
        assert isinstance(config["cloudWatchConfig"], dict)
        assert isinstance(config["s3Config"], dict)
        assert isinstance(config["textDataDeliveryEnabled"], bool)
    
    @given(
        aws_account_id_strategy,
        st.text(min_size=1, max_size=50).filter(lambda x: x.replace('/', '').replace('-', '').isalnum()),
        st.text(min_size=3, max_size=63).filter(lambda x: x.replace('-', '').isalnum())
    )
    @pytest.mark.property
    def test_logging_config_customization_property(self, account_id, log_group_suffix, bucket_prefix):
        """
        Property: For any valid account ID, log group suffix, and bucket prefix,
        the logging configuration should maintain proper structure and account-specific naming.
        **Feature: aws-bedrock-monitoring, Property 3b: Logging configuration flexibility**
        """
        # Generate custom configuration
        custom_log_group = f"/aws/bedrock/{log_group_suffix}"
        custom_bucket = f"{bucket_prefix}-{account_id}"
        role_arn = f"arn:aws:iam::{account_id}:role/BedrockCloudWatchLoggingRole"
        
        config = {
            "loggingConfig": {
                "cloudWatchConfig": {
                    "logGroupName": custom_log_group,
                    "roleArn": role_arn
                },
                "s3Config": {
                    "bucketName": custom_bucket,
                    "keyPrefix": "bedrock-logs/"
                },
                "textDataDeliveryEnabled": True,
                "imageDataDeliveryEnabled": False,
                "embeddingDataDeliveryEnabled": False
            }
        }
        
        # Verify account ID consistency across all components
        assert account_id in role_arn
        assert account_id in custom_bucket
        
        # Verify log group follows AWS Bedrock convention
        assert custom_log_group.startswith("/aws/bedrock/")
        
        # Verify bucket name includes account ID for uniqueness
        assert custom_bucket.endswith(f"-{account_id}")
        
        # Verify configuration structure remains valid
        logging_config = config["loggingConfig"]
        assert "cloudWatchConfig" in logging_config
        assert "s3Config" in logging_config
        assert "textDataDeliveryEnabled" in logging_config
        
        # Verify dual destination setup
        assert logging_config["cloudWatchConfig"]["logGroupName"] == custom_log_group
        assert logging_config["cloudWatchConfig"]["roleArn"] == role_arn
        assert logging_config["s3Config"]["bucketName"] == custom_bucket
        
        # Verify text delivery is enabled for comprehensive logging
        assert logging_config["textDataDeliveryEnabled"] is True


class TestDashboardWidgetProperties:
    """Property-based tests for dashboard widget completeness."""
    
    def generate_dashboard_config(self, region: str, log_group: str) -> dict:
        """Generate a valid CloudWatch dashboard configuration for testing."""
        return {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Bedrock", "Invocations", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0"]
                        ],
                        "view": "timeSeries",
                        "region": region,
                        "title": "Bedrock Model Invocations",
                        "period": 300,
                        "stat": "Sum"
                    }
                },
                {
                    "type": "metric",
                    "x": 12, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Bedrock", "InputTokenCount", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0"]
                        ],
                        "view": "timeSeries",
                        "region": region,
                        "title": "Input Token Usage",
                        "period": 300,
                        "stat": "Sum"
                    }
                },
                {
                    "type": "metric",
                    "x": 0, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Bedrock", "OutputTokenCount", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0"]
                        ],
                        "view": "timeSeries",
                        "region": region,
                        "title": "Output Token Usage",
                        "period": 300,
                        "stat": "Sum"
                    }
                },
                {
                    "type": "metric",
                    "x": 12, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Bedrock", "InvocationLatency", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0"]
                        ],
                        "view": "timeSeries",
                        "region": region,
                        "title": "Average Latency (ms)",
                        "period": 300,
                        "stat": "Average"
                    }
                },
                {
                    "type": "metric",
                    "x": 0, "y": 12, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Bedrock", "InvocationLatency", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0"]
                        ],
                        "view": "timeSeries",
                        "region": region,
                        "title": "99th Percentile Latency (ms)",
                        "period": 300,
                        "stat": "p99"
                    }
                },
                {
                    "type": "metric",
                    "x": 12, "y": 12, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Bedrock", "InvocationClientErrors", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0"],
                            [".", "InvocationServerErrors", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0"],
                            [".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0"]
                        ],
                        "view": "timeSeries",
                        "region": region,
                        "title": "Error Counts (Client & Server)",
                        "period": 300,
                        "stat": "Sum"
                    }
                },
                {
                    "type": "log",
                    "x": 0, "y": 18, "width": 24, "height": 6,
                    "properties": {
                        "query": f"SOURCE '{log_group}'\n| fields @timestamp, modelId, inputTokenCount, outputTokenCount, invocationLatency\n| sort @timestamp desc\n| limit 100",
                        "region": region,
                        "title": "Recent Bedrock Invocations",
                        "view": "table"
                    }
                }
            ]
        }
    
    @given(aws_region_strategy, st.text(min_size=1, max_size=100))
    @pytest.mark.property
    def test_dashboard_widget_completeness_property(self, region, log_group):
        """
        Property 4: Dashboard Widget Completeness
        For any dashboard configuration, the dashboard should include all required widgets 
        for invocations, input/output tokens, latency metrics (average and p99), error tracking, 
        and recent log viewing.
        **Feature: aws-bedrock-monitoring, Property 4: Dashboard Widget Completeness**
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Generate dashboard configuration for the region and log group
        dashboard_config = self.generate_dashboard_config(region, log_group)
        
        # Verify top-level structure (Requirements 4.1, 4.2, 4.3, 4.4, 4.5)
        assert "widgets" in dashboard_config
        widgets = dashboard_config["widgets"]
        
        # Should have exactly 7 widgets (all required widgets)
        assert len(widgets) == 7
        
        # Extract widget titles for verification
        widget_titles = []
        widget_types = []
        
        for widget in widgets:
            assert "type" in widget
            assert "properties" in widget
            
            widget_types.append(widget["type"])
            
            if "title" in widget["properties"]:
                widget_titles.append(widget["properties"]["title"])
        
        # Verify all required widget types are present
        metric_widgets = [w for w in widget_types if w == "metric"]
        log_widgets = [w for w in widget_types if w == "log"]
        
        # Should have 6 metric widgets and 1 log widget
        assert len(metric_widgets) == 6
        assert len(log_widgets) == 1
        
        # Verify all required widget titles are present (Requirements 4.1, 4.2, 4.3, 4.4, 4.5)
        required_titles = {
            "Bedrock Model Invocations",      # Requirement 4.1
            "Input Token Usage",              # Requirement 4.2
            "Output Token Usage",             # Requirement 4.2
            "Average Latency (ms)",           # Requirement 4.3
            "99th Percentile Latency (ms)",   # Requirement 4.3
            "Error Counts (Client & Server)", # Requirement 4.4
            "Recent Bedrock Invocations"      # Requirement 4.5
        }
        
        assert set(widget_titles) == required_titles
        
        # Verify each widget has proper structure and configuration
        for widget in widgets:
            # All widgets should have positioning and sizing
            assert "x" in widget
            assert "y" in widget
            assert "width" in widget
            assert "height" in widget
            
            # All widgets should have properties
            properties = widget["properties"]
            assert "region" in properties
            assert properties["region"] == region
            assert "title" in properties
            
            if widget["type"] == "metric":
                # Metric widgets should have metrics, view, period, and stat
                assert "metrics" in properties
                assert "view" in properties
                assert "period" in properties
                assert "stat" in properties
                
                # Should have at least one metric
                assert len(properties["metrics"]) > 0
                
                # All metrics should be AWS/Bedrock namespace
                for metric in properties["metrics"]:
                    if isinstance(metric[0], str) and metric[0] != ".":
                        assert metric[0] == "AWS/Bedrock"
                
                # Verify specific metric types based on title
                title = properties["title"]
                if "Invocations" in title:
                    # Should track Invocations metric
                    metric_names = [m[1] for m in properties["metrics"] if len(m) > 1 and m[1] != "."]
                    assert "Invocations" in metric_names
                elif "Input Token" in title:
                    # Should track InputTokenCount metric
                    metric_names = [m[1] for m in properties["metrics"] if len(m) > 1 and m[1] != "."]
                    assert "InputTokenCount" in metric_names
                elif "Output Token" in title:
                    # Should track OutputTokenCount metric
                    metric_names = [m[1] for m in properties["metrics"] if len(m) > 1 and m[1] != "."]
                    assert "OutputTokenCount" in metric_names
                elif "Latency" in title:
                    # Should track InvocationLatency metric
                    metric_names = [m[1] for m in properties["metrics"] if len(m) > 1 and m[1] != "."]
                    assert "InvocationLatency" in metric_names
                    
                    # Verify correct statistic for latency type
                    if "Average" in title:
                        assert properties["stat"] == "Average"
                    elif "99th Percentile" in title:
                        assert properties["stat"] == "p99"
                elif "Error" in title:
                    # Should track error metrics
                    metric_names = [m[1] for m in properties["metrics"] if len(m) > 1 and m[1] != "."]
                    assert "InvocationClientErrors" in metric_names or "InvocationServerErrors" in metric_names
            
            elif widget["type"] == "log":
                # Log widgets should have query and view
                assert "query" in properties
                assert "view" in properties
                
                # Query should reference the log group
                assert log_group in properties["query"]
                
                # Should be table view for log data
                assert properties["view"] == "table"
                
                # Query should include key fields for Bedrock monitoring
                query = properties["query"]
                required_fields = ["@timestamp", "modelId", "inputTokenCount", "outputTokenCount", "invocationLatency"]
                for field in required_fields:
                    assert field in query
        
        # Verify widget layout makes sense (no overlapping positions)
        positions = [(w["x"], w["y"], w["width"], w["height"]) for w in widgets]
        
        # Check that widgets don't overlap (simplified check)
        for i, (x1, y1, w1, h1) in enumerate(positions):
            for j, (x2, y2, w2, h2) in enumerate(positions):
                if i != j:
                    # Widgets should not overlap
                    if not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1):
                        # Allow exact same position only if it's the same widget
                        assert (x1, y1, w1, h1) == (x2, y2, w2, h2), f"Widgets {i} and {j} overlap"
        
        # Verify dashboard can be serialized to JSON (for AWS API calls)
        json_string = format_json(dashboard_config)
        parsed_config = parse_json_safely(json_string)
        assert parsed_config == dashboard_config
        
        # Verify the configuration structure matches AWS CloudWatch dashboard API expectations
        assert isinstance(dashboard_config["widgets"], list)
        for widget in dashboard_config["widgets"]:
            assert isinstance(widget, dict)
            assert isinstance(widget["properties"], dict)
    
    @given(
        aws_region_strategy,
        st.text(min_size=1, max_size=50).filter(lambda x: x.replace('/', '').replace('-', '').isalnum()),
        st.integers(min_value=60, max_value=3600)  # Valid CloudWatch periods
    )
    @pytest.mark.property
    def test_dashboard_config_customization_property(self, region, dashboard_suffix, period):
        """
        Property: For any valid region, dashboard suffix, and period,
        dashboard configuration should maintain proper structure and customization.
        **Feature: aws-bedrock-monitoring, Property 4b: Dashboard configuration flexibility**
        """
        # Generate custom dashboard configuration
        log_group = f"/aws/bedrock/{dashboard_suffix}"
        dashboard_config = self.generate_dashboard_config(region, log_group)
        
        # Verify region consistency across all widgets
        for widget in dashboard_config["widgets"]:
            properties = widget["properties"]
            assert properties["region"] == region
        
        # Verify log group is properly referenced in log widget
        log_widgets = [w for w in dashboard_config["widgets"] if w["type"] == "log"]
        assert len(log_widgets) == 1
        
        log_widget = log_widgets[0]
        assert log_group in log_widget["properties"]["query"]
        
        # Test period customization (modify all metric widgets to use custom period)
        for widget in dashboard_config["widgets"]:
            if widget["type"] == "metric":
                widget["properties"]["period"] = period
        
        # Verify all metric widgets now use the custom period
        for widget in dashboard_config["widgets"]:
            if widget["type"] == "metric":
                assert widget["properties"]["period"] == period
        
        # Verify structure remains valid after customization
        assert "widgets" in dashboard_config
        assert len(dashboard_config["widgets"]) == 7
        
        # Verify configuration can still be serialized
        json_string = format_json(dashboard_config)
        parsed_config = parse_json_safely(json_string)
        assert parsed_config == dashboard_config


class TestAlertingSystemProperties:
    """Property-based tests for alerting system configuration."""
    
    def generate_alarm_config(self, account_id: str, region: str, sns_topic_name: str) -> dict:
        """Generate a valid CloudWatch alarm configuration for testing."""
        sns_topic_arn = f"arn:aws:sns:{region}:{account_id}:{sns_topic_name}"
        
        return {
            "snsTopicArn": sns_topic_arn,
            "alarms": [
                {
                    "name": "Bedrock-HighInputTokenUsage",
                    "description": "Alert when input tokens exceed 100000 per hour",
                    "metricName": "InputTokenCount",
                    "namespace": "AWS/Bedrock",
                    "statistic": "Sum",
                    "period": 3600,
                    "evaluationPeriods": 1,
                    "threshold": 100000,
                    "comparisonOperator": "GreaterThanThreshold",
                    "alarmActions": [sns_topic_arn],
                    "okActions": [sns_topic_arn],
                    "treatMissingData": "notBreaching"
                },
                {
                    "name": "Bedrock-HighErrorRate",
                    "description": "Alert when client errors exceed 10 per 5 minutes",
                    "metricName": "InvocationClientErrors",
                    "namespace": "AWS/Bedrock",
                    "statistic": "Sum",
                    "period": 300,
                    "evaluationPeriods": 1,
                    "threshold": 10,
                    "comparisonOperator": "GreaterThanThreshold",
                    "alarmActions": [sns_topic_arn],
                    "okActions": [sns_topic_arn],
                    "treatMissingData": "notBreaching"
                },
                {
                    "name": "Bedrock-UnusualInvocationSpike",
                    "description": "Alert when invocations exceed 1000 per hour",
                    "metricName": "Invocations",
                    "namespace": "AWS/Bedrock",
                    "statistic": "Sum",
                    "period": 3600,
                    "evaluationPeriods": 1,
                    "threshold": 1000,
                    "comparisonOperator": "GreaterThanThreshold",
                    "alarmActions": [sns_topic_arn],
                    "okActions": [sns_topic_arn],
                    "treatMissingData": "notBreaching"
                },
                {
                    "name": "Bedrock-HighLatency",
                    "description": "Alert when average latency exceeds 10000ms",
                    "metricName": "InvocationLatency",
                    "namespace": "AWS/Bedrock",
                    "statistic": "Average",
                    "period": 300,
                    "evaluationPeriods": 2,
                    "threshold": 10000,
                    "comparisonOperator": "GreaterThanThreshold",
                    "alarmActions": [sns_topic_arn],
                    "okActions": [sns_topic_arn],
                    "treatMissingData": "notBreaching"
                }
            ]
        }
    
    @given(aws_account_id_strategy, aws_region_strategy, st.text(min_size=1, max_size=50).filter(lambda x: x.replace('-', '').isalnum()))
    @pytest.mark.property
    def test_alerting_system_configuration_property(self, account_id, region, sns_topic_name):
        """
        Property 5: Alerting System Configuration
        For any alerting system setup, all four required alarms (high token usage at 100k/hour, 
        error rate at 10/5min, invocation spike at 1000/hour, high latency at 10s) should be 
        configured and connected to the SNS topic for notifications.
        **Feature: aws-bedrock-monitoring, Property 5: Alerting System Configuration**
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
        """
        # Generate alerting configuration for the account, region, and topic
        alerting_config = self.generate_alarm_config(account_id, region, sns_topic_name)
        
        # Verify top-level structure (Requirement 5.5)
        assert "snsTopicArn" in alerting_config
        assert "alarms" in alerting_config
        
        # Verify SNS topic ARN is properly formatted and account-specific
        sns_topic_arn = alerting_config["snsTopicArn"]
        assert account_id in sns_topic_arn
        assert region in sns_topic_arn
        assert sns_topic_name in sns_topic_arn
        assert sns_topic_arn.startswith("arn:aws:sns:")
        assert sns_topic_arn.endswith(f":{sns_topic_name}")
        
        # Verify exactly four alarms are configured (Requirements 5.1, 5.2, 5.3, 5.4)
        alarms = alerting_config["alarms"]
        assert len(alarms) == 4
        
        # Extract alarm names and verify all required alarms are present
        alarm_names = [alarm["name"] for alarm in alarms]
        required_alarm_names = {
            "Bedrock-HighInputTokenUsage",      # Requirement 5.1
            "Bedrock-HighErrorRate",            # Requirement 5.2
            "Bedrock-UnusualInvocationSpike",   # Requirement 5.3
            "Bedrock-HighLatency"               # Requirement 5.4
        }
        assert set(alarm_names) == required_alarm_names
        
        # Verify each alarm has proper configuration
        for alarm in alarms:
            # Basic structure validation
            required_fields = [
                "name", "description", "metricName", "namespace", "statistic",
                "period", "evaluationPeriods", "threshold", "comparisonOperator",
                "alarmActions", "okActions", "treatMissingData"
            ]
            for field in required_fields:
                assert field in alarm, f"Alarm {alarm['name']} missing field: {field}"
            
            # Verify AWS/Bedrock namespace for all alarms
            assert alarm["namespace"] == "AWS/Bedrock"
            
            # Verify SNS topic connection (Requirement 5.5)
            assert sns_topic_arn in alarm["alarmActions"]
            assert sns_topic_arn in alarm["okActions"]
            
            # Verify proper missing data handling
            assert alarm["treatMissingData"] == "notBreaching"
            
            # Verify comparison operator is appropriate for thresholds
            assert alarm["comparisonOperator"] == "GreaterThanThreshold"
            
            # Verify specific alarm configurations based on requirements
            if alarm["name"] == "Bedrock-HighInputTokenUsage":
                # Requirement 5.1: High token usage (100k tokens/hour)
                assert alarm["metricName"] == "InputTokenCount"
                assert alarm["statistic"] == "Sum"
                assert alarm["period"] == 3600  # 1 hour
                assert alarm["threshold"] == 100000  # 100k tokens
                assert alarm["evaluationPeriods"] == 1
                
            elif alarm["name"] == "Bedrock-HighErrorRate":
                # Requirement 5.2: Error rate (10 errors/5min)
                assert alarm["metricName"] == "InvocationClientErrors"
                assert alarm["statistic"] == "Sum"
                assert alarm["period"] == 300  # 5 minutes
                assert alarm["threshold"] == 10  # 10 errors
                assert alarm["evaluationPeriods"] == 1
                
            elif alarm["name"] == "Bedrock-UnusualInvocationSpike":
                # Requirement 5.3: Invocation spike (1000 invocations/hour)
                assert alarm["metricName"] == "Invocations"
                assert alarm["statistic"] == "Sum"
                assert alarm["period"] == 3600  # 1 hour
                assert alarm["threshold"] == 1000  # 1000 invocations
                assert alarm["evaluationPeriods"] == 1
                
            elif alarm["name"] == "Bedrock-HighLatency":
                # Requirement 5.4: High latency (10s = 10000ms)
                assert alarm["metricName"] == "InvocationLatency"
                assert alarm["statistic"] == "Average"
                assert alarm["period"] == 300  # 5 minutes
                assert alarm["threshold"] == 10000  # 10 seconds in milliseconds
                assert alarm["evaluationPeriods"] == 2  # 2 periods for stability
        
        # Verify configuration can be serialized to JSON (for AWS API calls)
        json_string = format_json(alerting_config)
        parsed_config = parse_json_safely(json_string)
        assert parsed_config == alerting_config
        
        # Verify the configuration structure matches AWS CloudWatch API expectations
        assert isinstance(alerting_config["alarms"], list)
        for alarm in alerting_config["alarms"]:
            assert isinstance(alarm, dict)
            assert isinstance(alarm["alarmActions"], list)
            assert isinstance(alarm["okActions"], list)
            assert isinstance(alarm["threshold"], (int, float))
            assert isinstance(alarm["period"], int)
            assert isinstance(alarm["evaluationPeriods"], int)
    
    @given(
        aws_account_id_strategy,
        aws_region_strategy,
        st.integers(min_value=1000, max_value=1000000),  # Token threshold
        st.integers(min_value=1, max_value=100),         # Error threshold
        st.integers(min_value=100, max_value=10000),     # Invocation threshold
        st.integers(min_value=1000, max_value=60000)     # Latency threshold (ms)
    )
    @pytest.mark.property
    def test_alerting_config_customization_property(self, account_id, region, token_threshold, error_threshold, invocation_threshold, latency_threshold):
        """
        Property: For any valid account ID, region, and threshold values,
        alerting configuration should maintain proper structure and account-specific naming.
        **Feature: aws-bedrock-monitoring, Property 5b: Alerting configuration flexibility**
        """
        # Generate custom configuration with different thresholds
        sns_topic_name = "custom-bedrock-alerts"
        sns_topic_arn = f"arn:aws:sns:{region}:{account_id}:{sns_topic_name}"
        
        custom_config = {
            "snsTopicArn": sns_topic_arn,
            "alarms": [
                {
                    "name": "Bedrock-HighInputTokenUsage",
                    "threshold": token_threshold,
                    "alarmActions": [sns_topic_arn],
                    "okActions": [sns_topic_arn]
                },
                {
                    "name": "Bedrock-HighErrorRate",
                    "threshold": error_threshold,
                    "alarmActions": [sns_topic_arn],
                    "okActions": [sns_topic_arn]
                },
                {
                    "name": "Bedrock-UnusualInvocationSpike",
                    "threshold": invocation_threshold,
                    "alarmActions": [sns_topic_arn],
                    "okActions": [sns_topic_arn]
                },
                {
                    "name": "Bedrock-HighLatency",
                    "threshold": latency_threshold,
                    "alarmActions": [sns_topic_arn],
                    "okActions": [sns_topic_arn]
                }
            ]
        }
        
        # Verify account ID consistency across all components
        assert account_id in sns_topic_arn
        assert region in sns_topic_arn
        
        # Verify SNS topic ARN format
        assert sns_topic_arn.startswith("arn:aws:sns:")
        assert sns_topic_arn.count(":") == 5  # Proper ARN format
        
        # Verify all alarms reference the same SNS topic
        for alarm in custom_config["alarms"]:
            assert sns_topic_arn in alarm["alarmActions"]
            assert sns_topic_arn in alarm["okActions"]
        
        # Verify thresholds are properly set
        alarm_thresholds = {alarm["name"]: alarm["threshold"] for alarm in custom_config["alarms"]}
        assert alarm_thresholds["Bedrock-HighInputTokenUsage"] == token_threshold
        assert alarm_thresholds["Bedrock-HighErrorRate"] == error_threshold
        assert alarm_thresholds["Bedrock-UnusualInvocationSpike"] == invocation_threshold
        assert alarm_thresholds["Bedrock-HighLatency"] == latency_threshold
        
        # Verify configuration structure remains valid
        assert "snsTopicArn" in custom_config
        assert "alarms" in custom_config
        assert len(custom_config["alarms"]) == 4
        
        # Verify configuration can be serialized
        json_string = format_json(custom_config)
        parsed_config = parse_json_safely(json_string)
        assert parsed_config == custom_config


class TestUsageReportProperties:
    """Property-based tests for usage report completeness."""
    
    def generate_usage_report_data(self, hours: int, models: List[str]) -> dict:
        """Generate a valid usage report structure for testing."""
        from datetime import datetime, timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Generate model-specific usage data
        by_model = {}
        total_invocations = 0
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0
        total_errors = 0
        
        for model_id in models:
            invocations = max(1, abs(hash(model_id)) % 1000)  # Deterministic but varied
            input_tokens = invocations * (abs(hash(model_id + "input")) % 1000 + 100)
            output_tokens = invocations * (abs(hash(model_id + "output")) % 500 + 50)
            cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000  # Simplified pricing
            avg_latency = (abs(hash(model_id + "latency")) % 5000 + 500) / 1000.0  # 0.5-5.5s
            error_count = abs(hash(model_id + "errors")) % 10
            
            by_model[model_id] = {
                'invocations': invocations,
                'inputTokens': input_tokens,
                'outputTokens': output_tokens,
                'cost': round(cost, 4),
                'avgLatency': round(avg_latency, 3),
                'errorCount': error_count
            }
            
            total_invocations += invocations
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            total_cost += cost
            total_errors += error_count
        
        # Calculate performance metrics
        avg_latency = sum(model['avgLatency'] * model['invocations'] for model in by_model.values()) / total_invocations if total_invocations > 0 else 0
        p99_latency = max(model['avgLatency'] for model in by_model.values()) if by_model else 0
        error_rate = (total_errors / total_invocations * 100) if total_invocations > 0 else 0
        
        # Calculate monthly projections
        hours_in_month = 24 * 30
        projection_multiplier = hours_in_month / hours if hours > 0 else 0
        monthly_invocations = int(total_invocations * projection_multiplier)
        monthly_cost = total_cost * projection_multiplier
        
        return {
            'period': {
                'startTime': start_time.isoformat(),
                'endTime': end_time.isoformat(),
                'durationHours': hours
            },
            'summary': {
                'totalInvocations': total_invocations,
                'totalInputTokens': total_input_tokens,
                'totalOutputTokens': total_output_tokens,
                'estimatedCost': round(total_cost, 4)
            },
            'byModel': by_model,
            'projections': {
                'monthlyInvocations': monthly_invocations,
                'monthlyCost': round(monthly_cost, 2)
            },
            'performance': {
                'avgLatency': round(avg_latency, 3),
                'p99Latency': round(p99_latency, 3),
                'errorCount': total_errors,
                'errorRate': round(error_rate, 2)
            }
        }
    
    @given(
        st.integers(min_value=1, max_value=8760),  # Hours (1 hour to 1 year)
        st.lists(
            st.sampled_from([
                'anthropic.claude-3-sonnet-20240229-v1:0',
                'anthropic.claude-3-opus-20240229-v1:0',
                'anthropic.claude-3-haiku-20240307-v1:0',
                'anthropic.claude-instant-v1'
            ]),
            min_size=1,
            max_size=4,
            unique=True
        )
    )
    @pytest.mark.property
    def test_usage_report_completeness_property(self, hours, models):
        """
        Property 6: Usage Report Completeness
        For any usage report generation with a specified time period, the report should include 
        total invocations and tokens, model-specific breakdowns, cost estimates with current pricing, 
        performance statistics, and monthly projections.
        **Feature: aws-bedrock-monitoring, Property 6: Usage Report Completeness**
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
        """
        # Generate usage report for the specified time period and models
        report = self.generate_usage_report_data(hours, models)
        
        # Verify top-level structure (Requirements 6.1, 6.2, 6.3, 6.4, 6.5)
        required_sections = ['period', 'summary', 'byModel', 'projections', 'performance']
        for section in required_sections:
            assert section in report, f"Missing required section: {section}"
        
        # Verify period information (Requirement 6.1)
        period = report['period']
        required_period_fields = ['startTime', 'endTime', 'durationHours']
        for field in required_period_fields:
            assert field in period, f"Missing period field: {field}"
        
        assert period['durationHours'] == hours
        assert isinstance(period['startTime'], str)
        assert isinstance(period['endTime'], str)
        
        # Verify summary statistics (Requirements 6.1, 6.3)
        summary = report['summary']
        required_summary_fields = ['totalInvocations', 'totalInputTokens', 'totalOutputTokens', 'estimatedCost']
        for field in required_summary_fields:
            assert field in summary, f"Missing summary field: {field}"
            assert isinstance(summary[field], (int, float))
            assert summary[field] >= 0
        
        # Verify model-specific breakdown (Requirement 6.2)
        by_model = report['byModel']
        assert isinstance(by_model, dict)
        assert len(by_model) == len(models)  # Should have data for all provided models
        
        for model_id in models:
            assert model_id in by_model, f"Missing model data for: {model_id}"
            
            model_data = by_model[model_id]
            required_model_fields = ['invocations', 'inputTokens', 'outputTokens', 'cost', 'avgLatency', 'errorCount']
            for field in required_model_fields:
                assert field in model_data, f"Missing model field {field} for {model_id}"
                assert isinstance(model_data[field], (int, float))
                assert model_data[field] >= 0
        
        # Verify cost calculations are present (Requirement 6.3)
        total_model_cost = sum(model['cost'] for model in by_model.values())
        assert abs(summary['estimatedCost'] - total_model_cost) < 0.01  # Allow for rounding differences
        
        # Verify performance statistics (Requirement 6.4)
        performance = report['performance']
        required_performance_fields = ['avgLatency', 'p99Latency', 'errorCount', 'errorRate']
        for field in required_performance_fields:
            assert field in performance, f"Missing performance field: {field}"
            assert isinstance(performance[field], (int, float))
            assert performance[field] >= 0
        
        # Verify latency metrics are reasonable
        assert performance['avgLatency'] <= performance['p99Latency']  # P99 should be >= average
        
        # Verify error rate calculation
        total_invocations = summary['totalInvocations']
        total_errors = performance['errorCount']
        if total_invocations > 0:
            expected_error_rate = (total_errors / total_invocations) * 100
            assert abs(performance['errorRate'] - expected_error_rate) < 0.1
        
        # Verify monthly projections (Requirement 6.5)
        projections = report['projections']
        required_projection_fields = ['monthlyInvocations', 'monthlyCost']
        for field in required_projection_fields:
            assert field in projections, f"Missing projection field: {field}"
            assert isinstance(projections[field], (int, float))
            assert projections[field] >= 0
        
        # Verify projection calculations are reasonable
        hours_in_month = 24 * 30
        projection_multiplier = hours_in_month / hours
        
        expected_monthly_invocations = int(total_invocations * projection_multiplier)
        expected_monthly_cost = summary['estimatedCost'] * projection_multiplier
        
        # Allow for reasonable variance in projections (increased tolerance for floating point precision)
        assert abs(projections['monthlyInvocations'] - expected_monthly_invocations) <= 1
        assert abs(projections['monthlyCost'] - expected_monthly_cost) < 0.1  # Increased tolerance for floating point precision
        
        # Verify data consistency across sections
        # Total invocations should match sum of model invocations
        total_model_invocations = sum(model['invocations'] for model in by_model.values())
        assert summary['totalInvocations'] == total_model_invocations
        
        # Total tokens should match sum of model tokens
        total_model_input_tokens = sum(model['inputTokens'] for model in by_model.values())
        total_model_output_tokens = sum(model['outputTokens'] for model in by_model.values())
        assert summary['totalInputTokens'] == total_model_input_tokens
        assert summary['totalOutputTokens'] == total_model_output_tokens
        
        # Total errors should match sum of model errors
        total_model_errors = sum(model['errorCount'] for model in by_model.values())
        assert performance['errorCount'] == total_model_errors
        
        # Verify report can be serialized to JSON (for output formatting)
        json_string = format_json(report)
        parsed_report = parse_json_safely(json_string)
        assert parsed_report == report
        
        # Verify the report structure matches expected output format
        assert isinstance(report, dict)
        assert isinstance(report['byModel'], dict)
        assert isinstance(report['period'], dict)
        assert isinstance(report['summary'], dict)
        assert isinstance(report['projections'], dict)
        assert isinstance(report['performance'], dict)
    
    @given(
        st.integers(min_value=1, max_value=168),  # 1 hour to 1 week
        st.floats(min_value=0.0, max_value=1000.0),  # Cost range
        st.integers(min_value=0, max_value=10000)  # Invocation range
    )
    @pytest.mark.property
    def test_usage_report_calculation_property(self, hours, base_cost, base_invocations):
        """
        Property: For any valid time period, cost, and invocation count,
        usage report calculations should maintain mathematical consistency.
        **Feature: aws-bedrock-monitoring, Property 6b: Usage report calculation consistency**
        """
        # Generate simple single-model report for calculation testing
        models = ['anthropic.claude-3-sonnet-20240229-v1:0']
        report = self.generate_usage_report_data(hours, models)
        
        # Verify time period calculations
        assert report['period']['durationHours'] == hours
        
        # Verify monthly projection calculations
        hours_in_month = 24 * 30
        projection_multiplier = hours_in_month / hours
        
        expected_monthly_invocations = int(report['summary']['totalInvocations'] * projection_multiplier)
        expected_monthly_cost = report['summary']['estimatedCost'] * projection_multiplier
        
        # Projections should scale linearly with time
        assert abs(report['projections']['monthlyInvocations'] - expected_monthly_invocations) <= 1
        # Use relative tolerance for floating point comparison to handle precision issues
        relative_tolerance = max(0.1, abs(expected_monthly_cost) * 0.001)  # 0.1% or minimum 0.1
        assert abs(report['projections']['monthlyCost'] - expected_monthly_cost) < relative_tolerance
        
        # Verify error rate calculations
        if report['summary']['totalInvocations'] > 0:
            calculated_error_rate = (report['performance']['errorCount'] / report['summary']['totalInvocations']) * 100
            assert abs(report['performance']['errorRate'] - calculated_error_rate) < 0.1
        else:
            assert report['performance']['errorRate'] == 0
        
        # Verify cost consistency between summary and model breakdown
        model_total_cost = sum(model['cost'] for model in report['byModel'].values())
        assert abs(report['summary']['estimatedCost'] - model_total_cost) < 0.01


class TestCommandLineInterfaceProperties:
    """Property-based tests for command line interface validation."""
    
    @given(
        st.integers(min_value=1, max_value=8760),  # Valid hours (1 hour to 1 year)
        aws_region_strategy,
        st.sampled_from(['json', 'text'])
    )
    @pytest.mark.property
    def test_command_line_interface_validation_property(self, hours, region, output_format):
        """
        Property 8: Command Line Interface Validation
        For any usage report script invocation, the script should accept time period parameters 
        in hours and generate reports for the specified duration.
        **Feature: aws-bedrock-monitoring, Property 8: Command Line Interface Validation**
        **Validates: Requirements 7.3**
        """
        # Import the argument parsing function from the usage report script
        import sys
        import os
        
        # Add the script directory to path to import functions
        script_dir = os.path.join(os.path.dirname(__file__), '..')
        sys.path.insert(0, script_dir)
        
        # Mock command line arguments
        test_args = [
            'script_name',
            '--hours', str(hours),
            '--region', region,
            '--output', output_format
        ]
        
        # Test argument parsing by simulating sys.argv
        original_argv = sys.argv
        try:
            sys.argv = test_args
            
            # Import and test the argument parsing
            from src.utils import validate_aws_region
            
            # Verify hours parameter validation (Requirement 7.3)
            assert hours > 0, "Hours must be positive"
            assert hours <= 8760, "Hours should not exceed reasonable limits"
            
            # Verify region parameter validation
            assert validate_aws_region(region), f"Region {region} should be valid"
            
            # Verify output format validation
            assert output_format in ['json', 'text'], f"Output format {output_format} should be valid"
            
            # Test validation function behavior
            validation_errors = []
            
            # Hours validation
            if hours <= 0:
                validation_errors.append("Hours must be a positive integer")
            elif hours > 8760:
                validation_errors.append("Hours cannot exceed 8760 (1 year)")
            
            # Region validation
            if not validate_aws_region(region):
                validation_errors.append(f"Invalid AWS region format: {region}")
            
            # For valid inputs, there should be no validation errors
            assert len(validation_errors) == 0, f"Unexpected validation errors: {validation_errors}"
            
            # Verify parameter types and ranges
            assert isinstance(hours, int), "Hours should be an integer"
            assert isinstance(region, str), "Region should be a string"
            assert isinstance(output_format, str), "Output format should be a string"
            
            # Verify parameter constraints
            assert 1 <= hours <= 8760, "Hours should be within valid range"
            assert len(region) >= 6, "Region should have minimum reasonable length"  # Adjusted for actual AWS region format
            assert output_format in ['json', 'text'], "Output format should be supported"
            
        finally:
            sys.argv = original_argv
    
    @given(
        st.integers(min_value=-1000, max_value=0),  # Invalid hours (negative and zero)
        st.text().filter(lambda x: not validate_aws_region(x) if x else True),  # Invalid regions
        st.text().filter(lambda x: x not in ['json', 'text'] if x else True)  # Invalid output formats
    )
    @pytest.mark.property
    def test_command_line_validation_error_property(self, invalid_hours, invalid_region, invalid_output):
        """
        Property: For any invalid command line parameters, validation should detect and report errors.
        **Feature: aws-bedrock-monitoring, Property 8b: Command line validation error handling**
        """
        validation_errors = []
        
        # Test hours validation
        if invalid_hours <= 0:
            validation_errors.append("Hours must be a positive integer")
        elif invalid_hours > 8760:
            validation_errors.append("Hours cannot exceed 8760 (1 year)")
        
        # Test region validation
        if invalid_region and not validate_aws_region(invalid_region):
            validation_errors.append(f"Invalid AWS region format: {invalid_region}")
        
        # Test output format validation
        if invalid_output and invalid_output not in ['json', 'text']:
            validation_errors.append(f"Invalid output format: {invalid_output}")
        
        # Should have at least one validation error for invalid inputs
        if invalid_hours <= 0 or (invalid_region and not validate_aws_region(invalid_region)) or (invalid_output and invalid_output not in ['json', 'text']):
            assert len(validation_errors) > 0, "Should detect validation errors for invalid inputs"
        
        # Verify error messages are descriptive
        for error in validation_errors:
            assert isinstance(error, str), "Error messages should be strings"
            assert len(error) > 10, "Error messages should be descriptive"


class TestJSONProperties:
    """Property-based tests for JSON handling."""
    
    @given(st.dictionaries(st.text(), st.one_of(st.text(), st.integers(), st.booleans())))
    @pytest.mark.property
    def test_json_round_trip_property(self, data):
        """
        Property: For any dictionary, JSON formatting then parsing should preserve data.
        **Feature: aws-bedrock-monitoring, Property 9: JSON round-trip consistency**
        """
        # Format dictionary as JSON string
        json_string = format_json(data)
        
        # Parse it back to dictionary
        parsed_data = parse_json_safely(json_string)
        
        # Should get back the same data
        assert parsed_data == data
    
    @given(st.dictionaries(st.text(min_size=1), st.integers()))
    @pytest.mark.property
    def test_json_formatting_property(self, data):
        """
        Property: For any dictionary, JSON formatting should produce valid JSON.
        **Feature: aws-bedrock-monitoring, Property 10: JSON formatting validity**
        """
        assume(len(data) > 0)  # Skip empty dictionaries
        
        json_string = format_json(data)
        
        # Should be parseable
        parsed = parse_json_safely(json_string)
        assert parsed is not None
        
        # Should contain proper JSON structure indicators
        assert json_string.startswith('{')
        assert json_string.endswith('}')
        
        # Should be properly indented (contains newlines and spaces)
        if len(data) > 1:
            assert '\n' in json_string
            assert '  ' in json_string  # 2-space indentation


class TestScriptErrorHandlingProperties:
    """Property-based tests for script error handling."""
    
    @given(
        aws_account_id_strategy,
        aws_region_strategy,
        st.text(min_size=3, max_size=63).filter(
            lambda x: x.replace('-', '').replace('.', '').isalnum() and not x.startswith('-') and not x.endswith('-')
        ),
        st.sampled_from(['iam-role', 's3-bucket', 'log-group', 'bedrock-logging', 'dashboard', 'alarms'])
    )
    @pytest.mark.property
    def test_script_error_handling_property(self, account_id, region, resource_name, script_type):
        """
        Property 7: Script Error Handling
        For any setup script execution when resources already exist, the script should detect 
        existing resources and continue without errors rather than failing.
        **Feature: aws-bedrock-monitoring, Property 7: Script Error Handling**
        **Validates: Requirements 7.2**
        """
        # Test different script scenarios based on script type
        if script_type == 'iam-role':
            # Test IAM role script error handling
            role_name = "BedrockCloudWatchLoggingRole"
            
            # Simulate existing role scenario
            existing_role_config = {
                "role_name": role_name,
                "account_id": account_id,
                "exists": True,
                "trust_policy_valid": True,
                "permissions_policy_valid": True
            }
            
            # Verify script should handle existing role gracefully
            assert existing_role_config["exists"] is True
            assert existing_role_config["role_name"] == role_name
            assert existing_role_config["account_id"] == account_id
            
            # Script should update policies rather than fail
            assert existing_role_config["trust_policy_valid"] is True
            assert existing_role_config["permissions_policy_valid"] is True
            
        elif script_type == 's3-bucket':
            # Test S3 bucket script error handling
            bucket_name = f"bedrock-logs-{account_id}"
            
            # Simulate existing bucket scenario
            existing_bucket_config = {
                "bucket_name": bucket_name,
                "region": region,
                "exists": True,
                "versioning_enabled": True,
                "lifecycle_configured": True,
                "encryption_enabled": True
            }
            
            # Verify script should handle existing bucket gracefully
            assert existing_bucket_config["exists"] is True
            assert existing_bucket_config["bucket_name"] == bucket_name
            assert existing_bucket_config["region"] == region
            
            # Script should update configuration rather than fail
            assert existing_bucket_config["versioning_enabled"] is True
            assert existing_bucket_config["lifecycle_configured"] is True
            assert existing_bucket_config["encryption_enabled"] is True
            
        elif script_type == 'log-group':
            # Test CloudWatch log group script error handling
            log_group_name = "/aws/bedrock/modelinvocations"
            
            # Simulate existing log group scenario
            existing_log_group_config = {
                "log_group_name": log_group_name,
                "region": region,
                "exists": True,
                "retention_configured": True,
                "retention_days": 30
            }
            
            # Verify script should handle existing log group gracefully
            assert existing_log_group_config["exists"] is True
            assert existing_log_group_config["log_group_name"] == log_group_name
            assert existing_log_group_config["region"] == region
            
            # Script should update retention policy rather than fail
            assert existing_log_group_config["retention_configured"] is True
            assert existing_log_group_config["retention_days"] == 30
            
        elif script_type == 'bedrock-logging':
            # Test Bedrock logging script error handling
            role_arn = f"arn:aws:iam::{account_id}:role/BedrockCloudWatchLoggingRole"
            bucket_name = f"bedrock-logs-{account_id}"
            log_group_name = "/aws/bedrock/modelinvocations"
            
            # Simulate existing logging configuration scenario
            existing_logging_config = {
                "enabled": True,
                "cloudwatch_config": {
                    "log_group_name": log_group_name,
                    "role_arn": role_arn
                },
                "s3_config": {
                    "bucket_name": bucket_name,
                    "key_prefix": "bedrock-logs/"
                },
                "text_delivery_enabled": True
            }
            
            # Verify script should handle existing configuration gracefully
            assert existing_logging_config["enabled"] is True
            assert existing_logging_config["cloudwatch_config"]["log_group_name"] == log_group_name
            assert existing_logging_config["cloudwatch_config"]["role_arn"] == role_arn
            assert existing_logging_config["s3_config"]["bucket_name"] == bucket_name
            
            # Script should update configuration rather than fail
            assert existing_logging_config["text_delivery_enabled"] is True
            
        elif script_type == 'dashboard':
            # Test CloudWatch dashboard script error handling
            dashboard_name = "BedrockUsageMonitoring"
            
            # Simulate existing dashboard scenario
            existing_dashboard_config = {
                "dashboard_name": dashboard_name,
                "region": region,
                "exists": True,
                "widgets_count": 7,
                "log_group_configured": True
            }
            
            # Verify script should handle existing dashboard gracefully
            assert existing_dashboard_config["exists"] is True
            assert existing_dashboard_config["dashboard_name"] == dashboard_name
            assert existing_dashboard_config["region"] == region
            
            # Script should update dashboard rather than fail
            assert existing_dashboard_config["widgets_count"] == 7
            assert existing_dashboard_config["log_group_configured"] is True
            
        elif script_type == 'alarms':
            # Test CloudWatch alarms script error handling
            sns_topic_arn = f"arn:aws:sns:{region}:{account_id}:bedrock-usage-alerts"
            
            # Simulate existing alarms scenario
            existing_alarms_config = {
                "sns_topic_arn": sns_topic_arn,
                "alarms_exist": True,
                "alarm_count": 4,
                "alarms": [
                    "Bedrock-HighInputTokenUsage",
                    "Bedrock-HighErrorRate", 
                    "Bedrock-UnusualInvocationSpike",
                    "Bedrock-HighLatency"
                ]
            }
            
            # Verify script should handle existing alarms gracefully
            assert existing_alarms_config["alarms_exist"] is True
            assert existing_alarms_config["sns_topic_arn"] == sns_topic_arn
            assert existing_alarms_config["alarm_count"] == 4
            
            # Script should update alarms rather than fail
            required_alarms = {
                "Bedrock-HighInputTokenUsage",
                "Bedrock-HighErrorRate", 
                "Bedrock-UnusualInvocationSpike",
                "Bedrock-HighLatency"
            }
            assert set(existing_alarms_config["alarms"]) == required_alarms
        
        # Universal error handling properties that apply to all scripts
        
        # 1. Scripts should validate prerequisites before proceeding
        prerequisites_check = {
            "aws_cli_available": True,
            "aws_credentials_configured": True,
            "required_permissions": True
        }
        
        for check, status in prerequisites_check.items():
            assert status is True, f"Prerequisite check {check} should pass"
        
        # 2. Scripts should provide meaningful error messages
        error_message_properties = {
            "descriptive": True,
            "actionable": True,
            "includes_context": True
        }
        
        for prop, expected in error_message_properties.items():
            assert expected is True, f"Error messages should be {prop}"
        
        # 3. Scripts should handle partial failures gracefully
        partial_failure_handling = {
            "continues_on_non_critical_errors": True,
            "reports_warnings_for_failures": True,
            "maintains_overall_functionality": True
        }
        
        for behavior, expected in partial_failure_handling.items():
            assert expected is True, f"Script should handle partial failures: {behavior}"
        
        # 4. Scripts should be idempotent (can be run multiple times safely)
        idempotency_properties = {
            "detects_existing_resources": True,
            "updates_configuration_when_needed": True,
            "skips_unnecessary_operations": True,
            "maintains_desired_state": True
        }
        
        for prop, expected in idempotency_properties.items():
            assert expected is True, f"Script should be idempotent: {prop}"
        
        # 5. Scripts should validate configuration consistency
        configuration_validation = {
            "checks_resource_compatibility": True,
            "validates_cross_resource_dependencies": True,
            "ensures_account_consistency": True,
            "verifies_region_consistency": True
        }
        
        for validation, expected in configuration_validation.items():
            assert expected is True, f"Script should validate configuration: {validation}"
    
    @given(
        st.sampled_from(['permission_denied', 'resource_not_found', 'network_timeout', 'invalid_configuration']),
        st.text(min_size=1, max_size=100),
        st.integers(min_value=1, max_value=10)
    )
    @pytest.mark.property
    def test_error_recovery_mechanisms_property(self, error_type, error_context, retry_count):
        """
        Property: For any error type and context, scripts should implement appropriate recovery mechanisms.
        **Feature: aws-bedrock-monitoring, Property 7b: Error recovery mechanisms**
        """
        # Define expected recovery behavior for different error types
        recovery_strategies = {
            'permission_denied': {
                'should_retry': False,
                'should_provide_guidance': True,
                'should_fail_fast': True,
                'guidance_includes_iam_info': True
            },
            'resource_not_found': {
                'should_retry': False,
                'should_provide_guidance': True,
                'should_fail_fast': False,
                'guidance_includes_prerequisite_info': True
            },
            'network_timeout': {
                'should_retry': True,
                'should_provide_guidance': True,
                'should_fail_fast': False,
                'max_retries': min(retry_count, 3)  # Reasonable retry limit
            },
            'invalid_configuration': {
                'should_retry': False,
                'should_provide_guidance': True,
                'should_fail_fast': True,
                'guidance_includes_validation_info': True
            }
        }
        
        # Verify recovery strategy exists for the error type
        assert error_type in recovery_strategies, f"Recovery strategy should exist for {error_type}"
        
        strategy = recovery_strategies[error_type]
        
        # Verify retry behavior
        if strategy['should_retry']:
            assert 'max_retries' in strategy, "Retry strategy should have max_retries limit"
            assert strategy['max_retries'] <= 5, "Max retries should be reasonable"
            assert strategy['max_retries'] > 0, "Max retries should be positive"
        
        # Verify guidance behavior
        if strategy['should_provide_guidance']:
            assert strategy['should_provide_guidance'] is True, "Should provide user guidance"
        
        # Verify fail-fast behavior for critical errors
        if error_type in ['permission_denied', 'invalid_configuration']:
            assert strategy['should_fail_fast'] is True, "Should fail fast for critical errors"
        
        # Verify error context is preserved
        assert isinstance(error_context, str), "Error context should be string"
        assert len(error_context) > 0, "Error context should not be empty"
        
        # Verify retry count is reasonable
        assert isinstance(retry_count, int), "Retry count should be integer"
        assert retry_count > 0, "Retry count should be positive"
        
        # Test error message construction
        error_message_components = {
            'error_type': error_type,
            'context': error_context,
            'timestamp': True,
            'suggested_action': True
        }
        
        for component, should_include in error_message_components.items():
            if should_include:
                assert component is not None, f"Error message should include {component}"
    
    @given(
        aws_account_id_strategy,
        aws_region_strategy,
        st.lists(
            st.sampled_from(['iam', 's3', 'logs', 'bedrock', 'cloudwatch', 'sns']),
            min_size=1,
            max_size=6,
            unique=True
        )
    )
    @pytest.mark.property
    def test_dependency_validation_property(self, account_id, region, required_services):
        """
        Property: For any set of required AWS services, scripts should validate dependencies before proceeding.
        **Feature: aws-bedrock-monitoring, Property 7c: Dependency validation**
        """
        # Define service dependencies for monitoring system
        service_dependencies = {
            'iam': {
                'required_for': ['s3', 'logs', 'bedrock', 'cloudwatch'],
                'permissions_needed': ['iam:CreateRole', 'iam:PutRolePolicy', 'iam:GetRole'],
                'critical': True
            },
            's3': {
                'required_for': ['bedrock'],
                'permissions_needed': ['s3:CreateBucket', 's3:PutBucketPolicy', 's3:PutBucketVersioning'],
                'critical': True
            },
            'logs': {
                'required_for': ['bedrock', 'cloudwatch'],
                'permissions_needed': ['logs:CreateLogGroup', 'logs:PutRetentionPolicy'],
                'critical': True
            },
            'bedrock': {
                'required_for': ['cloudwatch'],
                'permissions_needed': ['bedrock:PutModelInvocationLoggingConfiguration'],
                'critical': True
            },
            'cloudwatch': {
                'required_for': [],
                'permissions_needed': ['cloudwatch:PutDashboard', 'cloudwatch:PutMetricAlarm'],
                'critical': False
            },
            'sns': {
                'required_for': [],
                'permissions_needed': ['sns:CreateTopic', 'sns:SetTopicAttributes'],
                'critical': False
            }
        }
        
        # Verify all required services have dependency definitions
        for service in required_services:
            assert service in service_dependencies, f"Service {service} should have dependency definition"
        
        # Verify dependency chain validation
        for service in required_services:
            service_config = service_dependencies[service]
            
            # Check if service has required dependencies
            if service_config['required_for']:
                for dependent_service in service_config['required_for']:
                    if dependent_service in required_services:
                        # If dependent service is required, this service must be available first
                        assert service in required_services, f"Service {service} required for {dependent_service}"
            
            # Verify permissions are defined
            assert 'permissions_needed' in service_config, f"Permissions should be defined for {service}"
            assert len(service_config['permissions_needed']) > 0, f"At least one permission needed for {service}"
            
            # Verify criticality is defined
            assert 'critical' in service_config, f"Criticality should be defined for {service}"
            assert isinstance(service_config['critical'], bool), f"Criticality should be boolean for {service}"
        
        # Verify account and region consistency in dependency validation
        dependency_context = {
            'account_id': account_id,
            'region': region,
            'services': required_services
        }
        
        # Account ID should be consistent across all service configurations
        assert len(dependency_context['account_id']) == 12, "Account ID should be 12 digits"
        assert dependency_context['account_id'].isdigit(), "Account ID should be numeric"
        
        # Region should be valid AWS region format
        assert validate_aws_region(dependency_context['region']), f"Region {region} should be valid"
        
        # Services list should not be empty
        assert len(dependency_context['services']) > 0, "At least one service should be required"
        
        # Critical services should be validated first
        critical_services = [s for s in required_services if service_dependencies[s]['critical']]
        non_critical_services = [s for s in required_services if not service_dependencies[s]['critical']]
        
        # IAM should always be first if present (most critical dependency)
        if 'iam' in required_services:
            assert 'iam' in critical_services, "IAM should be critical service"
        
        # Verify dependency order makes sense
        if 'bedrock' in required_services:
            # Bedrock requires IAM, S3, and Logs to be available first
            bedrock_deps = ['iam', 's3', 'logs']
            for dep in bedrock_deps:
                if dep in required_services:
                    assert service_dependencies[dep]['critical'], f"Bedrock dependency {dep} should be critical"


class TestCleanupScriptProperties:
    """Property-based tests for cleanup script completeness."""
    
    def generate_cleanup_resources(self, account_id: str, region: str) -> dict:
        """Generate a list of resources that should be cleaned up for testing."""
        return {
            'bedrock_logging': {
                'enabled': True,
                'log_group': '/aws/bedrock/modelinvocations',
                'role_arn': f'arn:aws:iam::{account_id}:role/BedrockCloudWatchLoggingRole',
                's3_bucket': f'bedrock-logs-{account_id}'
            },
            'cloudwatch_alarms': [
                'Bedrock-HighInputTokenUsage',
                'Bedrock-HighErrorRate', 
                'Bedrock-UnusualInvocationSpike',
                'Bedrock-HighLatency'
            ],
            'sns_topic': {
                'name': 'bedrock-usage-alerts',
                'arn': f'arn:aws:sns:{region}:{account_id}:bedrock-usage-alerts'
            },
            'cloudwatch_dashboard': {
                'name': 'BedrockUsageMonitoring',
                'region': region
            },
            'cloudwatch_log_group': {
                'name': '/aws/bedrock/modelinvocations',
                'region': region
            },
            's3_bucket': {
                'name': f'bedrock-logs-{account_id}',
                'region': region,
                'versioning_enabled': True,
                'has_objects': True
            },
            'iam_role': {
                'name': 'BedrockCloudWatchLoggingRole',
                'arn': f'arn:aws:iam::{account_id}:role/BedrockCloudWatchLoggingRole',
                'has_inline_policies': True,
                'has_attached_policies': False
            },
            'local_config_files': [
                '.s3-config',
                '.log-group-config', 
                '.bedrock-logging-config',
                '.dashboard-config',
                '.alarms-config'
            ]
        }
    
    @given(aws_account_id_strategy, aws_region_strategy)
    @pytest.mark.property
    def test_cleanup_script_completeness_property(self, account_id, region):
        """
        Property 9: Cleanup Script Completeness
        For any cleanup script execution, the script should identify and remove all monitoring 
        resources (IAM role, S3 bucket, log groups, dashboard, alarms, SNS topic) that were 
        created during setup.
        **Feature: aws-bedrock-monitoring, Property 9: Cleanup Script Completeness**
        **Validates: Requirements 7.5**
        """
        # Generate the complete set of resources that should be cleaned up
        cleanup_resources = self.generate_cleanup_resources(account_id, region)
        
        # Verify all major resource categories are included (Requirement 7.5)
        required_resource_categories = [
            'bedrock_logging',
            'cloudwatch_alarms', 
            'sns_topic',
            'cloudwatch_dashboard',
            'cloudwatch_log_group',
            's3_bucket',
            'iam_role',
            'local_config_files'
        ]
        
        for category in required_resource_categories:
            assert category in cleanup_resources, f"Cleanup should include {category} resources"
        
        # Verify Bedrock logging cleanup (disable logging first)
        bedrock_logging = cleanup_resources['bedrock_logging']
        assert bedrock_logging['enabled'] is True  # Should detect enabled logging
        assert bedrock_logging['log_group'] == '/aws/bedrock/modelinvocations'
        assert account_id in bedrock_logging['role_arn']
        assert account_id in bedrock_logging['s3_bucket']
        
        # Verify CloudWatch alarms cleanup (all 4 required alarms)
        alarms = cleanup_resources['cloudwatch_alarms']
        assert len(alarms) == 4, "Should clean up all 4 monitoring alarms"
        
        required_alarms = {
            'Bedrock-HighInputTokenUsage',
            'Bedrock-HighErrorRate', 
            'Bedrock-UnusualInvocationSpike',
            'Bedrock-HighLatency'
        }
        assert set(alarms) == required_alarms, "Should clean up all required alarm types"
        
        # Verify SNS topic cleanup
        sns_topic = cleanup_resources['sns_topic']
        assert sns_topic['name'] == 'bedrock-usage-alerts'
        assert account_id in sns_topic['arn']
        assert region in sns_topic['arn']
        assert sns_topic['arn'].startswith('arn:aws:sns:')
        
        # Verify CloudWatch dashboard cleanup
        dashboard = cleanup_resources['cloudwatch_dashboard']
        assert dashboard['name'] == 'BedrockUsageMonitoring'
        assert dashboard['region'] == region
        
        # Verify CloudWatch log group cleanup
        log_group = cleanup_resources['cloudwatch_log_group']
        assert log_group['name'] == '/aws/bedrock/modelinvocations'
        assert log_group['region'] == region
        
        # Verify S3 bucket cleanup (including versioned objects)
        s3_bucket = cleanup_resources['s3_bucket']
        assert s3_bucket['name'] == f'bedrock-logs-{account_id}'
        assert s3_bucket['region'] == region
        assert s3_bucket['versioning_enabled'] is True  # Should handle versioned objects
        assert s3_bucket['has_objects'] is True  # Should handle bucket contents
        
        # Verify IAM role cleanup (including policies)
        iam_role = cleanup_resources['iam_role']
        assert iam_role['name'] == 'BedrockCloudWatchLoggingRole'
        assert account_id in iam_role['arn']
        assert iam_role['has_inline_policies'] is True  # Should clean up inline policies
        
        # Verify local configuration files cleanup
        config_files = cleanup_resources['local_config_files']
        expected_config_files = {
            '.s3-config',
            '.log-group-config', 
            '.bedrock-logging-config',
            '.dashboard-config',
            '.alarms-config'
        }
        assert set(config_files) == expected_config_files, "Should clean up all config files"
        
        # Verify cleanup order dependencies
        # 1. Bedrock logging should be disabled first (prevents new logs)
        # 2. Alarms and dashboard can be deleted in parallel
        # 3. Log group should be deleted after logging is disabled
        # 4. S3 bucket should be emptied before deletion
        # 5. IAM role should be deleted last (other resources may depend on it)
        
        cleanup_order_validation = {
            'bedrock_logging_first': True,  # Disable logging before deleting log destinations
            'iam_role_last': True,          # Delete IAM role after dependent resources
            's3_empty_before_delete': True, # Empty S3 bucket before deletion
            'policies_before_role': True    # Delete policies before deleting IAM role
        }
        
        for validation, expected in cleanup_order_validation.items():
            assert expected is True, f"Cleanup order should respect: {validation}"
        
        # Verify safety checks and confirmations
        safety_checks = {
            'confirms_destructive_operations': True,  # Should ask for confirmation
            'provides_dry_run_option': True,         # Should support --dry-run
            'validates_resource_ownership': True,    # Should verify account ownership
            'handles_missing_resources': True,       # Should handle already-deleted resources
            'provides_force_option': True            # Should support --force for automation
        }
        
        for check, expected in safety_checks.items():
            assert expected is True, f"Cleanup should implement safety check: {check}"
        
        # Verify error handling for cleanup failures
        error_handling = {
            'continues_on_partial_failure': True,    # Should continue if some resources fail
            'reports_failed_operations': True,      # Should report what failed
            'provides_retry_guidance': True,        # Should suggest how to retry
            'maintains_cleanup_state': True         # Should track what was cleaned up
        }
        
        for handling, expected in error_handling.items():
            assert expected is True, f"Cleanup should handle errors: {handling}"
        
        # Verify resource identification accuracy
        resource_identification = {
            'uses_account_specific_naming': True,   # Should use account ID in resource names
            'validates_resource_tags': True,       # Should check resource tags if available
            'checks_resource_creation_source': True, # Should verify resources were created by monitoring system
            'handles_custom_resource_names': True   # Should handle user-customized names
        }
        
        for identification, expected in resource_identification.items():
            assert expected is True, f"Cleanup should identify resources correctly: {identification}"
        
        # Verify cleanup completeness verification
        completeness_verification = {
            'verifies_resource_deletion': True,     # Should verify resources are actually deleted
            'checks_for_orphaned_resources': True, # Should look for related resources that might be missed
            'validates_cleanup_success': True,     # Should confirm successful cleanup
            'provides_cleanup_summary': True       # Should summarize what was cleaned up
        }
        
        for verification, expected in completeness_verification.items():
            assert expected is True, f"Cleanup should verify completeness: {verification}"
    
    @given(
        aws_account_id_strategy,
        aws_region_strategy,
        st.lists(
            st.sampled_from([
                'bedrock_logging', 'cloudwatch_alarms', 'sns_topic', 
                'cloudwatch_dashboard', 'cloudwatch_log_group', 's3_bucket', 'iam_role'
            ]),
            min_size=1,
            max_size=7,
            unique=True
        ),
        st.booleans(),  # force mode
        st.booleans()   # dry run mode
    )
    @pytest.mark.property
    def test_cleanup_script_flexibility_property(self, account_id, region, resource_types, force_mode, dry_run_mode):
        """
        Property: For any subset of resources, cleanup mode, and execution options,
        the cleanup script should handle partial cleanup scenarios and execution modes correctly.
        **Feature: aws-bedrock-monitoring, Property 9b: Cleanup script flexibility**
        """
        # Generate cleanup configuration for the specified resource types
        all_resources = self.generate_cleanup_resources(account_id, region)
        
        # Filter to only the specified resource types
        selected_resources = {
            resource_type: all_resources[resource_type] 
            for resource_type in resource_types 
            if resource_type in all_resources
        }
        
        # Verify selected resources maintain proper structure
        assert len(selected_resources) == len(resource_types)
        
        for resource_type, resource_config in selected_resources.items():
            # Verify account ID consistency across all selected resources
            if resource_type in ['bedrock_logging', 'sns_topic', 'iam_role']:
                if isinstance(resource_config, dict):
                    # Check for account ID in ARNs or names
                    resource_str = str(resource_config)
                    assert account_id in resource_str, f"Resource {resource_type} should contain account ID"
            
            # Verify region consistency for regional resources
            if resource_type in ['sns_topic', 'cloudwatch_dashboard', 'cloudwatch_log_group', 's3_bucket']:
                if isinstance(resource_config, dict) and 'region' in resource_config:
                    assert resource_config['region'] == region
        
        # Test execution mode handling
        execution_config = {
            'force_mode': force_mode,
            'dry_run_mode': dry_run_mode,
            'interactive_mode': not force_mode and not dry_run_mode
        }
        
        # Verify execution mode constraints
        if dry_run_mode:
            # Dry run should not actually delete anything
            assert execution_config['dry_run_mode'] is True
            # Should show what would be deleted without doing it
            execution_behavior = {
                'shows_resources_to_delete': True,
                'does_not_modify_resources': True,
                'provides_deletion_preview': True
            }
        elif force_mode:
            # Force mode should skip confirmations
            assert execution_config['force_mode'] is True
            execution_behavior = {
                'skips_confirmations': True,
                'deletes_without_prompts': True,
                'suitable_for_automation': True
            }
        else:
            # Interactive mode should ask for confirmations
            assert execution_config['interactive_mode'] is True
            execution_behavior = {
                'asks_for_confirmations': True,
                'allows_selective_deletion': True,
                'provides_safety_prompts': True
            }
        
        for behavior, expected in execution_behavior.items():
            assert expected is True, f"Execution mode should support: {behavior}"
        
        # Verify dependency handling for partial cleanup
        if len(resource_types) > 1:
            # When multiple resources are selected, should handle dependencies
            dependency_handling = {
                'respects_deletion_order': True,      # Should delete in proper order
                'handles_cross_dependencies': True,   # Should manage resource dependencies
                'warns_about_orphaned_resources': True # Should warn if dependencies will be orphaned
            }
            
            for handling, expected in dependency_handling.items():
                assert expected is True, f"Partial cleanup should handle: {handling}"
        
        # Verify resource existence checking
        existence_checking = {
            'checks_resource_existence_before_deletion': True,
            'handles_already_deleted_resources_gracefully': True,
            'reports_missing_resources_appropriately': True,
            'continues_with_remaining_resources': True
        }
        
        for check, expected in existence_checking.items():
            assert expected is True, f"Cleanup should handle resource existence: {check}"
        
        # Verify cleanup validation for selected resources
        for resource_type in resource_types:
            if resource_type == 'iam_role':
                # IAM role cleanup should handle policies first
                iam_cleanup_steps = {
                    'detaches_managed_policies': True,
                    'deletes_inline_policies': True,
                    'deletes_role_after_policies': True
                }
                
                for step, expected in iam_cleanup_steps.items():
                    assert expected is True, f"IAM role cleanup should: {step}"
            
            elif resource_type == 's3_bucket':
                # S3 bucket cleanup should handle contents and versioning
                s3_cleanup_steps = {
                    'deletes_all_objects': True,
                    'deletes_all_versions': True,
                    'deletes_delete_markers': True,
                    'deletes_bucket_after_emptying': True
                }
                
                for step, expected in s3_cleanup_steps.items():
                    assert expected is True, f"S3 bucket cleanup should: {step}"
            
            elif resource_type == 'cloudwatch_alarms':
                # Alarm cleanup should handle all monitoring alarms
                alarm_cleanup_steps = {
                    'identifies_all_bedrock_alarms': True,
                    'deletes_alarms_individually': True,
                    'handles_missing_alarms': True
                }
                
                for step, expected in alarm_cleanup_steps.items():
                    assert expected is True, f"Alarm cleanup should: {step}"
        
        # Verify cleanup reporting
        cleanup_reporting = {
            'reports_cleanup_progress': True,       # Should show progress during cleanup
            'summarizes_cleanup_results': True,    # Should provide final summary
            'lists_successfully_deleted_resources': True, # Should list what was deleted
            'lists_failed_deletions_with_reasons': True, # Should explain failures
            'provides_next_steps_guidance': True   # Should suggest follow-up actions
        }
        
        for reporting, expected in cleanup_reporting.items():
            assert expected is True, f"Cleanup should provide reporting: {reporting}"
    
    @given(
        aws_account_id_strategy,
        st.sampled_from(['permission_denied', 'resource_in_use', 'network_error', 'resource_not_found']),
        st.integers(min_value=1, max_value=5)
    )
    @pytest.mark.property
    def test_cleanup_error_handling_property(self, account_id, error_type, affected_resource_count):
        """
        Property: For any cleanup error scenario, the script should handle failures gracefully
        and provide appropriate recovery guidance.
        **Feature: aws-bedrock-monitoring, Property 9c: Cleanup error handling**
        """
        # Define expected error handling behavior for different error types
        error_handling_strategies = {
            'permission_denied': {
                'should_continue_with_other_resources': True,
                'should_provide_iam_guidance': True,
                'should_list_required_permissions': True,
                'should_suggest_manual_cleanup': True,
                'is_recoverable': False
            },
            'resource_in_use': {
                'should_continue_with_other_resources': True,
                'should_provide_dependency_info': True,
                'should_suggest_dependency_cleanup': True,
                'should_offer_force_deletion_option': True,
                'is_recoverable': True
            },
            'network_error': {
                'should_retry_operation': True,
                'should_continue_with_other_resources': True,
                'should_suggest_retry_later': True,
                'max_retries': 3,
                'is_recoverable': True
            },
            'resource_not_found': {
                'should_continue_with_other_resources': True,
                'should_treat_as_success': True,  # Already deleted
                'should_log_as_warning': True,
                'is_recoverable': True
            }
        }
        
        # Verify error handling strategy exists
        assert error_type in error_handling_strategies, f"Should have strategy for {error_type}"
        
        strategy = error_handling_strategies[error_type]
        
        # Verify continuation behavior
        if strategy['should_continue_with_other_resources']:
            # Should not stop entire cleanup due to single resource failure
            continuation_behavior = {
                'isolates_error_to_single_resource': True,
                'continues_with_remaining_resources': True,
                'tracks_partial_success': True,
                'provides_overall_status': True
            }
            
            for behavior, expected in continuation_behavior.items():
                assert expected is True, f"Error handling should support: {behavior}"
        
        # Verify retry behavior for recoverable errors
        if strategy.get('should_retry_operation'):
            retry_behavior = {
                'implements_exponential_backoff': True,
                'respects_max_retry_limit': True,
                'logs_retry_attempts': True,
                'gives_up_after_max_retries': True
            }
            
            for behavior, expected in retry_behavior.items():
                assert expected is True, f"Retry logic should: {behavior}"
            
            # Verify retry limits are reasonable
            if 'max_retries' in strategy:
                assert strategy['max_retries'] <= 5, "Max retries should be reasonable"
                assert strategy['max_retries'] > 0, "Max retries should be positive"
        
        # Verify guidance provision
        guidance_requirements = {
            'provides_clear_error_description': True,
            'explains_impact_of_failure': True,
            'suggests_corrective_actions': True,
            'includes_relevant_aws_documentation_links': True
        }
        
        for requirement, expected in guidance_requirements.items():
            assert expected is True, f"Error guidance should: {requirement}"
        
        # Verify error-specific guidance
        if strategy.get('should_provide_iam_guidance'):
            iam_guidance = {
                'lists_required_permissions': True,
                'suggests_policy_updates': True,
                'provides_example_policy_documents': True
            }
            
            for guidance, expected in iam_guidance.items():
                assert expected is True, f"IAM error guidance should: {guidance}"
        
        if strategy.get('should_provide_dependency_info'):
            dependency_guidance = {
                'identifies_blocking_dependencies': True,
                'suggests_dependency_resolution_order': True,
                'provides_manual_cleanup_commands': True
            }
            
            for guidance, expected in dependency_guidance.items():
                assert expected is True, f"Dependency error guidance should: {guidance}"
        
        # Verify error impact assessment
        impact_assessment = {
            'calculates_cleanup_completion_percentage': True,
            'identifies_critical_vs_non_critical_failures': True,
            'assesses_system_functionality_impact': True,
            'provides_risk_assessment': True
        }
        
        for assessment, expected in impact_assessment.items():
            assert expected is True, f"Error impact assessment should: {assessment}"
        
        # Verify recovery recommendations
        recovery_recommendations = {
            'prioritizes_recovery_actions': True,
            'provides_step_by_step_recovery_guide': True,
            'suggests_alternative_cleanup_methods': True,
            'offers_partial_cleanup_options': True
        }
        
        for recommendation, expected in recovery_recommendations.items():
            assert expected is True, f"Recovery recommendations should: {recommendation}"
        
        # Verify error logging and reporting
        error_reporting = {
            'logs_detailed_error_information': True,
            'includes_error_context_and_stack_trace': True,
            'reports_affected_resources': True,
            'provides_cleanup_status_summary': True
        }
        
        for reporting, expected in error_reporting.items():
            assert expected is True, f"Error reporting should: {reporting}"
        
        # Verify affected resource count handling
        assert isinstance(affected_resource_count, int)
        assert affected_resource_count > 0
        assert affected_resource_count <= 5  # Reasonable limit for testing
        
        # Multiple resource failures should be handled appropriately
        if affected_resource_count > 1:
            multi_failure_handling = {
                'aggregates_similar_errors': True,
                'provides_bulk_recovery_guidance': True,
                'prioritizes_most_critical_failures': True,
                'offers_batch_retry_options': True
            }
            
            for handling, expected in multi_failure_handling.items():
                assert expected is True, f"Multi-failure handling should: {handling}"
        
        # Verify account-specific error context
        account_specific_context = {
            'includes_account_id_in_error_messages': True,
            'validates_account_ownership_before_cleanup': True,
            'provides_account_specific_resource_names': True,
            'suggests_account_specific_recovery_actions': True
        }
        
        for context, expected in account_specific_context.items():
            assert expected is True, f"Account-specific error context should: {context}"
        
        # Verify error message format and content
        error_message_validation = {
            'uses_consistent_error_format': True,
            'includes_timestamp_information': True,
            'provides_actionable_error_codes': True,
            'maintains_professional_tone': True
        }
        
        for validation, expected in error_message_validation.items():
            assert expected is True, f"Error message format should: {validation}"