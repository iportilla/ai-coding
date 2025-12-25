"""
Unit tests for utility functions.

Tests the utility functions for AWS operations, validation, JSON handling,
and error management.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from src.utils import (
    validate_aws_account_id, validate_aws_region, parse_json_safely,
    format_json, validate_required_fields, AWSError, ValidationError
)


class TestValidationFunctions:
    """Test validation utility functions."""
    
    def test_validate_aws_account_id_valid(self):
        """Test valid AWS account ID validation."""
        assert validate_aws_account_id("123456789012") is True
        assert validate_aws_account_id("000000000000") is True
        assert validate_aws_account_id("999999999999") is True
    
    def test_validate_aws_account_id_invalid(self):
        """Test invalid AWS account ID validation."""
        assert validate_aws_account_id("") is False
        assert validate_aws_account_id("12345678901") is False  # Too short
        assert validate_aws_account_id("1234567890123") is False  # Too long
        assert validate_aws_account_id("12345678901a") is False  # Contains letter
        assert validate_aws_account_id("123-456-789-012") is False  # Contains dashes
        assert validate_aws_account_id(None) is False
    
    def test_validate_aws_region_valid(self):
        """Test valid AWS region validation."""
        assert validate_aws_region("us-east-1") is True
        assert validate_aws_region("eu-west-2") is True
        assert validate_aws_region("ap-southeast-1") is True
        assert validate_aws_region("ca-central-1") is True
    
    def test_validate_aws_region_invalid(self):
        """Test invalid AWS region validation."""
        assert validate_aws_region("") is False
        assert validate_aws_region("us-east") is False  # Missing number
        assert validate_aws_region("invalid-region") is False
        assert validate_aws_region("us_east_1") is False  # Wrong separator
        assert validate_aws_region("US-EAST-1") is False  # Wrong case
        assert validate_aws_region(None) is False


class TestJSONUtilities:
    """Test JSON handling utilities."""
    
    def test_parse_json_safely_valid(self):
        """Test parsing valid JSON."""
        json_string = '{"key": "value", "number": 42}'
        result = parse_json_safely(json_string)
        assert result == {"key": "value", "number": 42}
    
    def test_parse_json_safely_invalid(self):
        """Test parsing invalid JSON."""
        assert parse_json_safely("invalid json") is None
        assert parse_json_safely('{"incomplete": }') is None
        assert parse_json_safely("") is None
    
    def test_format_json(self):
        """Test JSON formatting."""
        data = {"b": 2, "a": 1, "c": {"nested": True}}
        formatted = format_json(data)
        
        # Should be properly formatted and sorted
        expected_lines = [
            '{',
            '  "a": 1,',
            '  "b": 2,',
            '  "c": {',
            '    "nested": true',
            '  }',
            '}'
        ]
        assert formatted == '\n'.join(expected_lines)
    
    def test_format_json_custom_indent(self):
        """Test JSON formatting with custom indentation."""
        data = {"key": "value"}
        formatted = format_json(data, indent=4)
        assert "    " in formatted  # 4-space indentation


class TestFieldValidation:
    """Test field validation utilities."""
    
    def test_validate_required_fields_all_present(self):
        """Test validation when all required fields are present."""
        data = {"name": "test", "value": 42, "enabled": True}
        required = ["name", "value", "enabled"]
        missing = validate_required_fields(data, required)
        assert missing == []
    
    def test_validate_required_fields_some_missing(self):
        """Test validation when some required fields are missing."""
        data = {"name": "test", "enabled": True}
        required = ["name", "value", "enabled"]
        missing = validate_required_fields(data, required)
        assert missing == ["value"]
    
    def test_validate_required_fields_none_values(self):
        """Test validation with None values."""
        data = {"name": "test", "value": None, "enabled": True}
        required = ["name", "value", "enabled"]
        missing = validate_required_fields(data, required)
        assert missing == ["value"]
    
    def test_validate_required_fields_empty_requirements(self):
        """Test validation with no required fields."""
        data = {"name": "test"}
        required = []
        missing = validate_required_fields(data, required)
        assert missing == []


class TestExceptions:
    """Test custom exception classes."""
    
    def test_aws_error(self):
        """Test AWSError exception."""
        with pytest.raises(AWSError):
            raise AWSError("AWS operation failed")
    
    def test_validation_error(self):
        """Test ValidationError exception."""
        with pytest.raises(ValidationError):
            raise ValidationError("Validation failed")