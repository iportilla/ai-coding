#!/bin/bash

# AWS Bedrock Monitoring - CloudWatch Log Group Setup Script
# This script creates CloudWatch log group for Bedrock model invocations with retention policy

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
DEFAULT_LOG_GROUP="/aws/bedrock/modelinvocations"
DEFAULT_RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Function to get AWS account ID
get_account_id() {
    local account_id
    account_id=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
    
    if [[ -z "$account_id" || ! "$account_id" =~ ^[0-9]{12}$ ]]; then
        log_error "Failed to get AWS account ID. Please ensure AWS CLI is configured."
        exit 1
    fi
    
    echo "$account_id"
}

# Function to get AWS region
get_region() {
    local region
    region=$(aws configure get region 2>/dev/null)
    
    if [[ -z "$region" ]]; then
        region="us-east-1"
        log_warn "No default region configured, using us-east-1"
    fi
    
    echo "$region"
}

# Function to check if log group exists
log_group_exists() {
    local log_group_name="$1"
    local result
    result=$(aws logs describe-log-groups \
        --log-group-name-prefix "$log_group_name" \
        --query "logGroups[?logGroupName=='$log_group_name'].logGroupName" \
        --output text 2>/dev/null)
    
    [[ "$result" == "$log_group_name" ]]
}

# Function to get current retention policy
get_retention_policy() {
    local log_group_name="$1"
    aws logs describe-log-groups \
        --log-group-name-prefix "$log_group_name" \
        --query "logGroups[?logGroupName=='$log_group_name'].retentionInDays" \
        --output text 2>/dev/null || echo "null"
}

# Function to create or update CloudWatch log group
create_log_group() {
    local log_group_name="$1"
    local retention_days="$2"
    local region="$3"
    
    log_info "Setting up CloudWatch log group: $log_group_name"
    
    # Check if log group already exists
    if log_group_exists "$log_group_name"; then
        log_warn "Log group $log_group_name already exists. Validating configuration..."
        
        # Check current retention policy
        local current_retention
        current_retention=$(get_retention_policy "$log_group_name")
        
        if [[ "$current_retention" == "null" || "$current_retention" == "" ]]; then
            log_info "No retention policy set. Applying $retention_days days retention..."
            if ! aws logs put-retention-policy \
                --log-group-name "$log_group_name" \
                --retention-in-days "$retention_days" 2>/dev/null; then
                log_warn "Failed to set retention policy for log group $log_group_name"
            else
                log_info "✅ Retention policy applied successfully"
            fi
        elif [[ "$current_retention" != "$retention_days" ]]; then
            log_info "Current retention: $current_retention days. Updating to $retention_days days..."
            if ! aws logs put-retention-policy \
                --log-group-name "$log_group_name" \
                --retention-in-days "$retention_days" 2>/dev/null; then
                log_warn "Failed to update retention policy for log group $log_group_name"
            else
                log_info "✅ Retention policy updated successfully"
            fi
        else
            log_info "Log group already has correct retention policy ($retention_days days)"
        fi
    else
        # Create the log group
        log_info "Creating log group $log_group_name"
        if ! aws logs create-log-group --log-group-name "$log_group_name" 2>/dev/null; then
            log_error "Failed to create log group $log_group_name"
            return 1
        fi
        
        # Set retention policy
        log_info "Setting retention policy to $retention_days days"
        if ! aws logs put-retention-policy \
            --log-group-name "$log_group_name" \
            --retention-in-days "$retention_days" 2>/dev/null; then
            log_warn "Failed to set retention policy for log group $log_group_name"
        else
            log_info "✅ Retention policy applied successfully"
        fi
        
        log_info "Log group $log_group_name created successfully"
    fi
    
    # Add tags to the log group (with error handling)
    log_info "Adding tags to log group"
    if ! aws logs tag-log-group \
        --log-group-name "$log_group_name" \
        --tags \
        "Purpose=BedrockMonitoring" \
        "Service=Bedrock" \
        "Component=Logging" \
        "RetentionDays=$retention_days" \
        "Region=$region" 2>/dev/null; then
        log_warn "Failed to add tags to log group (may not be supported in this region)"
    else
        log_info "✅ Tags applied successfully"
    fi
    
    log_info "CloudWatch log group setup completed"
    
    # Output log group information
    echo
    echo "=== CloudWatch Log Group Configuration ==="
    echo "Log Group Name: $log_group_name"
    echo "Region: $region"
    echo "Retention Policy: $retention_days days"
    echo "Purpose: Bedrock model invocation logging"
    echo "=========================================="
    
    return 0
}

# Function to validate prerequisites
validate_prerequisites() {
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install AWS CLI first."
        exit 1
    fi
    
    # Check if AWS credentials are configured
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check CloudWatch Logs permissions
    if ! aws logs describe-log-groups --max-items 1 >/dev/null 2>&1; then
        log_error "Insufficient permissions for CloudWatch Logs. Please check IAM permissions."
        exit 1
    fi
    
    log_info "Prerequisites validated successfully"
}

# Function to validate retention days
validate_retention_days() {
    local retention_days="$1"
    
    # Valid retention values for CloudWatch Logs
    local valid_values=(1 3 5 7 14 30 60 90 120 150 180 365 400 545 731 1827 3653)
    
    for valid in "${valid_values[@]}"; do
        if [[ "$retention_days" == "$valid" ]]; then
            return 0
        fi
    done
    
    log_error "Invalid retention days: $retention_days"
    log_error "Valid values: ${valid_values[*]}"
    exit 1
}

# Main function
main() {
    log_info "Starting CloudWatch log group setup for AWS Bedrock monitoring"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Get configuration
    local account_id region log_group_name retention_days
    account_id=$(get_account_id)
    region=$(get_region)
    log_group_name="${LOG_GROUP_NAME:-$DEFAULT_LOG_GROUP}"
    retention_days="${RETENTION_DAYS:-$DEFAULT_RETENTION_DAYS}"
    
    # Validate retention days
    validate_retention_days "$retention_days"
    
    log_info "AWS Account ID: $account_id"
    log_info "AWS Region: $region"
    log_info "Target log group: $log_group_name"
    log_info "Retention policy: $retention_days days"
    
    # Create or update log group
    if ! create_log_group "$log_group_name" "$retention_days" "$region"; then
        log_error "Failed to create or configure log group. Exiting."
        exit 1
    fi
    
    log_info "CloudWatch log group setup completed successfully!"
    
    # Export log group configuration for use by other scripts
    echo "export BEDROCK_LOG_GROUP_NAME=\"$log_group_name\"" > "${SCRIPT_DIR}/.log-group-config"
    echo "export BEDROCK_LOG_RETENTION_DAYS=\"$retention_days\"" >> "${SCRIPT_DIR}/.log-group-config"
    log_info "Log group configuration saved to .log-group-config"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo
        echo "Environment Variables:"
        echo "  LOG_GROUP_NAME      CloudWatch log group name (default: /aws/bedrock/modelinvocations)"
        echo "  RETENTION_DAYS      Log retention days (default: 30)"
        echo
        echo "Valid retention days: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653"
        echo
        echo "This script creates a CloudWatch log group for AWS Bedrock with:"
        echo "  - Configurable retention policy"
        echo "  - Proper tagging for resource management"
        echo "  - Existing resource detection and updates"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac