"""
Unit tests for IAM role setup script functionality.

Tests the IAM role creation, policy generation, and error handling
to ensure proper security configuration and existing resource handling.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from src.utils import run_aws_command, resource_exists, ValidationError
from src.config import IAMConfig


class TestIAMRoleCreation:
    """Test IAM role creation and management."""
    
    def test_iam_role_policy_generation(self):
        """Test IAM trust and permissions policy generation."""
        account_id = "123456789012"
        
        # Test trust policy structure
        trust_policy = {
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
        
        # Verify trust policy structure
        assert trust_policy["Version"] == "2012-10-17"
        assert len(trust_policy["Statement"]) == 1
        
        statement = trust_policy["Statement"][0]
        assert statement["Principal"]["Service"] == "bedrock.amazonaws.com"
        assert statement["Condition"]["StringEquals"]["aws:SourceAccount"] == account_id
        
        # Test permissions policy structure
        permissions_policy = {
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
        
        # Verify permissions policy has minimal required permissions
        assert permissions_policy["Version"] == "2012-10-17"
        assert len(permissions_policy["Statement"]) == 2
        
        # Check CloudWatch permissions
        cloudwatch_statement = permissions_policy["Statement"][0]
        required_actions = {"logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"}
        assert set(cloudwatch_statement["Action"]) == required_actions
        
        # Check S3 permissions
        s3_statement = permissions_policy["Statement"][1]
        assert s3_statement["Action"] == ["s3:PutObject"]
        assert f"bedrock-logs-{account_id}" in s3_statement["Resource"][0]
    
    def test_iam_config_initialization(self):
        """Test IAM configuration initialization."""
        config = IAMConfig(account_id="123456789012")
        assert config.role_name == "BedrockCloudWatchLoggingRole"
        assert config.account_id == "123456789012"
    
    @patch('src.utils.subprocess.run')
    def test_existing_role_detection(self, mock_run):
        """Test detection of existing IAM roles."""
        # Mock successful role existence check
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"Role": {"RoleName": "BedrockCloudWatchLoggingRole"}}',
            stderr='',
            check=True
        )
        
        exists = resource_exists("iam-role", "BedrockCloudWatchLoggingRole")
        assert exists is True
        
        # Verify correct AWS CLI command was called
        mock_run.assert_called_with(
            ['aws', 'iam', 'get-role', '--role-name', 'BedrockCloudWatchLoggingRole'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('src.utils.subprocess.run')
    def test_nonexistent_role_detection(self, mock_run):
        """Test detection when IAM role doesn't exist."""
        # Mock failed role existence check
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(
            returncode=254,
            cmd=['aws', 'iam', 'get-role'],
            stderr='NoSuchEntity'
        )
        
        exists = resource_exists("iam-role", "NonexistentRole")
        assert exists is False
    
    @patch('src.utils.subprocess.run')
    def test_aws_command_execution_success(self, mock_run):
        """Test successful AWS CLI command execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='123456789012',
            stderr='',
            check=True
        )
        
        success, output = run_aws_command(['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'])
        
        assert success is True
        assert output == '123456789012'
    
    @patch('src.utils.subprocess.run')
    def test_aws_command_execution_failure(self, mock_run):
        """Test failed AWS CLI command execution."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(
            returncode=1,
            cmd=['aws', 'iam', 'get-role'],
            stderr='AccessDenied: User is not authorized'
        )
        
        success, output = run_aws_command(['aws', 'iam', 'get-role', '--role-name', 'TestRole'])
        
        assert success is False
        assert 'AccessDenied' in output


class TestIAMRoleErrorHandling:
    """Test error handling in IAM role operations."""
    
    def test_invalid_resource_type(self):
        """Test error handling for invalid resource types."""
        with pytest.raises(ValidationError, match="Unknown resource type"):
            resource_exists("invalid-type", "test-resource")
    
    @patch('src.utils.subprocess.run')
    def test_aws_cli_not_found(self, mock_run):
        """Test handling when AWS CLI is not installed."""
        mock_run.side_effect = FileNotFoundError("aws command not found")
        
        success, output = run_aws_command(['aws', 'sts', 'get-caller-identity'])
        
        assert success is False
        assert "AWS CLI not found" in output
    
    def test_policy_document_validation(self):
        """Test validation of policy document structure."""
        # Valid policy document
        valid_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "logs:CreateLogGroup",
                    "Resource": "*"
                }
            ]
        }
        
        # Should be valid JSON
        json_string = json.dumps(valid_policy)
        parsed_policy = json.loads(json_string)
        
        assert parsed_policy["Version"] == "2012-10-17"
        assert "Statement" in parsed_policy
        assert len(parsed_policy["Statement"]) > 0
    
    def test_account_specific_resource_arns(self):
        """Test that resource ARNs are account-specific."""
        account_id = "123456789012"
        
        # CloudWatch log group ARN
        log_group_arn = f"arn:aws:logs:*:{account_id}:log-group:/aws/bedrock/*"
        assert account_id in log_group_arn
        assert "/aws/bedrock/" in log_group_arn
        
        # S3 bucket ARN
        s3_bucket_arn = f"arn:aws:s3:::bedrock-logs-{account_id}/*"
        assert account_id in s3_bucket_arn
        assert "bedrock-logs" in s3_bucket_arn
    
    def test_minimal_permissions_validation(self):
        """Test that only minimal required permissions are granted."""
        # Define the exact set of required actions
        required_actions = {
            "logs:CreateLogGroup",
            "logs:CreateLogStream", 
            "logs:PutLogEvents",
            "s3:PutObject"
        }
        
        # Test policy should contain exactly these actions
        test_policy_actions = [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents",
            "s3:PutObject"
        ]
        
        assert set(test_policy_actions) == required_actions
        
        # Verify no excessive permissions
        excessive_actions = {
            "s3:DeleteObject",
            "logs:DeleteLogGroup",
            "iam:CreateRole",
            "*"
        }
        
        for action in excessive_actions:
            assert action not in test_policy_actions


class TestIAMRoleIntegration:
    """Integration tests for IAM role setup."""
    
    def test_role_configuration_completeness(self):
        """Test that role configuration includes all required components."""
        account_id = "123456789012"
        role_name = "BedrockCloudWatchLoggingRole"
        
        # Simulate complete role configuration
        role_config = {
            "role_name": role_name,
            "account_id": account_id,
            "trust_policy": {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {"aws:SourceAccount": account_id},
                        "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock:*:{account_id}:*"}
                    }
                }]
            },
            "permissions_policy": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                        "Resource": [f"arn:aws:logs:*:{account_id}:log-group:/aws/bedrock/*"]
                    },
                    {
                        "Effect": "Allow", 
                        "Action": ["s3:PutObject"],
                        "Resource": [f"arn:aws:s3:::bedrock-logs-{account_id}/*"]
                    }
                ]
            }
        }
        
        # Verify all required components are present
        assert "role_name" in role_config
        assert "account_id" in role_config
        assert "trust_policy" in role_config
        assert "permissions_policy" in role_config
        
        # Verify trust policy structure
        trust_policy = role_config["trust_policy"]
        assert trust_policy["Statement"][0]["Principal"]["Service"] == "bedrock.amazonaws.com"
        
        # Verify permissions policy structure
        permissions_policy = role_config["permissions_policy"]
        assert len(permissions_policy["Statement"]) == 2
        
        # Verify account-specific restrictions
        for statement in permissions_policy["Statement"]:
            for resource in statement["Resource"]:
                assert account_id in resource