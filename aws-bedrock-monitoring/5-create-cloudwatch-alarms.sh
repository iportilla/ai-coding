#!/bin/bash

# AWS Bedrock Monitoring - CloudWatch Alarms Setup Script
# This script creates comprehensive CloudWatch alarms for Bedrock usage monitoring
# Includes four required alarms with SNS topic for notifications

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
DEFAULT_SNS_TOPIC_NAME="bedrock-usage-alerts"
DEFAULT_REGION="us-east-1"

# Alarm thresholds (configurable via environment variables)
HIGH_TOKEN_THRESHOLD="${HIGH_TOKEN_THRESHOLD:-100000}"      # 100k tokens/hour
ERROR_RATE_THRESHOLD="${ERROR_RATE_THRESHOLD:-10}"          # 10 errors/5min
INVOCATION_THRESHOLD="${INVOCATION_THRESHOLD:-1000}"        # 1000 invocations/hour
HIGH_LATENCY_THRESHOLD="${HIGH_LATENCY_THRESHOLD:-10000}"   # 10s in milliseconds

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

# Function to check if SNS topic exists
sns_topic_exists() {
    local topic_name="$1"
    aws sns list-topics --query "Topics[?contains(TopicArn, ':${topic_name}')].TopicArn" --output text | grep -q "$topic_name"
}

# Function to get or create SNS topic
get_or_create_sns_topic() {
    local topic_name="$1"
    local account_id="$2"
    local region="$3"
    
    log_info "Setting up SNS topic for alarm notifications: $topic_name"
    
    # Check if topic already exists
    if sns_topic_exists "$topic_name"; then
        log_info "SNS topic $topic_name already exists"
        local topic_arn
        topic_arn=$(aws sns list-topics --query "Topics[?contains(TopicArn, ':${topic_name}')].TopicArn" --output text)
        echo "$topic_arn"
    else
        log_info "Creating new SNS topic: $topic_name"
        local topic_arn
        topic_arn=$(aws sns create-topic --name "$topic_name" --query 'TopicArn' --output text)
        
        # Set topic display name for better identification
        aws sns set-topic-attributes \
            --topic-arn "$topic_arn" \
            --attribute-name DisplayName \
            --attribute-value "Bedrock Usage Alerts"
        
        log_info "SNS topic created successfully: $topic_arn"
        echo "$topic_arn"
    fi
}

# Function to check if alarm exists
alarm_exists() {
    local alarm_name="$1"
    aws cloudwatch describe-alarms --alarm-names "$alarm_name" --query 'MetricAlarms[0].AlarmName' --output text 2>/dev/null | grep -q "$alarm_name"
}

# Function to create or update high token usage alarm
create_high_token_alarm() {
    local sns_topic_arn="$1"
    local threshold="$2"
    local alarm_name="Bedrock-HighInputTokenUsage"
    
    log_info "Creating/updating high token usage alarm (threshold: ${threshold} tokens/hour)"
    
    if aws cloudwatch put-metric-alarm \
        --alarm-name "$alarm_name" \
        --alarm-description "Alert when input tokens exceed ${threshold} per hour - indicates high usage that may impact costs" \
        --metric-name InputTokenCount \
        --namespace AWS/Bedrock \
        --statistic Sum \
        --period 3600 \
        --evaluation-periods 1 \
        --threshold "$threshold" \
        --comparison-operator GreaterThanThreshold \
        --alarm-actions "$sns_topic_arn" \
        --ok-actions "$sns_topic_arn" \
        --treat-missing-data notBreaching \
        --tags Key=Purpose,Value=BedrockMonitoring Key=AlarmType,Value=Usage 2>/dev/null; then
        log_info "✅ High token usage alarm configured: $alarm_name"
        return 0
    else
        log_error "Failed to create high token usage alarm: $alarm_name"
        return 1
    fi
}

# Function to create or update error rate alarm
create_error_rate_alarm() {
    local sns_topic_arn="$1"
    local threshold="$2"
    local alarm_name="Bedrock-HighErrorRate"
    
    log_info "Creating/updating error rate alarm (threshold: ${threshold} errors/5min)"
    
    if aws cloudwatch put-metric-alarm \
        --alarm-name "$alarm_name" \
        --alarm-description "Alert when client errors exceed ${threshold} per 5 minutes - indicates API issues or invalid requests" \
        --metric-name InvocationClientErrors \
        --namespace AWS/Bedrock \
        --statistic Sum \
        --period 300 \
        --evaluation-periods 1 \
        --threshold "$threshold" \
        --comparison-operator GreaterThanThreshold \
        --alarm-actions "$sns_topic_arn" \
        --ok-actions "$sns_topic_arn" \
        --treat-missing-data notBreaching \
        --tags Key=Purpose,Value=BedrockMonitoring Key=AlarmType,Value=Reliability 2>/dev/null; then
        log_info "✅ Error rate alarm configured: $alarm_name"
        return 0
    else
        log_error "Failed to create error rate alarm: $alarm_name"
        return 1
    fi
}

# Function to create or update invocation spike alarm
create_invocation_spike_alarm() {
    local sns_topic_arn="$1"
    local threshold="$2"
    local alarm_name="Bedrock-UnusualInvocationSpike"
    
    log_info "Creating/updating invocation spike alarm (threshold: ${threshold} invocations/hour)"
    
    if aws cloudwatch put-metric-alarm \
        --alarm-name "$alarm_name" \
        --alarm-description "Alert when invocations exceed ${threshold} per hour - indicates unusual activity or potential runaway processes" \
        --metric-name Invocations \
        --namespace AWS/Bedrock \
        --statistic Sum \
        --period 3600 \
        --evaluation-periods 1 \
        --threshold "$threshold" \
        --comparison-operator GreaterThanThreshold \
        --alarm-actions "$sns_topic_arn" \
        --ok-actions "$sns_topic_arn" \
        --treat-missing-data notBreaching \
        --tags Key=Purpose,Value=BedrockMonitoring Key=AlarmType,Value=Activity 2>/dev/null; then
        log_info "✅ Invocation spike alarm configured: $alarm_name"
        return 0
    else
        log_error "Failed to create invocation spike alarm: $alarm_name"
        return 1
    fi
}

# Function to create or update high latency alarm
create_high_latency_alarm() {
    local sns_topic_arn="$1"
    local threshold="$2"
    local alarm_name="Bedrock-HighLatency"
    
    log_info "Creating/updating high latency alarm (threshold: ${threshold}ms average)"
    
    if aws cloudwatch put-metric-alarm \
        --alarm-name "$alarm_name" \
        --alarm-description "Alert when average latency exceeds ${threshold}ms - indicates performance degradation" \
        --metric-name InvocationLatency \
        --namespace AWS/Bedrock \
        --statistic Average \
        --period 300 \
        --evaluation-periods 2 \
        --threshold "$threshold" \
        --comparison-operator GreaterThanThreshold \
        --alarm-actions "$sns_topic_arn" \
        --ok-actions "$sns_topic_arn" \
        --treat-missing-data notBreaching \
        --tags Key=Purpose,Value=BedrockMonitoring Key=AlarmType,Value=Performance 2>/dev/null; then
        log_info "✅ High latency alarm configured: $alarm_name"
        return 0
    else
        log_error "Failed to create high latency alarm: $alarm_name"
        return 1
    fi
}

# Function to create all CloudWatch alarms
create_cloudwatch_alarms() {
    local sns_topic_arn="$1"
    local account_id="$2"
    local region="$3"
    
    log_info "Creating CloudWatch alarms for Bedrock monitoring"
    log_info "SNS Topic: $sns_topic_arn"
    log_info "Account: $account_id"
    log_info "Region: $region"
    
    local failed_alarms=0
    
    # Create all four required alarms
    if ! create_high_token_alarm "$sns_topic_arn" "$HIGH_TOKEN_THRESHOLD"; then
        ((failed_alarms++))
    fi
    
    if ! create_error_rate_alarm "$sns_topic_arn" "$ERROR_RATE_THRESHOLD"; then
        ((failed_alarms++))
    fi
    
    if ! create_invocation_spike_alarm "$sns_topic_arn" "$INVOCATION_THRESHOLD"; then
        ((failed_alarms++))
    fi
    
    if ! create_high_latency_alarm "$sns_topic_arn" "$HIGH_LATENCY_THRESHOLD"; then
        ((failed_alarms++))
    fi
    
    if [[ $failed_alarms -eq 0 ]]; then
        log_info "All CloudWatch alarms created/updated successfully"
        return 0
    else
        log_error "$failed_alarms alarm(s) failed to create"
        return 1
    fi
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
    if ! aws cloudwatch list-metrics --namespace AWS/Bedrock >/dev/null 2>&1; then
        log_warn "Unable to list CloudWatch metrics. Alarms will be created but may not function until Bedrock logging is enabled."
    fi
    
    # Check SNS permissions
    if ! aws sns list-topics >/dev/null 2>&1; then
        log_error "Unable to access SNS topics. Please check IAM permissions for SNS operations."
        exit 1
    fi
    
    log_info "Prerequisites validated successfully"
}

# Function to display subscription instructions
display_subscription_instructions() {
    local sns_topic_arn="$1"
    
    echo
    echo "=== Email Subscription Setup ==="
    echo "To receive alarm notifications via email, subscribe to the SNS topic:"
    echo
    echo "Command:"
    echo "  aws sns subscribe \\"
    echo "    --topic-arn $sns_topic_arn \\"
    echo "    --protocol email \\"
    echo "    --notification-endpoint YOUR_EMAIL@example.com"
    echo
    echo "After running the command:"
    echo "1. Check your email for a confirmation message"
    echo "2. Click the confirmation link to activate notifications"
    echo "3. You'll receive alerts when any alarm threshold is breached"
    echo "================================"
}

# Function to display alarm summary
display_alarm_summary() {
    local sns_topic_arn="$1"
    
    echo
    echo "=== CloudWatch Alarms Configuration ==="
    echo "SNS Topic: $sns_topic_arn"
    echo
    echo "Alarms Created:"
    echo "  1. 🔥 High Input Token Usage"
    echo "     • Threshold: $HIGH_TOKEN_THRESHOLD tokens/hour"
    echo "     • Purpose: Cost monitoring and usage tracking"
    echo
    echo "  2. ⚠️  High Error Rate"
    echo "     • Threshold: $ERROR_RATE_THRESHOLD errors/5min"
    echo "     • Purpose: API reliability monitoring"
    echo
    echo "  3. 📈 Unusual Invocation Spike"
    echo "     • Threshold: $INVOCATION_THRESHOLD invocations/hour"
    echo "     • Purpose: Activity anomaly detection"
    echo
    echo "  4. 🐌 High Latency"
    echo "     • Threshold: $HIGH_LATENCY_THRESHOLD ms average"
    echo "     • Purpose: Performance monitoring"
    echo
    echo "All alarms will:"
    echo "  • Send notifications when thresholds are breached"
    echo "  • Send OK notifications when returning to normal"
    echo "  • Treat missing data as not breaching (normal)"
    echo "========================================"
}

# Main function
main() {
    log_info "Starting CloudWatch alarms setup for AWS Bedrock monitoring"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Get configuration
    local account_id region sns_topic_name
    account_id=$(get_account_id)
    region=$(get_region)
    sns_topic_name="${SNS_TOPIC_NAME:-$DEFAULT_SNS_TOPIC_NAME}"
    
    log_info "AWS Account ID: $account_id"
    log_info "AWS Region: $region"
    log_info "SNS Topic Name: $sns_topic_name"
    
    # Display threshold configuration
    log_info "Alarm Thresholds:"
    log_info "  High Token Usage: $HIGH_TOKEN_THRESHOLD tokens/hour"
    log_info "  Error Rate: $ERROR_RATE_THRESHOLD errors/5min"
    log_info "  Invocation Spike: $INVOCATION_THRESHOLD invocations/hour"
    log_info "  High Latency: $HIGH_LATENCY_THRESHOLD ms"
    
    # Create or get SNS topic
    local sns_topic_arn
    sns_topic_arn=$(get_or_create_sns_topic "$sns_topic_name" "$account_id" "$region")
    
    # Create CloudWatch alarms
    if ! create_cloudwatch_alarms "$sns_topic_arn" "$account_id" "$region"; then
        log_error "Some alarms failed to create. Check the output above for details."
        log_warn "Continuing with partial alarm setup..."
    fi
    
    # Display subscription instructions
    display_subscription_instructions "$sns_topic_arn"
    
    # Display alarm summary
    display_alarm_summary "$sns_topic_arn"
    
    log_info "CloudWatch alarms setup completed successfully!"
    
    # Export configuration for use by other scripts
    echo "export BEDROCK_SNS_TOPIC_ARN=\"$sns_topic_arn\"" > "${SCRIPT_DIR}/.alarms-config"
    echo "export BEDROCK_ALARMS_REGION=\"$region\"" >> "${SCRIPT_DIR}/.alarms-config"
    log_info "Alarms configuration saved to .alarms-config"
    
    echo
    echo "🎉 CloudWatch alarms are now monitoring your Bedrock usage!"
    echo "📧 Don't forget to subscribe your email to receive notifications"
    echo "🔧 Customize thresholds by setting environment variables before running this script"
    echo
    echo "Next steps:"
    echo "1. Subscribe your email to the SNS topic using the command above"
    echo "2. Make some Bedrock API calls to test the monitoring"
    echo "3. Use 6-usage-report.py to generate detailed usage reports"
    echo "4. Monitor your dashboard for real-time metrics"
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
        echo "  SNS_TOPIC_NAME           SNS topic name (default: bedrock-usage-alerts)"
        echo "  HIGH_TOKEN_THRESHOLD     High token usage threshold (default: 100000)"
        echo "  ERROR_RATE_THRESHOLD     Error rate threshold (default: 10)"
        echo "  INVOCATION_THRESHOLD     Invocation spike threshold (default: 1000)"
        echo "  HIGH_LATENCY_THRESHOLD   High latency threshold in ms (default: 10000)"
        echo
        echo "This script creates four CloudWatch alarms:"
        echo "  1. High Input Token Usage (>100k tokens/hour)"
        echo "  2. High Error Rate (>10 errors/5min)"
        echo "  3. Unusual Invocation Spike (>1000 invocations/hour)"
        echo "  4. High Latency (>10s average)"
        echo
        echo "All alarms send notifications via SNS topic."
        echo "Subscribe your email to receive alerts."
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
