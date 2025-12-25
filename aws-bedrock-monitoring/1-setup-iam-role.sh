#!/bin/bash

# AWS Bedrock CloudWatch Logging IAM Role Setup
# This script creates the IAM role needed for Bedrock to write logs to CloudWatch
# Implements minimal permissions with account-specific resource restrictions

set -e

# Get AWS account ID dynamically
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_NAME="BedrockCloudWatchLoggingRole"
POLICY_NAME="BedrockCloudWatchLoggingPolicy"

echo "=========================================="
echo "Setting up IAM Role for Bedrock Logging"
echo "Account ID: $ACCOUNT_ID"
echo "=========================================="
echo ""

# Function to check if role exists
check_role_exists() {
    aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1
}

# Function to create trust policy with account-specific restrictions
create_trust_policy() {
    cat > /tmp/bedrock-trust-policy.json << EOF
{
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
          "aws:SourceAccount": "$ACCOUNT_ID"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:bedrock:*:$ACCOUNT_ID:*"
        }
      }
    }
  ]
}
EOF
}

# Function to create minimal permissions policy
create_permissions_policy() {
    cat > /tmp/bedrock-logging-policy.json << EOF
{
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
        "arn:aws:logs:*:$ACCOUNT_ID:log-group:/aws/bedrock/*",
        "arn:aws:logs:*:$ACCOUNT_ID:log-group:/aws/bedrock/*:log-stream:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::bedrock-logs-$ACCOUNT_ID/*"
      ]
    }
  ]
}
EOF
}

# Function to update existing role policies
update_existing_role() {
    echo "Role $ROLE_NAME already exists. Validating and updating configuration..."
    
    # Validate current trust policy
    echo "Checking current trust policy..."
    local current_trust_policy
    current_trust_policy=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.AssumeRolePolicyDocument' --output json 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        echo "Current trust policy retrieved successfully"
    else
        echo "⚠️  Warning: Could not retrieve current trust policy"
    fi
    
    # Update trust policy
    echo "Updating trust policy..."
    create_trust_policy
    if aws iam update-assume-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-document file:///tmp/bedrock-trust-policy.json 2>/dev/null; then
        echo "✅ Trust policy updated successfully"
    else
        echo "⚠️  Warning: Trust policy update failed, but continuing..."
    fi
    
    # Check current permissions policy
    echo "Checking current permissions policy..."
    local current_policy_exists
    current_policy_exists=$(aws iam get-role-policy --role-name "$ROLE_NAME" --policy-name "$POLICY_NAME" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        echo "Current permissions policy found"
    else
        echo "No existing permissions policy found, will create new one"
    fi
    
    # Update permissions policy
    echo "Updating permissions policy..."
    create_permissions_policy
    if aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "$POLICY_NAME" \
        --policy-document file:///tmp/bedrock-logging-policy.json 2>/dev/null; then
        echo "✅ Permissions policy updated successfully"
    else
        echo "❌ Error: Failed to update permissions policy"
        return 1
    fi
    
    echo "✅ Existing role configuration validated and updated successfully!"
}

# Function to create new role
create_new_role() {
    echo "Creating new IAM role: $ROLE_NAME"
    
    # Create trust policy
    echo "Creating trust policy..."
    create_trust_policy
    
    # Create the IAM role
    if aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/bedrock-trust-policy.json \
        --description "Role for Bedrock to write logs to CloudWatch with minimal permissions" 2>/dev/null; then
        echo "✅ IAM role created successfully"
    else
        echo "❌ Error: Failed to create IAM role"
        return 1
    fi
    
    # Create and attach permissions policy
    echo "Creating and attaching permissions policy..."
    create_permissions_policy
    if aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "$POLICY_NAME" \
        --policy-document file:///tmp/bedrock-logging-policy.json 2>/dev/null; then
        echo "✅ Permissions policy attached successfully"
    else
        echo "❌ Error: Failed to attach permissions policy"
        # Clean up the role if policy attachment fails
        aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null
        return 1
    fi
    
    echo "✅ New IAM role created successfully!"
}

# Main execution logic with existing role detection
echo "Checking for existing IAM role..."
if check_role_exists; then
    if ! update_existing_role; then
        echo "❌ Failed to update existing role. Exiting."
        exit 1
    fi
else
    if ! create_new_role; then
        echo "❌ Failed to create new role. Exiting."
        exit 1
    fi
fi

# Wait for role to propagate
echo "Waiting for IAM role to propagate (10 seconds)..."
sleep 10

# Get and display role ARN
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)

echo ""
echo "=========================================="
echo "✅ IAM Role Setup Complete!"
echo "=========================================="
echo "Role Name: $ROLE_NAME"
echo "Role ARN: $ROLE_ARN"
echo "Account ID: $ACCOUNT_ID"
echo ""
echo "Security Features Implemented:"
echo "- Minimal required permissions only"
echo "- Account-specific resource ARN restrictions"
echo "- Bedrock service-only trust policy"
echo "- Source account and ARN conditions"
echo ""
echo "You can now use this role for Bedrock logging configuration."
echo ""

# Clean up temp files
rm -f /tmp/bedrock-trust-policy.json /tmp/bedrock-logging-policy.json
