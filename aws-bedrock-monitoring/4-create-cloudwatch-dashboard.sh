#!/bin/bash

# AWS Bedrock Monitoring - CloudWatch Dashboard Creation Script
# This script creates a comprehensive CloudWatch dashboard for Bedrock usage monitoring
# Includes invocation, token, latency, error, and log viewer widgets

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
DEFAULT_DASHBOARD_NAME="BedrockUsageMonitoring"
DEFAULT_REGION="us-east-1"
DEFAULT_LOG_GROUP="/aws/bedrock/modelinvocations"

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
        region="$DEFAULT_REGION"
        log_warn "No default region configured, using $DEFAULT_REGION"
    fi
    
    echo "$region"
}

# Function to check if dashboard exists
dashboard_exists() {
    local dashboard_name="$1"
    aws cloudwatch get-dashboard --dashboard-name "$dashboard_name" >/dev/null 2>&1
}

# Function to create invocation metrics widget
create_invocation_widget() {
    local region="$1"
    
    cat <<EOF
{
    "type": "metric",
    "x": 0,
    "y": 0,
    "width": 12,
    "height": 6,
    "properties": {
        "metrics": [
            [ "AWS/Bedrock", "Invocations", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-instant-v1" ],
            [ ".", ".", ".", "anthropic.claude-v2" ],
            [ ".", ".", ".", "anthropic.claude-v2:1" ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "$region",
        "title": "Bedrock Model Invocations",
        "period": 300,
        "stat": "Sum",
        "yAxis": {
            "left": {
                "min": 0
            }
        }
    }
}
EOF
}

# Function to create input token metrics widget
create_input_token_widget() {
    local region="$1"
    
    cat <<EOF
{
    "type": "metric",
    "x": 12,
    "y": 0,
    "width": 12,
    "height": 6,
    "properties": {
        "metrics": [
            [ "AWS/Bedrock", "InputTokenCount", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-instant-v1" ],
            [ ".", ".", ".", "anthropic.claude-v2" ],
            [ ".", ".", ".", "anthropic.claude-v2:1" ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "$region",
        "title": "Input Token Usage",
        "period": 300,
        "stat": "Sum",
        "yAxis": {
            "left": {
                "min": 0
            }
        }
    }
}
EOF
}

# Function to create output token metrics widget
create_output_token_widget() {
    local region="$1"
    
    cat <<EOF
{
    "type": "metric",
    "x": 0,
    "y": 6,
    "width": 12,
    "height": 6,
    "properties": {
        "metrics": [
            [ "AWS/Bedrock", "OutputTokenCount", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-instant-v1" ],
            [ ".", ".", ".", "anthropic.claude-v2" ],
            [ ".", ".", ".", "anthropic.claude-v2:1" ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "$region",
        "title": "Output Token Usage",
        "period": 300,
        "stat": "Sum",
        "yAxis": {
            "left": {
                "min": 0
            }
        }
    }
}
EOF
}

# Function to create average latency widget
create_average_latency_widget() {
    local region="$1"
    
    cat <<EOF
{
    "type": "metric",
    "x": 12,
    "y": 6,
    "width": 12,
    "height": 6,
    "properties": {
        "metrics": [
            [ "AWS/Bedrock", "InvocationLatency", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-instant-v1" ],
            [ ".", ".", ".", "anthropic.claude-v2" ],
            [ ".", ".", ".", "anthropic.claude-v2:1" ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "$region",
        "title": "Average Latency (ms)",
        "period": 300,
        "stat": "Average",
        "yAxis": {
            "left": {
                "min": 0
            }
        }
    }
}
EOF
}

# Function to create p99 latency widget
create_p99_latency_widget() {
    local region="$1"
    
    cat <<EOF
{
    "type": "metric",
    "x": 0,
    "y": 12,
    "width": 12,
    "height": 6,
    "properties": {
        "metrics": [
            [ "AWS/Bedrock", "InvocationLatency", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-instant-v1" ],
            [ ".", ".", ".", "anthropic.claude-v2" ],
            [ ".", ".", ".", "anthropic.claude-v2:1" ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "$region",
        "title": "99th Percentile Latency (ms)",
        "period": 300,
        "stat": "p99",
        "yAxis": {
            "left": {
                "min": 0
            }
        }
    }
}
EOF
}

# Function to create error tracking widget
create_error_widget() {
    local region="$1"
    
    cat <<EOF
{
    "type": "metric",
    "x": 12,
    "y": 12,
    "width": 12,
    "height": 6,
    "properties": {
        "metrics": [
            [ "AWS/Bedrock", "InvocationClientErrors", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-instant-v1" ],
            [ ".", ".", ".", "anthropic.claude-v2" ],
            [ ".", ".", ".", "anthropic.claude-v2:1" ],
            [ ".", "InvocationServerErrors", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-opus-20240229-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0" ],
            [ ".", ".", ".", "anthropic.claude-instant-v1" ],
            [ ".", ".", ".", "anthropic.claude-v2" ],
            [ ".", ".", ".", "anthropic.claude-v2:1" ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "$region",
        "title": "Error Counts (Client & Server)",
        "period": 300,
        "stat": "Sum",
        "yAxis": {
            "left": {
                "min": 0
            }
        }
    }
}
EOF
}

# Function to create log viewer widget
create_log_viewer_widget() {
    local region="$1"
    local log_group="$2"
    
    cat <<EOF
{
    "type": "log",
    "x": 0,
    "y": 18,
    "width": 24,
    "height": 6,
    "properties": {
        "query": "SOURCE '$log_group'\n| fields @timestamp, modelId, inputTokenCount, outputTokenCount, invocationLatency\n| sort @timestamp desc\n| limit 100",
        "region": "$region",
        "title": "Recent Bedrock Invocations",
        "view": "table"
    }
}
EOF
}

# Function to create complete dashboard body
create_dashboard_body() {
    local region="$1"
    local log_group="$2"
    
    cat <<EOF
{
    "widgets": [
$(create_invocation_widget "$region"),
$(create_input_token_widget "$region"),
$(create_output_token_widget "$region"),
$(create_average_latency_widget "$region"),
$(create_p99_latency_widget "$region"),
$(create_error_widget "$region"),
$(create_log_viewer_widget "$region" "$log_group")
    ]
}
EOF
}

# Function to create CloudWatch dashboard
create_cloudwatch_dashboard() {
    local dashboard_name="$1"
    local region="$2"
    local log_group="$3"
    
    log_info "Setting up CloudWatch dashboard: $dashboard_name"
    
    # Check if dashboard already exists
    if dashboard_exists "$dashboard_name"; then
        log_warn "Dashboard $dashboard_name already exists. Updating configuration..."
    else
        log_info "Creating new dashboard: $dashboard_name"
    fi
    
    # Create dashboard body
    local dashboard_body
    dashboard_body=$(create_dashboard_body "$region" "$log_group")
    
    log_debug "Dashboard configuration:"
    log_debug "$dashboard_body"
    
    # Create or update the dashboard
    if echo "$dashboard_body" | aws cloudwatch put-dashboard \
        --dashboard-name "$dashboard_name" \
        --dashboard-body file:///dev/stdin 2>/dev/null; then
        log_info "✅ CloudWatch dashboard created/updated successfully"
    else
        log_error "Failed to create/update CloudWatch dashboard"
        return 1
    fi
    
    # Get dashboard URL
    local dashboard_url="https://${region}.console.aws.amazon.com/cloudwatch/home?region=${region}#dashboards:name=${dashboard_name}"
    
    echo
    echo "=== CloudWatch Dashboard Configuration ==="
    echo "Dashboard Name: $dashboard_name"
    echo "Region: $region"
    echo "Log Group: $log_group"
    echo "Dashboard URL: $dashboard_url"
    echo
    echo "Widgets Included:"
    echo "  ✅ Model Invocations (by model type)"
    echo "  ✅ Input Token Usage (by model type)"
    echo "  ✅ Output Token Usage (by model type)"
    echo "  ✅ Average Latency (by model type)"
    echo "  ✅ 99th Percentile Latency (by model type)"
    echo "  ✅ Error Tracking (client & server errors)"
    echo "  ✅ Recent Invocations Log Viewer"
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
    
    # Check CloudWatch permissions
    if ! aws cloudwatch list-dashboards >/dev/null 2>&1; then
        log_error "Unable to access CloudWatch dashboards. Please check IAM permissions."
        exit 1
    fi
    
    log_info "Prerequisites validated successfully"
}

# Function to verify log group exists
verify_log_group() {
    local log_group_name="$1"
    local result
    
    result=$(aws logs describe-log-groups \
        --log-group-name-prefix "$log_group_name" \
        --query "logGroups[?logGroupName=='$log_group_name'].logGroupName" \
        --output text 2>/dev/null)
    
    if [[ "$result" != "$log_group_name" ]]; then
        log_warn "CloudWatch log group $log_group_name not found."
        log_warn "Dashboard will be created, but log viewer widget may not show data until logging is enabled."
        log_warn "Run 2b-create-log-group.sh and 3-enable-bedrock-logging.sh to enable logging."
    else
        log_info "CloudWatch log group $log_group_name verified"
    fi
}

# Main function
main() {
    log_info "Starting CloudWatch dashboard creation for AWS Bedrock monitoring"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Get configuration
    local account_id region dashboard_name log_group_name
    account_id=$(get_account_id)
    region=$(get_region)
    dashboard_name="${DASHBOARD_NAME:-$DEFAULT_DASHBOARD_NAME}"
    log_group_name="${LOG_GROUP_NAME:-$DEFAULT_LOG_GROUP}"
    
    log_info "AWS Account ID: $account_id"
    log_info "AWS Region: $region"
    log_info "Dashboard Name: $dashboard_name"
    log_info "Log Group: $log_group_name"
    
    # Verify log group exists (warn if not, but continue)
    verify_log_group "$log_group_name"
    
    # Create CloudWatch dashboard
    if ! create_cloudwatch_dashboard "$dashboard_name" "$region" "$log_group_name"; then
        log_error "Failed to create CloudWatch dashboard. Exiting."
        exit 1
    fi
    
    log_info "CloudWatch dashboard creation completed successfully!"
    
    # Export configuration for use by other scripts
    echo "export BEDROCK_DASHBOARD_NAME=\"$dashboard_name\"" > "${SCRIPT_DIR}/.dashboard-config"
    echo "export BEDROCK_DASHBOARD_REGION=\"$region\"" >> "${SCRIPT_DIR}/.dashboard-config"
    log_info "Dashboard configuration saved to .dashboard-config"
    
    echo
    echo "🎉 CloudWatch dashboard is now available!"
    echo "📊 Dashboard includes all required widgets:"
    echo "   • Model invocations by type"
    echo "   • Input and output token usage"
    echo "   • Average and 99th percentile latency"
    echo "   • Error tracking (client and server)"
    echo "   • Recent invocations log viewer"
    echo
    echo "🔗 Access your dashboard at:"
    echo "   https://${region}.console.aws.amazon.com/cloudwatch/home?region=${region}#dashboards:name=${dashboard_name}"
    echo
    echo "Next steps:"
    echo "1. Make some Bedrock API calls to see data in the dashboard"
    echo "2. Run 5-create-cloudwatch-alarms.sh to set up alerting"
    echo "3. Use 6-usage-report.py to generate detailed usage reports"
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
        echo "  DASHBOARD_NAME      CloudWatch dashboard name (default: BedrockUsageMonitoring)"
        echo "  LOG_GROUP_NAME      CloudWatch log group name (default: /aws/bedrock/modelinvocations)"
        echo
        echo "This script creates a comprehensive CloudWatch dashboard with:"
        echo "  - Model invocation metrics by type"
        echo "  - Input and output token usage tracking"
        echo "  - Average and 99th percentile latency metrics"
        echo "  - Error tracking for client and server errors"
        echo "  - Recent invocations log viewer"
        echo "  - Time period controls and metric aggregations"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac