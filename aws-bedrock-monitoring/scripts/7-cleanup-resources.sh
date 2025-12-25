#!/bin/bash

# AWS Bedrock Monitoring - Comprehensive Cleanup Script
# This script removes all resources created by the Bedrock monitoring system
# Includes safety checks and confirmation prompts to prevent accidental deletion

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
DEFAULT_IAM_ROLE_NAME="BedrockCloudWatchLoggingRole"
DEFAULT_POLICY_NAME="BedrockCloudWatchLoggingPolicy"
DEFAULT_BUCKET_PREFIX="bedrock-logs"
DEFAULT_LOG_GROUP="/aws/bedrock/modelinvocations"
DEFAULT_DASHBOARD_NAME="BedrockUsageMonitoring"
DEFAULT_SNS_TOPIC_NAME="bedrock-usage-alerts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_success() {
    echo -e "${CYAN}[SUCCESS]${NC} $1"
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

# Function to generate resource names based on account ID
generate_resource_names() {
    local account_id="$1"
    
    # Generate S3 bucket name
    S3_BUCKET_NAME="${BUCKET_PREFIX:-$DEFAULT_BUCKET_PREFIX}-${account_id}"
    
    # Other resource names
    IAM_ROLE_NAME="${IAM_ROLE_NAME:-$DEFAULT_IAM_ROLE_NAME}"
    POLICY_NAME="${POLICY_NAME:-$DEFAULT_POLICY_NAME}"
    LOG_GROUP_NAME="${LOG_GROUP_NAME:-$DEFAULT_LOG_GROUP}"
    DASHBOARD_NAME="${DASHBOARD_NAME:-$DEFAULT_DASHBOARD_NAME}"
    SNS_TOPIC_NAME="${SNS_TOPIC_NAME:-$DEFAULT_SNS_TOPIC_NAME}"
}

# Function to confirm deletion with user
confirm_deletion() {
    local resource_type="$1"
    local resource_name="$2"
    local force_mode="$3"
    
    if [[ "$force_mode" == "true" ]]; then
        return 0
    fi
    
    echo
    log_warn "About to delete $resource_type: $resource_name"
    read -p "Are you sure you want to delete this resource? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Skipping deletion of $resource_type: $resource_name"
        return 1
    fi
    
    return 0
}

# Function to disable Bedrock logging
disable_bedrock_logging() {
    local force_mode="$1"
    
    log_info "Checking Bedrock logging configuration..."
    
    # Check if logging is currently enabled
    local current_config
    current_config=$(aws bedrock get-model-invocation-logging-configuration 2>/dev/null || echo "{}")
    
    local logging_enabled
    logging_enabled=$(echo "$current_config" | jq -r '.loggingConfig // empty' 2>/dev/null)
    
    if [[ -z "$logging_enabled" || "$logging_enabled" == "null" ]]; then
        log_info "Bedrock logging is not currently enabled"
        return 0
    fi
    
    if ! confirm_deletion "Bedrock logging configuration" "model invocation logging" "$force_mode"; then
        return 0
    fi
    
    log_info "Disabling Bedrock model invocation logging..."
    
    # Disable logging by removing the configuration
    if aws bedrock delete-model-invocation-logging-configuration 2>/dev/null; then
        log_success "✅ Bedrock logging disabled successfully"
    else
        log_error "Failed to disable Bedrock logging"
        return 1
    fi
    
    return 0
}

# Function to delete CloudWatch alarms
delete_cloudwatch_alarms() {
    local force_mode="$1"
    
    log_info "Checking for CloudWatch alarms..."
    
    # List of alarm names to delete
    local alarm_names=(
        "Bedrock-HighInputTokenUsage"
        "Bedrock-HighErrorRate"
        "Bedrock-UnusualInvocationSpike"
        "Bedrock-HighLatency"
    )
    
    local deleted_count=0
    
    for alarm_name in "${alarm_names[@]}"; do
        # Check if alarm exists
        if aws cloudwatch describe-alarms --alarm-names "$alarm_name" --query 'MetricAlarms[0].AlarmName' --output text 2>/dev/null | grep -q "$alarm_name"; then
            if confirm_deletion "CloudWatch alarm" "$alarm_name" "$force_mode"; then
                log_info "Deleting CloudWatch alarm: $alarm_name"
                if aws cloudwatch delete-alarms --alarm-names "$alarm_name" 2>/dev/null; then
                    log_success "✅ Deleted alarm: $alarm_name"
                    ((deleted_count++))
                else
                    log_error "Failed to delete alarm: $alarm_name"
                fi
            fi
        else
            log_debug "Alarm not found: $alarm_name"
        fi
    done
    
    if [[ $deleted_count -gt 0 ]]; then
        log_success "Deleted $deleted_count CloudWatch alarm(s)"
    else
        log_info "No CloudWatch alarms found to delete"
    fi
    
    return 0
}

# Function to delete SNS topic
delete_sns_topic() {
    local topic_name="$1"
    local force_mode="$2"
    
    log_info "Checking for SNS topic: $topic_name"
    
    # Get topic ARN if it exists
    local topic_arn
    topic_arn=$(aws sns list-topics --query "Topics[?contains(TopicArn, ':${topic_name}')].TopicArn" --output text 2>/dev/null)
    
    if [[ -z "$topic_arn" ]]; then
        log_info "SNS topic not found: $topic_name"
        return 0
    fi
    
    if ! confirm_deletion "SNS topic" "$topic_name ($topic_arn)" "$force_mode"; then
        return 0
    fi
    
    log_info "Deleting SNS topic: $topic_name"
    
    if aws sns delete-topic --topic-arn "$topic_arn" 2>/dev/null; then
        log_success "✅ SNS topic deleted: $topic_name"
    else
        log_error "Failed to delete SNS topic: $topic_name"
        return 1
    fi
    
    return 0
}

# Function to delete CloudWatch dashboard
delete_cloudwatch_dashboard() {
    local dashboard_name="$1"
    local force_mode="$2"
    
    log_info "Checking for CloudWatch dashboard: $dashboard_name"
    
    # Check if dashboard exists
    if ! aws cloudwatch get-dashboard --dashboard-name "$dashboard_name" >/dev/null 2>&1; then
        log_info "CloudWatch dashboard not found: $dashboard_name"
        return 0
    fi
    
    if ! confirm_deletion "CloudWatch dashboard" "$dashboard_name" "$force_mode"; then
        return 0
    fi
    
    log_info "Deleting CloudWatch dashboard: $dashboard_name"
    
    if aws cloudwatch delete-dashboards --dashboard-names "$dashboard_name" 2>/dev/null; then
        log_success "✅ CloudWatch dashboard deleted: $dashboard_name"
    else
        log_error "Failed to delete CloudWatch dashboard: $dashboard_name"
        return 1
    fi
    
    return 0
}

# Function to delete CloudWatch log group
delete_cloudwatch_log_group() {
    local log_group_name="$1"
    local force_mode="$2"
    
    log_info "Checking for CloudWatch log group: $log_group_name"
    
    # Check if log group exists
    local result
    result=$(aws logs describe-log-groups \
        --log-group-name-prefix "$log_group_name" \
        --query "logGroups[?logGroupName=='$log_group_name'].logGroupName" \
        --output text 2>/dev/null)
    
    if [[ "$result" != "$log_group_name" ]]; then
        log_info "CloudWatch log group not found: $log_group_name"
        return 0
    fi
    
    if ! confirm_deletion "CloudWatch log group" "$log_group_name" "$force_mode"; then
        return 0
    fi
    
    log_warn "⚠️  This will permanently delete all logs in the log group!"
    if [[ "$force_mode" != "true" ]]; then
        read -p "Are you absolutely sure? This cannot be undone! (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping deletion of log group: $log_group_name"
            return 0
        fi
    fi
    
    log_info "Deleting CloudWatch log group: $log_group_name"
    
    if aws logs delete-log-group --log-group-name "$log_group_name" 2>/dev/null; then
        log_success "✅ CloudWatch log group deleted: $log_group_name"
    else
        log_error "Failed to delete CloudWatch log group: $log_group_name"
        return 1
    fi
    
    return 0
}

# Function to delete S3 bucket
delete_s3_bucket() {
    local bucket_name="$1"
    local force_mode="$2"
    
    log_info "Checking for S3 bucket: $bucket_name"
    
    # Check if bucket exists
    if ! aws s3api head-bucket --bucket "$bucket_name" >/dev/null 2>&1; then
        log_info "S3 bucket not found: $bucket_name"
        return 0
    fi
    
    if ! confirm_deletion "S3 bucket" "$bucket_name" "$force_mode"; then
        return 0
    fi
    
    log_warn "⚠️  This will permanently delete the bucket and ALL its contents!"
    if [[ "$force_mode" != "true" ]]; then
        read -p "Are you absolutely sure? This cannot be undone! (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping deletion of S3 bucket: $bucket_name"
            return 0
        fi
    fi
    
    log_info "Deleting S3 bucket contents: $bucket_name"
    
    # First, delete all objects and versions in the bucket
    if aws s3 rm "s3://$bucket_name" --recursive 2>/dev/null; then
        log_info "Bucket contents deleted"
    else
        log_warn "Failed to delete some bucket contents (may be empty)"
    fi
    
    # Delete all object versions if versioning is enabled
    log_info "Deleting object versions..."
    aws s3api list-object-versions --bucket "$bucket_name" --query 'Versions[].{Key:Key,VersionId:VersionId}' --output text 2>/dev/null | \
    while read -r key version_id; do
        if [[ -n "$key" && -n "$version_id" ]]; then
            aws s3api delete-object --bucket "$bucket_name" --key "$key" --version-id "$version_id" >/dev/null 2>&1 || true
        fi
    done
    
    # Delete delete markers
    log_info "Deleting delete markers..."
    aws s3api list-object-versions --bucket "$bucket_name" --query 'DeleteMarkers[].{Key:Key,VersionId:VersionId}' --output text 2>/dev/null | \
    while read -r key version_id; do
        if [[ -n "$key" && -n "$version_id" ]]; then
            aws s3api delete-object --bucket "$bucket_name" --key "$key" --version-id "$version_id" >/dev/null 2>&1 || true
        fi
    done
    
    # Now delete the bucket
    log_info "Deleting S3 bucket: $bucket_name"
    
    if aws s3api delete-bucket --bucket "$bucket_name" 2>/dev/null; then
        log_success "✅ S3 bucket deleted: $bucket_name"
    else
        log_error "Failed to delete S3 bucket: $bucket_name"
        log_error "The bucket may still contain objects or have dependencies"
        return 1
    fi
    
    return 0
}

# Function to delete IAM role and policies
delete_iam_role() {
    local role_name="$1"
    local policy_name="$2"
    local force_mode="$3"
    
    log_info "Checking for IAM role: $role_name"
    
    # Check if role exists
    if ! aws iam get-role --role-name "$role_name" >/dev/null 2>&1; then
        log_info "IAM role not found: $role_name"
        return 0
    fi
    
    if ! confirm_deletion "IAM role" "$role_name" "$force_mode"; then
        return 0
    fi
    
    log_info "Deleting IAM role: $role_name"
    
    # First, detach and delete inline policies
    log_info "Removing inline policies from role: $role_name"
    local policies
    policies=$(aws iam list-role-policies --role-name "$role_name" --query 'PolicyNames' --output text 2>/dev/null)
    
    if [[ -n "$policies" ]]; then
        for policy in $policies; do
            log_debug "Deleting inline policy: $policy"
            if aws iam delete-role-policy --role-name "$role_name" --policy-name "$policy" 2>/dev/null; then
                log_info "✅ Deleted inline policy: $policy"
            else
                log_warn "Failed to delete inline policy: $policy"
            fi
        done
    fi
    
    # Detach managed policies
    log_info "Detaching managed policies from role: $role_name"
    local attached_policies
    attached_policies=$(aws iam list-attached-role-policies --role-name "$role_name" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null)
    
    if [[ -n "$attached_policies" ]]; then
        for policy_arn in $attached_policies; do
            log_debug "Detaching managed policy: $policy_arn"
            if aws iam detach-role-policy --role-name "$role_name" --policy-arn "$policy_arn" 2>/dev/null; then
                log_info "✅ Detached managed policy: $policy_arn"
            else
                log_warn "Failed to detach managed policy: $policy_arn"
            fi
        done
    fi
    
    # Delete the role
    log_info "Deleting IAM role: $role_name"
    
    if aws iam delete-role --role-name "$role_name" 2>/dev/null; then
        log_success "✅ IAM role deleted: $role_name"
    else
        log_error "Failed to delete IAM role: $role_name"
        return 1
    fi
    
    return 0
}

# Function to clean up local configuration files
cleanup_local_files() {
    local force_mode="$1"
    
    log_info "Cleaning up local configuration files..."
    
    local config_files=(
        ".s3-config"
        ".log-group-config"
        ".bedrock-logging-config"
        ".dashboard-config"
        ".alarms-config"
    )
    
    local deleted_count=0
    
    for config_file in "${config_files[@]}"; do
        local file_path="${SCRIPT_DIR}/${config_file}"
        if [[ -f "$file_path" ]]; then
            if [[ "$force_mode" == "true" ]] || confirm_deletion "configuration file" "$config_file" "$force_mode"; then
                if rm -f "$file_path" 2>/dev/null; then
                    log_success "✅ Deleted configuration file: $config_file"
                    ((deleted_count++))
                else
                    log_warn "Failed to delete configuration file: $config_file"
                fi
            fi
        fi
    done
    
    if [[ $deleted_count -gt 0 ]]; then
        log_success "Cleaned up $deleted_count configuration file(s)"
    else
        log_info "No configuration files found to clean up"
    fi
    
    return 0
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
    
    log_info "Prerequisites validated successfully"
}

# Function to display cleanup summary
display_cleanup_summary() {
    local account_id="$1"
    local region="$2"
    
    echo
    echo "=== Cleanup Summary ==="
    echo "Account ID: $account_id"
    echo "Region: $region"
    echo
    echo "Resources that will be checked for deletion:"
    echo "  🔧 Bedrock logging configuration"
    echo "  ⚠️  CloudWatch alarms (4 alarms)"
    echo "  📧 SNS topic: $SNS_TOPIC_NAME"
    echo "  📊 CloudWatch dashboard: $DASHBOARD_NAME"
    echo "  📝 CloudWatch log group: $LOG_GROUP_NAME"
    echo "  🗄️  S3 bucket: $S3_BUCKET_NAME"
    echo "  🔐 IAM role: $IAM_ROLE_NAME"
    echo "  📁 Local configuration files"
    echo
    echo "⚠️  WARNING: This operation cannot be undone!"
    echo "⚠️  All logs and data will be permanently deleted!"
    echo "======================="
}

# Function to perform complete cleanup
perform_cleanup() {
    local force_mode="$1"
    local account_id="$2"
    local region="$3"
    
    log_info "Starting comprehensive cleanup of Bedrock monitoring resources..."
    
    local failed_operations=0
    
    # 1. Disable Bedrock logging first (prevents new logs)
    if ! disable_bedrock_logging "$force_mode"; then
        ((failed_operations++))
    fi
    
    # 2. Delete CloudWatch alarms
    if ! delete_cloudwatch_alarms "$force_mode"; then
        ((failed_operations++))
    fi
    
    # 3. Delete SNS topic
    if ! delete_sns_topic "$SNS_TOPIC_NAME" "$force_mode"; then
        ((failed_operations++))
    fi
    
    # 4. Delete CloudWatch dashboard
    if ! delete_cloudwatch_dashboard "$DASHBOARD_NAME" "$force_mode"; then
        ((failed_operations++))
    fi
    
    # 5. Delete CloudWatch log group (after disabling logging)
    if ! delete_cloudwatch_log_group "$LOG_GROUP_NAME" "$force_mode"; then
        ((failed_operations++))
    fi
    
    # 6. Delete S3 bucket
    if ! delete_s3_bucket "$S3_BUCKET_NAME" "$force_mode"; then
        ((failed_operations++))
    fi
    
    # 7. Delete IAM role (last, as other resources may depend on it)
    if ! delete_iam_role "$IAM_ROLE_NAME" "$POLICY_NAME" "$force_mode"; then
        ((failed_operations++))
    fi
    
    # 8. Clean up local configuration files
    if ! cleanup_local_files "$force_mode"; then
        ((failed_operations++))
    fi
    
    # Summary
    echo
    if [[ $failed_operations -eq 0 ]]; then
        log_success "🎉 Cleanup completed successfully!"
        log_success "All Bedrock monitoring resources have been removed."
    else
        log_warn "⚠️  Cleanup completed with $failed_operations failed operation(s)."
        log_warn "Some resources may still exist. Check the output above for details."
    fi
    
    return $failed_operations
}

# Main function
main() {
    local force_mode="false"
    local dry_run="false"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force|-f)
                force_mode="true"
                shift
                ;;
            --dry-run)
                dry_run="true"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    log_info "AWS Bedrock Monitoring - Comprehensive Cleanup"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Get AWS configuration
    local account_id region
    account_id=$(get_account_id)
    region=$(get_region)
    
    # Generate resource names
    generate_resource_names "$account_id"
    
    # Display cleanup summary
    display_cleanup_summary "$account_id" "$region"
    
    # Dry run mode - just show what would be deleted
    if [[ "$dry_run" == "true" ]]; then
        log_info "DRY RUN MODE - No resources will be deleted"
        log_info "This would delete the resources listed above"
        exit 0
    fi
    
    # Final confirmation unless in force mode
    if [[ "$force_mode" != "true" ]]; then
        echo
        log_warn "This will permanently delete ALL Bedrock monitoring resources!"
        read -p "Are you absolutely sure you want to proceed? (y/N): " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Cleanup cancelled by user"
            exit 0
        fi
    fi
    
    # Perform the cleanup
    if ! perform_cleanup "$force_mode" "$account_id" "$region"; then
        exit 1
    fi
    
    log_success "Cleanup process completed!"
}

# Function to show help
show_help() {
    cat << EOF
Usage: $0 [options]

Options:
  --force, -f         Skip all confirmation prompts (dangerous!)
  --dry-run          Show what would be deleted without actually deleting
  --help, -h         Show this help message

Environment Variables:
  IAM_ROLE_NAME      IAM role name (default: BedrockCloudWatchLoggingRole)
  BUCKET_PREFIX      S3 bucket prefix (default: bedrock-logs)
  LOG_GROUP_NAME     CloudWatch log group (default: /aws/bedrock/modelinvocations)
  DASHBOARD_NAME     CloudWatch dashboard (default: BedrockUsageMonitoring)
  SNS_TOPIC_NAME     SNS topic name (default: bedrock-usage-alerts)

This script removes ALL resources created by the Bedrock monitoring system:
  - Bedrock logging configuration
  - CloudWatch alarms (4 alarms)
  - SNS topic for notifications
  - CloudWatch dashboard
  - CloudWatch log group (with all logs)
  - S3 bucket (with all contents)
  - IAM role and policies
  - Local configuration files

⚠️  WARNING: This operation cannot be undone!
⚠️  All monitoring data and logs will be permanently deleted!

Examples:
  $0                    # Interactive cleanup with confirmations
  $0 --dry-run         # Show what would be deleted
  $0 --force           # Delete everything without prompts (dangerous!)

EOF
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi