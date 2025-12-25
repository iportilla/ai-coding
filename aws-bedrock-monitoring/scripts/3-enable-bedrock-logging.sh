#!/bin/bash

# AWS Bedrock Monitoring - Bedrock Logging Configuration Script
# This script enables Bedrock model invocation logging with dual destination configuration
# Configures text data delivery to both CloudWatch and S3

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
DEFAULT_LOG_GROUP="/aws/bedrock/modelinvocations"
DEFAULT_IAM_ROLE_NAME="BedrockCloudWatchLoggingRole"
DEFAULT_BUCKET_PREFIX="bedrock-logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
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

# Function to get IAM role ARN
get_iam_role_arn() {
    local role_name="$1"
    local role_arn
    
    role_arn=$(aws iam get-role --role-name "$role_name" --query 'Role.Arn' --output text 2>/dev/null)
    
    if [[ -z "$role_arn" || "$role_arn" == "None" ]]; then
        log_error "IAM role $role_name not found. Please run 1-setup-iam-role.sh first."
        exit 1
    fi
    
    echo "$role_arn"
}

# Function to generate S3 bucket name
generate_s3_bucket_name() {
    local account_id="$1"
    local bucket_prefix="${BUCKET_PREFIX:-$DEFAULT_BUCKET_PREFIX}"
    echo "${bucket_prefix}-${account_id}"
}

# Function to verify S3 bucket exists
verify_s3_bucket() {
    local bucket_name="$1"
    
    if ! aws s3api head-bucket --bucket "$bucket_name" >/dev/null 2>&1; then
        log_error "S3 bucket $bucket_name not found or not accessible."
        log_error "Please run 2-create-s3-bucket.sh first or check bucket permissions."
        return 1
    fi
    
    log_info "S3 bucket $bucket_name verified"
    return 0
}

# Function to verify CloudWatch log group exists
verify_log_group() {
    local log_group_name="$1"
    local result
    
    result=$(aws logs describe-log-groups \
        --log-group-name-prefix "$log_group_name" \
        --query "logGroups[?logGroupName=='$log_group_name'].logGroupName" \
        --output text 2>/dev/null)
    
    if [[ "$result" != "$log_group_name" ]]; then
        log_error "CloudWatch log group $log_group_name not found."
        log_error "Please run 2b-create-log-group.sh first."
        return 1
    fi
    
    log_info "CloudWatch log group $log_group_name verified"
    return 0
}

# Function to check current Bedrock logging configuration
get_current_logging_config() {
    local config
    config=$(aws bedrock get-model-invocation-logging-configuration 2>/dev/null || echo "{}")
    echo "$config"
}

# Function to check if logging is already enabled
is_logging_enabled() {
    local config="$1"
    local logging_config
    
    logging_config=$(echo "$config" | jq -r '.loggingConfig // empty' 2>/dev/null)
    
    if [[ -n "$logging_config" && "$logging_config" != "null" ]]; then
        return 0  # Logging is enabled
    else
        return 1  # Logging is not enabled
    fi
}

# Function to create logging configuration JSON
create_logging_config() {
    local log_group_name="$1"
    local role_arn="$2"
    local s3_bucket_name="$3"
    
    cat <<EOF
{
    "loggingConfig": {
        "cloudWatchConfig": {
            "logGroupName": "$log_group_name",
            "roleArn": "$role_arn"
        },
        "s3Config": {
            "bucketName": "$s3_bucket_name",
            "keyPrefix": "bedrock-logs/"
        },
        "textDataDeliveryEnabled": true,
        "imageDataDeliveryEnabled": false,
        "embeddingDataDeliveryEnabled": false
    }
}
EOF
}

# Function to enable Bedrock logging
enable_bedrock_logging() {
    local log_group_name="$1"
    local role_arn="$2"
    local s3_bucket_name="$3"
    
    log_info "Enabling Bedrock model invocation logging..."
    
    # Check current configuration
    local current_config
    current_config=$(get_current_logging_config)
    
    if is_logging_enabled "$current_config"; then
        log_warn "Bedrock logging is already enabled. Checking configuration..."
        
        # Extract current settings
        local current_log_group current_role_arn current_s3_bucket
        current_log_group=$(echo "$current_config" | jq -r '.loggingConfig.cloudWatchConfig.logGroupName // empty' 2>/dev/null)
        current_role_arn=$(echo "$current_config" | jq -r '.loggingConfig.cloudWatchConfig.roleArn // empty' 2>/dev/null)
        current_s3_bucket=$(echo "$current_config" | jq -r '.loggingConfig.s3Config.bucketName // empty' 2>/dev/null)
        
        log_debug "Current log group: $current_log_group"
        log_debug "Current role ARN: $current_role_arn"
        log_debug "Current S3 bucket: $current_s3_bucket"
        
        # Check if configuration matches desired settings
        local needs_update=false
        
        if [[ "$current_log_group" != "$log_group_name" ]]; then
            log_info "Log group mismatch. Current: $current_log_group, Desired: $log_group_name"
            needs_update=true
        fi
        
        if [[ "$current_role_arn" != "$role_arn" ]]; then
            log_info "IAM role mismatch. Current: $current_role_arn, Desired: $role_arn"
            needs_update=true
        fi
        
        if [[ "$current_s3_bucket" != "$s3_bucket_name" ]]; then
            log_info "S3 bucket mismatch. Current: $current_s3_bucket, Desired: $s3_bucket_name"
            needs_update=true
        fi
        
        if [[ "$needs_update" == "true" ]]; then
            log_info "Configuration mismatch detected. Updating logging configuration..."
        else
            log_info "Current configuration matches desired settings. No update needed."
            return 0
        fi
    else
        log_info "Bedrock logging is not currently enabled. Enabling now..."
    fi
    
    # Create logging configuration
    local logging_config
    logging_config=$(create_logging_config "$log_group_name" "$role_arn" "$s3_bucket_name")
    
    log_debug "Logging configuration JSON:"
    log_debug "$logging_config"
    
    # Apply the logging configuration
    if echo "$logging_config" | aws bedrock put-model-invocation-logging-configuration \
        --cli-input-json file:///dev/stdin 2>/dev/null; then
        log_info "Bedrock logging configuration applied successfully"
    else
        log_error "Failed to apply Bedrock logging configuration"
        return 1
    fi
    
    # Wait for configuration to propagate
    log_info "Waiting for configuration to propagate (5 seconds)..."
    sleep 5
    
    # Verify the configuration was applied
    local new_config
    new_config=$(get_current_logging_config)
    
    if is_logging_enabled "$new_config"; then
        log_info "✅ Bedrock logging configuration verified successfully"
        return 0
    else
        log_error "Failed to verify Bedrock logging configuration"
        return 1
    fi
}

# Function to display current logging configuration
display_logging_config() {
    local config="$1"
    
    if is_logging_enabled "$config"; then
        local log_group role_arn s3_bucket text_delivery
        log_group=$(echo "$config" | jq -r '.loggingConfig.cloudWatchConfig.logGroupName // "Not configured"' 2>/dev/null)
        role_arn=$(echo "$config" | jq -r '.loggingConfig.cloudWatchConfig.roleArn // "Not configured"' 2>/dev/null)
        s3_bucket=$(echo "$config" | jq -r '.loggingConfig.s3Config.bucketName // "Not configured"' 2>/dev/null)
        text_delivery=$(echo "$config" | jq -r '.loggingConfig.textDataDeliveryEnabled // false' 2>/dev/null)
        
        echo
        echo "=== Current Bedrock Logging Configuration ==="
        echo "Status: ENABLED"
        echo "CloudWatch Log Group: $log_group"
        echo "IAM Role ARN: $role_arn"
        echo "S3 Bucket: $s3_bucket"
        echo "Text Data Delivery: $text_delivery"
        echo "============================================="
    else
        echo
        echo "=== Current Bedrock Logging Configuration ==="
        echo "Status: DISABLED"
        echo "============================================="
    fi
}

# Function to validate prerequisites
validate_prerequisites() {
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install AWS CLI first."
        exit 1
    fi
    
    # Check if jq is installed (needed for JSON parsing)
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed. Please install jq for JSON parsing."
        exit 1
    fi
    
    # Check if AWS credentials are configured
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check Bedrock permissions
    if ! aws bedrock get-model-invocation-logging-configuration >/dev/null 2>&1; then
        log_warn "Unable to check current Bedrock logging configuration. This may be normal if logging is not yet enabled."
    fi
    
    log_info "Prerequisites validated successfully"
}

# Main function
main() {
    log_info "Starting Bedrock logging configuration for AWS Bedrock monitoring"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Get configuration
    local account_id region log_group_name role_name role_arn s3_bucket_name
    account_id=$(get_account_id)
    region=$(get_region)
    log_group_name="${LOG_GROUP_NAME:-$DEFAULT_LOG_GROUP}"
    role_name="${IAM_ROLE_NAME:-$DEFAULT_IAM_ROLE_NAME}"
    s3_bucket_name=$(generate_s3_bucket_name "$account_id")
    
    log_info "AWS Account ID: $account_id"
    log_info "AWS Region: $region"
    log_info "CloudWatch Log Group: $log_group_name"
    log_info "IAM Role Name: $role_name"
    log_info "S3 Bucket Name: $s3_bucket_name"
    
    # Get IAM role ARN
    role_arn=$(get_iam_role_arn "$role_name")
    log_info "IAM Role ARN: $role_arn"
    
    # Verify prerequisites exist
    if ! verify_s3_bucket "$s3_bucket_name"; then
        log_error "S3 bucket verification failed. Exiting."
        exit 1
    fi
    
    if ! verify_log_group "$log_group_name"; then
        log_error "Log group verification failed. Exiting."
        exit 1
    fi
    
    # Display current configuration
    local current_config
    current_config=$(get_current_logging_config)
    display_logging_config "$current_config"
    
    # Enable Bedrock logging
    if ! enable_bedrock_logging "$log_group_name" "$role_arn" "$s3_bucket_name"; then
        log_error "Failed to enable Bedrock logging. Exiting."
        exit 1
    fi
    
    # Display final configuration
    local final_config
    final_config=$(get_current_logging_config)
    display_logging_config "$final_config"
    
    log_info "Bedrock logging configuration completed successfully!"
    
    # Export configuration for use by other scripts
    echo "export BEDROCK_LOGGING_ENABLED=\"true\"" > "${SCRIPT_DIR}/.bedrock-logging-config"
    echo "export BEDROCK_LOG_GROUP_NAME=\"$log_group_name\"" >> "${SCRIPT_DIR}/.bedrock-logging-config"
    echo "export BEDROCK_IAM_ROLE_ARN=\"$role_arn\"" >> "${SCRIPT_DIR}/.bedrock-logging-config"
    echo "export BEDROCK_S3_BUCKET_NAME=\"$s3_bucket_name\"" >> "${SCRIPT_DIR}/.bedrock-logging-config"
    log_info "Bedrock logging configuration saved to .bedrock-logging-config"
    
    echo
    echo "🎉 Bedrock logging is now configured!"
    echo "📊 Model invocations will be logged to:"
    echo "   • CloudWatch Logs: $log_group_name"
    echo "   • S3 Bucket: $s3_bucket_name"
    echo "📝 Text data delivery is enabled for full request/response logging"
    echo
    echo "Next steps:"
    echo "1. Run 4-create-cloudwatch-dashboard.sh to create monitoring dashboard"
    echo "2. Run 5-create-cloudwatch-alarms.sh to set up alerting"
    echo "3. Make some Bedrock API calls to generate logs"
    echo "4. Use 6-usage-report.py to analyze usage patterns"
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
        echo "  IAM_ROLE_NAME       IAM role name (default: BedrockCloudWatchLoggingRole)"
        echo "  BUCKET_PREFIX       S3 bucket prefix (default: bedrock-logs)"
        echo
        echo "Prerequisites:"
        echo "  1. Run 1-setup-iam-role.sh to create IAM role"
        echo "  2. Run 2-create-s3-bucket.sh to create S3 bucket"
        echo "  3. Run 2b-create-log-group.sh to create CloudWatch log group"
        echo
        echo "This script enables Bedrock model invocation logging with:"
        echo "  - Dual destination configuration (CloudWatch + S3)"
        echo "  - Text data delivery for full request/response logging"
        echo "  - Existing configuration detection and updates"
        echo "  - Configuration verification and validation"
        exit 0
        ;;
    --status)
        # Show current logging status only
        validate_prerequisites
        current_config=$(get_current_logging_config)
        display_logging_config "$current_config"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac