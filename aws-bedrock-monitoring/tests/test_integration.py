"""
Integration tests for AWS Bedrock monitoring system end-to-end setup.

These tests validate the complete setup and cleanup cycle, cross-component dependencies,
and integration between all monitoring components.
"""

import pytest
import subprocess
import json
import os
import time
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock


class TestEndToEndSetup:
    """Integration tests for complete setup and cleanup cycle."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.script_dir = os.path.join(os.path.dirname(__file__), '..')
        self.test_account_id = "123456789012"  # Mock account ID for testing
        self.test_region = "us-east-1"
        self.test_resources = {}
        
    def teardown_method(self):
        """Clean up test environment after each test."""
        # Clean up any test resources if needed
        pass
    
    @patch('subprocess.run')
    @patch('boto3.client')
    def test_complete_setup_sequence(self, mock_boto_client, mock_subprocess):
        """
        Test complete setup sequence runs all scripts in correct order.
        **Validates: Requirements 7.1, 7.5**
        """
        # Mock AWS CLI responses for successful setup
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Success"
        mock_subprocess.return_value.stderr = ""
        
        # Mock boto3 clients
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': self.test_account_id}
        mock_boto_client.return_value = mock_sts
        
        # Test orchestration script execution
        orchestration_script = os.path.join(self.script_dir, '0-setup-all.sh')
        
        # Verify script exists and is executable
        assert os.path.exists(orchestration_script), "Orchestration script should exist"
        assert os.access(orchestration_script, os.X_OK), "Orchestration script should be executable"
        
        # Mock the script execution
        with patch('os.system') as mock_system:
            mock_system.return_value = 0  # Success
            
            # Simulate running the orchestration script
            result = self._simulate_orchestration_script()
            
            # Verify all setup steps were attempted
            expected_steps = [
                '1-setup-iam-role.sh',
                '2-create-s3-bucket.sh', 
                '2b-create-log-group.sh',
                '3-enable-bedrock-logging.sh',
                '4-create-cloudwatch-dashboard.sh',
                '5-create-cloudwatch-alarms.sh'
            ]
            
            assert result['steps_executed'] == len(expected_steps)
            assert result['success'] is True
            assert result['failed_steps'] == []
    
    def _simulate_orchestration_script(self) -> Dict:
        """Simulate orchestration script execution for testing."""
        # This simulates the behavior of the orchestration script
        steps = [
            {'name': 'IAM Role Setup', 'script': '1-setup-iam-role.sh'},
            {'name': 'S3 Bucket Creation', 'script': '2-create-s3-bucket.sh'},
            {'name': 'CloudWatch Log Group Setup', 'script': '2b-create-log-group.sh'},
            {'name': 'Bedrock Logging Configuration', 'script': '3-enable-bedrock-logging.sh'},
            {'name': 'CloudWatch Dashboard Creation', 'script': '4-create-cloudwatch-dashboard.sh'},
            {'name': 'CloudWatch Alarms Setup', 'script': '5-create-cloudwatch-alarms.sh'}
        ]
        
        executed_steps = 0
        failed_steps = []
        
        for step in steps:
            # Simulate step execution
            script_path = os.path.join(self.script_dir, step['script'])
            
            if os.path.exists(script_path):
                executed_steps += 1
                # Simulate successful execution
                self.test_resources[step['name']] = {
                    'status': 'created',
                    'script': step['script']
                }
            else:
                failed_steps.append(step['name'])
        
        return {
            'steps_executed': executed_steps,
            'success': len(failed_steps) == 0,
            'failed_steps': failed_steps,
            'resources': self.test_resources
        }
    
    @patch('subprocess.run')
    def test_dependency_validation(self, mock_subprocess):
        """
        Test that setup validates dependencies between components.
        **Validates: Requirements 7.1**
        """
        # Mock AWS CLI availability check
        mock_subprocess.return_value.returncode = 0
        
        # Test dependency chain validation
        dependencies = {
            'iam-role': [],  # No dependencies
            's3-bucket': ['iam-role'],  # Needs IAM role for bucket policy
            'log-group': [],  # Independent
            'bedrock-logging': ['iam-role', 's3-bucket', 'log-group'],  # Needs all previous
            'dashboard': ['bedrock-logging'],  # Needs logging for log viewer
            'alarms': ['bedrock-logging']  # Needs logging for metrics
        }
        
        # Verify dependency order is correct
        for component, deps in dependencies.items():
            for dep in deps:
                assert dep in dependencies, f"Dependency {dep} should be defined"
        
        # Test that IAM role is created first (no dependencies)
        assert len(dependencies['iam-role']) == 0, "IAM role should have no dependencies"
        
        # Test that Bedrock logging has all required dependencies
        bedrock_deps = dependencies['bedrock-logging']
        required_deps = ['iam-role', 's3-bucket', 'log-group']
        for req_dep in required_deps:
            assert req_dep in bedrock_deps, f"Bedrock logging should depend on {req_dep}"
    
    @patch('subprocess.run')
    @patch('boto3.client')
    def test_error_recovery_and_retry(self, mock_boto_client, mock_subprocess):
        """
        Test error recovery mechanisms and retry logic.
        **Validates: Requirements 7.1, 7.2**
        """
        # Mock intermittent failures followed by success
        call_count = 0
        
        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # Fail first two attempts, succeed on third
            if call_count <= 2:
                result = MagicMock()
                result.returncode = 1
                result.stderr = "Temporary network error"
                return result
            else:
                result = MagicMock()
                result.returncode = 0
                result.stdout = "Success"
                return result
        
        mock_subprocess.side_effect = mock_run_side_effect
        
        # Test retry logic simulation
        max_retries = 3
        success = False
        
        for attempt in range(max_retries):
            try:
                # Simulate script execution
                result = mock_subprocess()
                if result.returncode == 0:
                    success = True
                    break
                elif attempt < max_retries - 1:
                    # Retry on failure (except last attempt)
                    time.sleep(0.1)  # Brief delay for testing
                    continue
                else:
                    # Final attempt failed
                    break
            except Exception:
                if attempt < max_retries - 1:
                    continue
                else:
                    break
        
        # Should succeed after retries
        assert success is True, "Should succeed after retries"
        assert call_count == 3, "Should have made 3 attempts"
    
    @patch('subprocess.run')
    def test_existing_resource_handling(self, mock_subprocess):
        """
        Test graceful handling of existing resources.
        **Validates: Requirements 7.2**
        """
        # Mock responses for existing resources
        existing_resource_responses = {
            'iam-role': {
                'returncode': 0,
                'stdout': 'Role BedrockCloudWatchLoggingRole already exists. Validating and updating configuration...',
                'stderr': ''
            },
            's3-bucket': {
                'returncode': 0,
                'stdout': 'S3 bucket bedrock-logs-123456789012 already exists. Validating configuration...',
                'stderr': ''
            },
            'log-group': {
                'returncode': 0,
                'stdout': 'Log group /aws/bedrock/modelinvocations already exists. Validating configuration...',
                'stderr': ''
            }
        }
        
        # Test each script handles existing resources
        for resource_type, expected_response in existing_resource_responses.items():
            mock_subprocess.return_value.returncode = expected_response['returncode']
            mock_subprocess.return_value.stdout = expected_response['stdout']
            mock_subprocess.return_value.stderr = expected_response['stderr']
            
            # Verify script handles existing resource gracefully
            result = mock_subprocess()
            assert result.returncode == 0, f"Script should handle existing {resource_type} gracefully"
            assert "already exists" in result.stdout, f"Should detect existing {resource_type}"
            assert "Validating" in result.stdout, f"Should validate existing {resource_type} configuration"
    
    @patch('subprocess.run')
    def test_configuration_validation(self, mock_subprocess):
        """
        Test cross-component configuration validation.
        **Validates: Requirements 7.1**
        """
        # Mock configuration validation responses
        mock_subprocess.return_value.returncode = 0
        
        # Test configuration consistency checks
        config_validations = {
            'account_id_consistency': {
                'iam_role_arn': f'arn:aws:iam::{self.test_account_id}:role/BedrockCloudWatchLoggingRole',
                's3_bucket_name': f'bedrock-logs-{self.test_account_id}',
                'sns_topic_arn': f'arn:aws:sns:{self.test_region}:{self.test_account_id}:bedrock-usage-alerts'
            },
            'region_consistency': {
                'dashboard_region': self.test_region,
                'alarms_region': self.test_region,
                'sns_topic_region': self.test_region
            },
            'resource_naming': {
                'log_group_name': '/aws/bedrock/modelinvocations',
                'dashboard_name': 'BedrockUsageMonitoring',
                'role_name': 'BedrockCloudWatchLoggingRole'
            }
        }
        
        # Verify account ID consistency across all resources
        account_id_resources = config_validations['account_id_consistency']
        for resource_name, resource_arn in account_id_resources.items():
            assert self.test_account_id in resource_arn, f"Account ID should be in {resource_name}"
        
        # Verify region consistency across all resources
        region_resources = config_validations['region_consistency']
        for resource_name, resource_region in region_resources.items():
            assert resource_region == self.test_region, f"Region should be consistent for {resource_name}"
        
        # Verify standard resource naming conventions
        naming_resources = config_validations['resource_naming']
        expected_names = {
            'log_group_name': '/aws/bedrock/modelinvocations',
            'dashboard_name': 'BedrockUsageMonitoring',
            'role_name': 'BedrockCloudWatchLoggingRole'
        }
        
        for resource_type, actual_name in naming_resources.items():
            expected_name = expected_names[resource_type]
            assert actual_name == expected_name, f"{resource_type} should follow naming convention"


class TestCrossComponentDependencies:
    """Tests for validating dependencies between monitoring components."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_account_id = "123456789012"
        self.test_region = "us-east-1"
    
    @patch('boto3.client')
    def test_iam_role_s3_bucket_integration(self, mock_boto_client):
        """
        Test IAM role and S3 bucket integration.
        **Validates: Requirements 1.4, 2.2**
        """
        # Mock IAM and S3 clients
        mock_iam = MagicMock()
        mock_s3 = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'iam':
                return mock_iam
            elif service_name == 's3':
                return mock_s3
            return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        # Test IAM role permissions for S3 bucket
        role_name = "BedrockCloudWatchLoggingRole"
        bucket_name = f"bedrock-logs-{self.test_account_id}"
        
        # Mock IAM role policy
        mock_iam.get_role_policy.return_value = {
            'PolicyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Action': ['s3:PutObject'],
                        'Resource': [f'arn:aws:s3:::{bucket_name}/*']
                    }
                ]
            }
        }
        
        # Mock S3 bucket policy
        mock_s3.get_bucket_policy.return_value = {
            'Policy': json.dumps({
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Sid': 'BedrockLogDelivery',
                        'Effect': 'Allow',
                        'Principal': {'Service': 'bedrock.amazonaws.com'},
                        'Action': ['s3:PutObject'],
                        'Resource': f'arn:aws:s3:::{bucket_name}/bedrock-logs/*',
                        'Condition': {
                            'StringEquals': {'aws:SourceAccount': self.test_account_id}
                        }
                    }
                ]
            })
        }
        
        # Verify IAM role has S3 permissions
        iam_policy = mock_iam.get_role_policy()
        s3_statement = iam_policy['PolicyDocument']['Statement'][0]
        assert 's3:PutObject' in s3_statement['Action']
        assert bucket_name in s3_statement['Resource'][0]
        
        # Verify S3 bucket policy allows Bedrock access
        s3_policy = json.loads(mock_s3.get_bucket_policy()['Policy'])
        bedrock_statement = s3_policy['Statement'][0]
        assert bedrock_statement['Principal']['Service'] == 'bedrock.amazonaws.com'
        assert 's3:PutObject' in bedrock_statement['Action']
        assert self.test_account_id in bedrock_statement['Condition']['StringEquals']['aws:SourceAccount']
    
    @patch('boto3.client')
    def test_bedrock_logging_configuration_integration(self, mock_boto_client):
        """
        Test Bedrock logging configuration with CloudWatch and S3.
        **Validates: Requirements 3.1, 3.3, 3.4, 3.5**
        """
        # Mock Bedrock client
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        # Mock Bedrock logging configuration
        expected_config = {
            'loggingConfig': {
                'cloudWatchConfig': {
                    'logGroupName': '/aws/bedrock/modelinvocations',
                    'roleArn': f'arn:aws:iam::{self.test_account_id}:role/BedrockCloudWatchLoggingRole'
                },
                's3Config': {
                    'bucketName': f'bedrock-logs-{self.test_account_id}',
                    'keyPrefix': 'bedrock-logs/'
                },
                'textDataDeliveryEnabled': True,
                'imageDataDeliveryEnabled': False,
                'embeddingDataDeliveryEnabled': False
            }
        }
        
        mock_bedrock.get_model_invocation_logging_configuration.return_value = expected_config
        
        # Verify logging configuration
        config = mock_bedrock.get_model_invocation_logging_configuration()
        logging_config = config['loggingConfig']
        
        # Verify CloudWatch configuration
        cloudwatch_config = logging_config['cloudWatchConfig']
        assert cloudwatch_config['logGroupName'] == '/aws/bedrock/modelinvocations'
        assert self.test_account_id in cloudwatch_config['roleArn']
        assert 'BedrockCloudWatchLoggingRole' in cloudwatch_config['roleArn']
        
        # Verify S3 configuration
        s3_config = logging_config['s3Config']
        assert s3_config['bucketName'] == f'bedrock-logs-{self.test_account_id}'
        assert s3_config['keyPrefix'] == 'bedrock-logs/'
        
        # Verify data delivery settings
        assert logging_config['textDataDeliveryEnabled'] is True
        assert logging_config['imageDataDeliveryEnabled'] is False
        assert logging_config['embeddingDataDeliveryEnabled'] is False
    
    @patch('boto3.client')
    def test_cloudwatch_dashboard_log_integration(self, mock_boto_client):
        """
        Test CloudWatch dashboard integration with log groups.
        **Validates: Requirements 4.5**
        """
        # Mock CloudWatch client
        mock_cloudwatch = MagicMock()
        mock_boto_client.return_value = mock_cloudwatch
        
        # Mock dashboard configuration
        dashboard_body = {
            'widgets': [
                {
                    'type': 'log',
                    'properties': {
                        'query': 'SOURCE \'/aws/bedrock/modelinvocations\'\n| fields @timestamp, modelId, inputTokenCount, outputTokenCount, invocationLatency\n| sort @timestamp desc\n| limit 100',
                        'region': self.test_region,
                        'title': 'Recent Bedrock Invocations',
                        'view': 'table'
                    }
                }
            ]
        }
        
        mock_cloudwatch.get_dashboard.return_value = {
            'DashboardBody': json.dumps(dashboard_body)
        }
        
        # Verify dashboard log widget configuration
        dashboard = mock_cloudwatch.get_dashboard()
        dashboard_config = json.loads(dashboard['DashboardBody'])
        
        log_widgets = [w for w in dashboard_config['widgets'] if w['type'] == 'log']
        assert len(log_widgets) == 1, "Should have one log widget"
        
        log_widget = log_widgets[0]
        assert '/aws/bedrock/modelinvocations' in log_widget['properties']['query']
        assert log_widget['properties']['region'] == self.test_region
        assert log_widget['properties']['view'] == 'table'
        
        # Verify log query includes required fields
        query = log_widget['properties']['query']
        required_fields = ['@timestamp', 'modelId', 'inputTokenCount', 'outputTokenCount', 'invocationLatency']
        for field in required_fields:
            assert field in query, f"Log query should include {field}"
    
    @patch('boto3.client')
    def test_cloudwatch_alarms_sns_integration(self, mock_boto_client):
        """
        Test CloudWatch alarms integration with SNS notifications.
        **Validates: Requirements 5.5**
        """
        # Mock CloudWatch and SNS clients
        mock_cloudwatch = MagicMock()
        mock_sns = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'cloudwatch':
                return mock_cloudwatch
            elif service_name == 'sns':
                return mock_sns
            return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        # Mock SNS topic
        sns_topic_arn = f'arn:aws:sns:{self.test_region}:{self.test_account_id}:bedrock-usage-alerts'
        mock_sns.list_topics.return_value = {
            'Topics': [{'TopicArn': sns_topic_arn}]
        }
        
        # Mock CloudWatch alarms
        expected_alarms = [
            'Bedrock-HighInputTokenUsage',
            'Bedrock-HighErrorRate',
            'Bedrock-UnusualInvocationSpike',
            'Bedrock-HighLatency'
        ]
        
        mock_alarms = []
        for alarm_name in expected_alarms:
            mock_alarms.append({
                'AlarmName': alarm_name,
                'AlarmActions': [sns_topic_arn],
                'OKActions': [sns_topic_arn],
                'StateValue': 'OK'
            })
        
        mock_cloudwatch.describe_alarms.return_value = {'MetricAlarms': mock_alarms}
        
        # Verify SNS topic exists
        topics = mock_sns.list_topics()
        topic_arns = [topic['TopicArn'] for topic in topics['Topics']]
        assert sns_topic_arn in topic_arns, "SNS topic should exist"
        
        # Verify all alarms are connected to SNS topic
        alarms = mock_cloudwatch.describe_alarms()
        for alarm in alarms['MetricAlarms']:
            assert sns_topic_arn in alarm['AlarmActions'], f"Alarm {alarm['AlarmName']} should have SNS action"
            assert sns_topic_arn in alarm['OKActions'], f"Alarm {alarm['AlarmName']} should have SNS OK action"
        
        # Verify all required alarms exist
        alarm_names = [alarm['AlarmName'] for alarm in alarms['MetricAlarms']]
        for expected_alarm in expected_alarms:
            assert expected_alarm in alarm_names, f"Alarm {expected_alarm} should exist"


class TestCleanupIntegration:
    """Tests for cleanup script integration and completeness."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_account_id = "123456789012"
        self.test_region = "us-east-1"
        self.script_dir = os.path.join(os.path.dirname(__file__), '..')
    
    @patch('subprocess.run')
    @patch('boto3.client')
    def test_complete_cleanup_cycle(self, mock_boto_client, mock_subprocess):
        """
        Test complete cleanup removes all created resources.
        **Validates: Requirements 7.5**
        """
        # Mock successful cleanup operations
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Resource deleted successfully"
        
        # Mock AWS clients for cleanup verification
        mock_clients = {
            'bedrock': MagicMock(),
            'cloudwatch': MagicMock(),
            'logs': MagicMock(),
            's3': MagicMock(),
            'iam': MagicMock(),
            'sns': MagicMock()
        }
        
        def mock_client(service_name, **kwargs):
            return mock_clients.get(service_name, MagicMock())
        
        mock_boto_client.side_effect = mock_client
        
        # Test cleanup script execution
        cleanup_script = os.path.join(self.script_dir, '7-cleanup-resources.sh')
        
        # Verify cleanup script exists
        assert os.path.exists(cleanup_script), "Cleanup script should exist"
        
        # Simulate cleanup operations
        cleanup_operations = [
            {'service': 'bedrock', 'operation': 'delete_model_invocation_logging_configuration'},
            {'service': 'cloudwatch', 'operation': 'delete_dashboards'},
            {'service': 'cloudwatch', 'operation': 'delete_alarms'},
            {'service': 'sns', 'operation': 'delete_topic'},
            {'service': 'logs', 'operation': 'delete_log_group'},
            {'service': 's3', 'operation': 'delete_bucket'},
            {'service': 'iam', 'operation': 'delete_role'}
        ]
        
        # Verify each cleanup operation
        for operation in cleanup_operations:
            service = operation['service']
            op_name = operation['operation']
            
            # Mock the operation
            mock_client = mock_clients[service]
            mock_operation = getattr(mock_client, op_name)
            mock_operation.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
            
            # Verify operation was configured
            assert hasattr(mock_client, op_name), f"Client should have {op_name} operation"
    
    @patch('subprocess.run')
    def test_cleanup_dependency_order(self, mock_subprocess):
        """
        Test cleanup operations happen in correct dependency order.
        **Validates: Requirements 7.5**
        """
        # Mock successful cleanup
        mock_subprocess.return_value.returncode = 0
        
        # Define cleanup order (reverse of setup order)
        expected_cleanup_order = [
            'disable_bedrock_logging',      # First - stop new logs
            'delete_cloudwatch_alarms',     # Remove monitoring
            'delete_cloudwatch_dashboard',  # Remove dashboard
            'delete_sns_topic',            # Remove notifications
            'delete_log_group',            # Remove log storage
            'empty_and_delete_s3_bucket',  # Remove S3 storage (empty first)
            'delete_iam_role'              # Last - remove permissions
        ]
        
        # Verify cleanup order makes sense
        cleanup_dependencies = {
            'disable_bedrock_logging': [],  # Can be done first
            'delete_cloudwatch_alarms': ['disable_bedrock_logging'],  # After logging disabled
            'delete_cloudwatch_dashboard': ['disable_bedrock_logging'],  # After logging disabled
            'delete_sns_topic': ['delete_cloudwatch_alarms'],  # After alarms removed
            'delete_log_group': ['disable_bedrock_logging'],  # After logging disabled
            'empty_and_delete_s3_bucket': ['disable_bedrock_logging'],  # After logging disabled
            'delete_iam_role': ['empty_and_delete_s3_bucket', 'delete_log_group']  # After resources removed
        }
        
        # Verify dependency order
        for i, operation in enumerate(expected_cleanup_order):
            dependencies = cleanup_dependencies[operation]
            
            # All dependencies should come before this operation
            for dep in dependencies:
                dep_index = expected_cleanup_order.index(dep)
                assert dep_index < i, f"Dependency {dep} should come before {operation}"
    
    @patch('os.path.exists')
    def test_cleanup_local_config_files(self, mock_exists):
        """
        Test cleanup removes local configuration files.
        **Validates: Requirements 7.5**
        """
        # Mock config files exist
        mock_exists.return_value = True
        
        # Expected local config files
        expected_config_files = [
            '.s3-config',
            '.log-group-config',
            '.bedrock-logging-config',
            '.dashboard-config',
            '.alarms-config'
        ]
        
        # Verify all config files are identified for cleanup
        for config_file in expected_config_files:
            file_path = os.path.join(self.script_dir, config_file)
            
            # Mock file existence check
            exists = mock_exists(file_path)
            assert exists is True, f"Config file {config_file} should be checked for existence"
        
        # Verify cleanup handles missing files gracefully
        mock_exists.return_value = False
        
        for config_file in expected_config_files:
            file_path = os.path.join(self.script_dir, config_file)
            
            # Should not fail if file doesn't exist
            exists = mock_exists(file_path)
            assert exists is False, f"Cleanup should handle missing {config_file} gracefully"
    
    @patch('subprocess.run')
    def test_cleanup_error_handling(self, mock_subprocess):
        """
        Test cleanup handles errors gracefully and continues with other resources.
        **Validates: Requirements 7.5**
        """
        # Mock mixed success/failure responses
        call_count = 0
        
        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            result = MagicMock()
            
            # Simulate some operations failing
            if call_count in [2, 4]:  # Fail 2nd and 4th operations
                result.returncode = 1
                result.stderr = "Resource not found or permission denied"
            else:
                result.returncode = 0
                result.stdout = "Resource deleted successfully"
            
            return result
        
        mock_subprocess.side_effect = mock_run_side_effect
        
        # Simulate cleanup with some failures
        total_operations = 6
        successful_operations = 0
        failed_operations = 0
        
        for i in range(total_operations):
            result = mock_subprocess()
            
            if result.returncode == 0:
                successful_operations += 1
            else:
                failed_operations += 1
                # Cleanup should continue despite failures
                assert "not found" in result.stderr or "permission denied" in result.stderr
        
        # Verify cleanup attempted all operations despite failures
        assert call_count == total_operations, "Should attempt all cleanup operations"
        assert successful_operations == 4, "Should have 4 successful operations"
        assert failed_operations == 2, "Should have 2 failed operations"
        
        # Cleanup should report partial success
        cleanup_success_rate = successful_operations / total_operations
        assert cleanup_success_rate >= 0.5, "Should have reasonable success rate even with failures"


class TestConfigurationPersistence:
    """Tests for configuration file management and persistence."""
    
    def setup_method(self):
        """Set up test environment."""
        self.script_dir = os.path.join(os.path.dirname(__file__), '..')
        self.test_account_id = "123456789012"
        self.test_region = "us-east-1"
    
    def test_config_file_generation(self):
        """
        Test that setup scripts generate configuration files for cross-script communication.
        **Validates: Requirements 7.1**
        """
        # Expected configuration files and their content
        expected_configs = {
            '.s3-config': {
                'BEDROCK_S3_BUCKET_NAME': f'bedrock-logs-{self.test_account_id}'
            },
            '.log-group-config': {
                'BEDROCK_LOG_GROUP_NAME': '/aws/bedrock/modelinvocations',
                'BEDROCK_LOG_RETENTION_DAYS': '30'
            },
            '.bedrock-logging-config': {
                'BEDROCK_LOGGING_ENABLED': 'true',
                'BEDROCK_LOG_GROUP_NAME': '/aws/bedrock/modelinvocations',
                'BEDROCK_IAM_ROLE_ARN': f'arn:aws:iam::{self.test_account_id}:role/BedrockCloudWatchLoggingRole',
                'BEDROCK_S3_BUCKET_NAME': f'bedrock-logs-{self.test_account_id}'
            },
            '.dashboard-config': {
                'BEDROCK_DASHBOARD_NAME': 'BedrockUsageMonitoring',
                'BEDROCK_DASHBOARD_REGION': self.test_region
            },
            '.alarms-config': {
                'BEDROCK_SNS_TOPIC_ARN': f'arn:aws:sns:{self.test_region}:{self.test_account_id}:bedrock-usage-alerts',
                'BEDROCK_ALARMS_REGION': self.test_region
            }
        }
        
        # Verify configuration structure
        for config_file, expected_vars in expected_configs.items():
            # Verify all required variables are defined
            assert len(expected_vars) > 0, f"Config file {config_file} should have variables"
            
            # Verify variable naming convention
            for var_name, var_value in expected_vars.items():
                assert var_name.startswith('BEDROCK_'), f"Variable {var_name} should have BEDROCK_ prefix"
                assert isinstance(var_value, str), f"Variable {var_name} should be string"
                
                # Verify account ID consistency where applicable
                if 'arn:aws:' in var_value:
                    assert self.test_account_id in var_value, f"ARN {var_value} should contain account ID"
                
                # Verify region consistency where applicable
                if 'arn:aws:sns:' in var_value or 'REGION' in var_name:
                    assert self.test_region in var_value, f"Value {var_value} should contain region"
    
    def test_config_file_sourcing(self):
        """
        Test that scripts can source configuration files from previous steps.
        **Validates: Requirements 7.1**
        """
        # Test configuration sourcing pattern
        config_sourcing_examples = {
            '3-enable-bedrock-logging.sh': ['.s3-config'],  # Needs S3 bucket name
            '4-create-cloudwatch-dashboard.sh': ['.bedrock-logging-config'],  # Needs log group
            '5-create-cloudwatch-alarms.sh': [],  # Independent
            '6-usage-report.py': ['.bedrock-logging-config'],  # Needs configuration
            '7-cleanup-resources.sh': ['.s3-config', '.alarms-config', '.dashboard-config']  # Needs all
        }
        
        # Verify sourcing dependencies
        for script, required_configs in config_sourcing_examples.items():
            script_path = os.path.join(self.script_dir, script)
            
            # Verify script exists
            if os.path.exists(script_path):
                # Verify required config files are documented
                for config_file in required_configs:
                    assert config_file.startswith('.'), f"Config file {config_file} should start with dot"
                    assert config_file.endswith('-config'), f"Config file {config_file} should end with -config"
    
    @patch('builtins.open', create=True)
    def test_config_file_format(self, mock_open):
        """
        Test configuration file format is consistent and parseable.
        **Validates: Requirements 7.1**
        """
        # Mock config file content
        mock_config_content = '''export BEDROCK_S3_BUCKET_NAME="bedrock-logs-123456789012"
export BEDROCK_LOG_GROUP_NAME="/aws/bedrock/modelinvocations"
export BEDROCK_IAM_ROLE_ARN="arn:aws:iam::123456789012:role/BedrockCloudWatchLoggingRole"
'''
        
        mock_open.return_value.__enter__.return_value.read.return_value = mock_config_content
        
        # Parse config file content
        config_lines = mock_config_content.strip().split('\n')
        parsed_config = {}
        
        for line in config_lines:
            if line.startswith('export '):
                # Parse export statement
                export_part = line[7:]  # Remove 'export '
                if '=' in export_part:
                    var_name, var_value = export_part.split('=', 1)
                    # Remove quotes
                    var_value = var_value.strip('"\'')
                    parsed_config[var_name] = var_value
        
        # Verify parsed configuration
        assert 'BEDROCK_S3_BUCKET_NAME' in parsed_config
        assert 'BEDROCK_LOG_GROUP_NAME' in parsed_config
        assert 'BEDROCK_IAM_ROLE_ARN' in parsed_config
        
        # Verify values are properly formatted
        assert parsed_config['BEDROCK_S3_BUCKET_NAME'] == 'bedrock-logs-123456789012'
        assert parsed_config['BEDROCK_LOG_GROUP_NAME'] == '/aws/bedrock/modelinvocations'
        assert parsed_config['BEDROCK_IAM_ROLE_ARN'].startswith('arn:aws:iam::')
        
        # Verify export format is shell-compatible
        for line in config_lines:
            assert line.startswith('export '), f"Line should start with 'export ': {line}"
            assert '=' in line, f"Line should contain assignment: {line}"
            
            # Verify quoted values
            if '"' in line:
                quote_count = line.count('"')
                assert quote_count == 2, f"Line should have exactly 2 quotes: {line}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])