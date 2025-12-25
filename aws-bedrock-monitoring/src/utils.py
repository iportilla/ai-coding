"""
Shared utility functions for AWS Bedrock monitoring system.

This module provides common utilities for AWS operations, JSON handling,
error management, and resource validation across all monitoring components.
"""

import json
import subprocess
import sys
from typing import Dict, Any, List, Optional, Tuple
import re


class AWSError(Exception):
    """Custom exception for AWS-related errors."""
    pass


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def run_aws_command(command: List[str], check_output: bool = True) -> Tuple[bool, str]:
    """
    Execute AWS CLI command and return success status and output.
    
    Args:
        command: List of command parts (e.g., ['aws', 'iam', 'get-role'])
        check_output: Whether to capture and return output
        
    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        if check_output:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        else:
            subprocess.run(command, check=True)
            return True, ""
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        return False, error_msg
    except FileNotFoundError:
        return False, "AWS CLI not found. Please install and configure AWS CLI."


def validate_aws_account_id(account_id: str) -> bool:
    """
    Validate AWS account ID format.
    
    Args:
        account_id: AWS account ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not account_id:
        return False
    
    # AWS account IDs are 12-digit numbers
    pattern = r'^\d{12}$'
    return bool(re.match(pattern, account_id))


def validate_aws_region(region: str) -> bool:
    """
    Validate AWS region format.
    
    Args:
        region: AWS region to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not region:
        return False
    
    # Basic AWS region pattern (e.g., us-east-1, eu-west-2)
    pattern = r'^[a-z]{2}-[a-z]+-\d+$'
    return bool(re.match(pattern, region))


def get_aws_account_id() -> Optional[str]:
    """
    Get current AWS account ID using AWS CLI.
    
    Returns:
        Account ID if successful, None otherwise
    """
    success, output = run_aws_command(['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'])
    
    if success and validate_aws_account_id(output):
        return output
    
    return None


def get_aws_region() -> Optional[str]:
    """
    Get current AWS region from configuration.
    
    Returns:
        Region if successful, None otherwise
    """
    success, output = run_aws_command(['aws', 'configure', 'get', 'region'])
    
    if success and validate_aws_region(output):
        return output
    
    return None


def resource_exists(resource_type: str, resource_name: str, **kwargs) -> bool:
    """
    Check if an AWS resource exists.
    
    Args:
        resource_type: Type of resource (iam-role, s3-bucket, log-group, etc.)
        resource_name: Name of the resource
        **kwargs: Additional parameters for specific resource types
        
    Returns:
        True if resource exists, False otherwise
    """
    if resource_type == "iam-role":
        success, _ = run_aws_command(['aws', 'iam', 'get-role', '--role-name', resource_name])
        return success
    
    elif resource_type == "s3-bucket":
        success, _ = run_aws_command(['aws', 's3api', 'head-bucket', '--bucket', resource_name])
        return success
    
    elif resource_type == "log-group":
        success, output = run_aws_command([
            'aws', 'logs', 'describe-log-groups',
            '--log-group-name-prefix', resource_name,
            '--query', f'logGroups[?logGroupName==`{resource_name}`].logGroupName',
            '--output', 'text'
        ])
        return success and output.strip() == resource_name
    
    elif resource_type == "sns-topic":
        success, output = run_aws_command([
            'aws', 'sns', 'list-topics',
            '--query', f'Topics[?contains(TopicArn, `{resource_name}`)].TopicArn',
            '--output', 'text'
        ])
        return success and resource_name in output
    
    elif resource_type == "dashboard":
        success, output = run_aws_command([
            'aws', 'cloudwatch', 'list-dashboards',
            '--query', f'DashboardEntries[?DashboardName==`{resource_name}`].DashboardName',
            '--output', 'text'
        ])
        return success and output.strip() == resource_name
    
    else:
        raise ValidationError(f"Unknown resource type: {resource_type}")


def parse_json_safely(json_string: str) -> Optional[Dict[str, Any]]:
    """
    Parse JSON string safely with error handling.
    
    Args:
        json_string: JSON string to parse
        
    Returns:
        Parsed dictionary or None if parsing fails
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return None


def format_json(data: Dict[str, Any], indent: int = 2) -> str:
    """
    Format dictionary as JSON string with proper indentation.
    
    Args:
        data: Dictionary to format
        indent: Number of spaces for indentation
        
    Returns:
        Formatted JSON string
    """
    return json.dumps(data, indent=indent, sort_keys=True)


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """
    Validate that required fields are present in data dictionary.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        
    Returns:
        List of missing field names (empty if all present)
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    
    return missing_fields


def log_operation(operation: str, resource: str, success: bool, details: str = "") -> None:
    """
    Log operation results to stdout with consistent formatting.
    
    Args:
        operation: Operation being performed (e.g., "CREATE", "UPDATE", "DELETE")
        resource: Resource being operated on
        success: Whether operation was successful
        details: Additional details about the operation
    """
    status = "SUCCESS" if success else "FAILED"
    message = f"[{operation}] {resource}: {status}"
    
    if details:
        message += f" - {details}"
    
    print(message)
    
    if not success:
        print(f"Error details: {details}", file=sys.stderr)