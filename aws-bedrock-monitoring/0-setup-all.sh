#!/bin/bash

# AWS Bedrock Monitoring - Main Setup Orchestration Script
# This script runs all setup steps in the correct sequence with dependency checking and error recovery
# Implements Requirements 7.1: Command-line interface and automation

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# Function to print banner
print_banner() {
    echo
    echo "=========================================="
    echo "  AWS Bedrock Monitoring Setup"
    echo "  Complete Infrastructure Deployment"
    echo "=========================================="
    echo
}

# Function to validate prerequisites
validate_prerequisites() {
    log_step "Validating prerequisites..."
    
    local missing_tools=()
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws-cli")
    fi
    
    # Check if jq is installed (needed for JSON parsing)
    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again."
        exit 1
    fi
    
    # Check if AWS credentials are configured
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Get AWS account info
    local account_id region
    account_id=$(aws sts get-caller-identity --query Account --output text)
    region=$(aws configure get region 2>/dev/null || echo "us-east-1")
    
    log_info "✅ Prerequisites validated"
    log_info "AWS Account ID: $account_id"
    log_info "AWS Region: $region"
    
    return 0
}

# Function to check if a script exists and is executable
check_script() {
    local script_path="$1"
    
    if [[ ! -f "$script_path" ]]; then
        log_error "Script not found: $script_path"
        return 1
    fi
    
    if [[ ! -x "$script_path" ]]; then
        log_warn "Script not executable, making executable: $script_path"
        chmod +x "$script_path"
    fi
    
    return 0
}

# Function to run a setup step with error handling
run_setup_step() {
    local step_number="$1"
    local step_name="$2"
    local script_path="$3"
    local description="$4"
    
    log_step "Step $step_number: $step_name"
    log_info "$description"
    
    # Check if script exists
    if ! check_script "$script_path"; then
        log_error "Cannot proceed with step $step_number"
        return 1
    fi
    
    # Run the script
    log_info "Executing: $script_path"
    
    if "$script_path"; then
        log_info "✅ Step $step_number completed successfully"
        return 0
    else
        local exit_code=$?
        log_error "❌ Step $step_number failed with exit code $exit_code"
        return $exit_code
    fi
}

# Function to handle step failure with recovery options
handle_step_failure() {
    local step_number="$1"
    local step_name="$2"
    local script_path="$3"
    
    log_error "Step $step_number ($step_name) failed"
    
    if [[ "${INTERACTIVE:-true}" == "true" ]]; then
        echo
        echo "Recovery options:"
        echo "1. Retry this step"
        echo "2. Skip this step and continue"
        echo "3. Abort setup"
        echo
        read -p "Choose an option (1-3): " choice
        
        case $choice in
            1)
                log_info "Retrying step $step_number..."
                return 0  # Retry
                ;;
            2)
                log_warn "Skipping step $step_number..."
                return 1  # Skip
                ;;
            3|*)
                log_error "Setup aborted by user"
                exit 1
                ;;
        esac
    else
        # Non-interactive mode - fail fast
        log_error "Setup failed at step $step_number. Run with --interactive for recovery options."
        exit 1
    fi
}

# Function to run setup step with retry logic
run_step_with_retry() {
    local step_number="$1"
    local step_name="$2"
    local script_path="$3"
    local description="$4"
    local max_retries=2
    local retry_count=0
    
    while [[ $retry_count -le $max_retries ]]; do
        if run_setup_step "$step_number" "$step_name" "$script_path" "$description"; then
            return 0  # Success
        else
            if [[ $retry_count -lt $max_retries ]]; then
                if handle_step_failure "$step_number" "$step_name" "$script_path"; then
                    ((retry_count++))
                    log_info "Retry attempt $retry_count of $max_retries"
                    continue
                else
                    log_warn "Skipping step $step_number"
                    return 1  # Skip
                fi
            else
                log_error "Step $step_number failed after $max_retries retries"
                if [[ "${INTERACTIVE:-true}" == "true" ]]; then
                    handle_step_failure "$step_number" "$step_name" "$script_path"
                    return 1  # Skip after user choice
                else
                    exit 1  # Fail in non-interactive mode
                fi
            fi
        fi
    done
}

# Function to display setup summary
display_setup_summary() {
    local failed_steps=("$@")
    
    echo
    echo "=========================================="
    echo "  Setup Summary"
    echo "=========================================="
    
    if [[ ${#failed_steps[@]} -eq 0 ]]; then
        log_info "🎉 All setup steps completed successfully!"
        echo
        echo "Your AWS Bedrock monitoring system is now ready:"
        echo "  ✅ IAM role configured with minimal permissions"
        echo "  ✅ S3 bucket created with lifecycle policies"
        echo "  ✅ CloudWatch log group configured"
        echo "  ✅ Bedrock logging enabled"
        echo "  ✅ CloudWatch dashboard created"
        echo "  ✅ CloudWatch alarms configured"
        echo
        echo "Next steps:"
        echo "1. Subscribe to SNS notifications for alerts"
        echo "2. Make some Bedrock API calls to generate data"
        echo "3. View your dashboard and run usage reports"
    else
        log_warn "⚠️  Setup completed with ${#failed_steps[@]} failed/skipped step(s):"
        for step in "${failed_steps[@]}"; do
            log_warn "  - $step"
        done
        echo
        echo "You can re-run individual scripts to complete the failed steps:"
        for step in "${failed_steps[@]}"; do
            echo "  $step"
        done
    fi
    
    echo "=========================================="
}

# Function to display usage information
display_usage() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --help, -h          Show this help message"
    echo "  --interactive       Enable interactive mode with recovery options (default)"
    echo "  --non-interactive   Disable interactive mode, fail fast on errors"
    echo "  --skip-validation   Skip prerequisite validation"
    echo
    echo "Environment Variables:"
    echo "  All environment variables from individual scripts are supported"
    echo
    echo "This script runs the complete Bedrock monitoring setup:"
    echo "  1. IAM role setup (1-setup-iam-role.sh)"
    echo "  2. S3 bucket creation (2-create-s3-bucket.sh)"
    echo "  3. CloudWatch log group setup (2b-create-log-group.sh)"
    echo "  4. Bedrock logging configuration (3-enable-bedrock-logging.sh)"
    echo "  5. CloudWatch dashboard creation (4-create-cloudwatch-dashboard.sh)"
    echo "  6. CloudWatch alarms setup (5-create-cloudwatch-alarms.sh)"
    echo
    echo "Each step handles existing resources gracefully and can be run independently."
}

# Main setup function
main() {
    local skip_validation=false
    local failed_steps=()
    
    print_banner
    
    # Validate prerequisites unless skipped
    if [[ "$skip_validation" != "true" ]]; then
        if ! validate_prerequisites; then
            log_error "Prerequisites validation failed. Exiting."
            exit 1
        fi
    fi
    
    log_info "Starting complete AWS Bedrock monitoring setup..."
    echo
    
    # Step 1: IAM Role Setup
    if ! run_step_with_retry "1" "IAM Role Setup" \
        "${SCRIPT_DIR}/1-setup-iam-role.sh" \
        "Creating IAM role with minimal permissions for Bedrock logging"; then
        failed_steps+=("Step 1: IAM Role Setup (${SCRIPT_DIR}/1-setup-iam-role.sh)")
    fi
    
    echo
    
    # Step 2: S3 Bucket Creation
    if ! run_step_with_retry "2" "S3 Bucket Creation" \
        "${SCRIPT_DIR}/2-create-s3-bucket.sh" \
        "Creating S3 bucket for log storage with lifecycle policies"; then
        failed_steps+=("Step 2: S3 Bucket Creation (${SCRIPT_DIR}/2-create-s3-bucket.sh)")
    fi
    
    echo
    
    # Step 3: CloudWatch Log Group Setup
    if ! run_step_with_retry "3" "CloudWatch Log Group Setup" \
        "${SCRIPT_DIR}/2b-create-log-group.sh" \
        "Creating CloudWatch log group with retention policy"; then
        failed_steps+=("Step 3: CloudWatch Log Group Setup (${SCRIPT_DIR}/2b-create-log-group.sh)")
    fi
    
    echo
    
    # Step 4: Bedrock Logging Configuration
    if ! run_step_with_retry "4" "Bedrock Logging Configuration" \
        "${SCRIPT_DIR}/3-enable-bedrock-logging.sh" \
        "Enabling Bedrock model invocation logging with dual destinations"; then
        failed_steps+=("Step 4: Bedrock Logging Configuration (${SCRIPT_DIR}/3-enable-bedrock-logging.sh)")
    fi
    
    echo
    
    # Step 5: CloudWatch Dashboard Creation
    if ! run_step_with_retry "5" "CloudWatch Dashboard Creation" \
        "${SCRIPT_DIR}/4-create-cloudwatch-dashboard.sh" \
        "Creating comprehensive monitoring dashboard with all required widgets"; then
        failed_steps+=("Step 5: CloudWatch Dashboard Creation (${SCRIPT_DIR}/4-create-cloudwatch-dashboard.sh)")
    fi
    
    echo
    
    # Step 6: CloudWatch Alarms Setup
    if ! run_step_with_retry "6" "CloudWatch Alarms Setup" \
        "${SCRIPT_DIR}/5-create-cloudwatch-alarms.sh" \
        "Creating monitoring alarms with SNS notifications"; then
        failed_steps+=("Step 6: CloudWatch Alarms Setup (${SCRIPT_DIR}/5-create-cloudwatch-alarms.sh)")
    fi
    
    # Display final summary
    display_setup_summary "${failed_steps[@]}"
    
    # Exit with appropriate code
    if [[ ${#failed_steps[@]} -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        display_usage
        exit 0
        ;;
    --non-interactive)
        export INTERACTIVE=false
        shift
        main "$@"
        ;;
    --interactive)
        export INTERACTIVE=true
        shift
        main "$@"
        ;;
    --skip-validation)
        skip_validation=true
        shift
        main "$@"
        ;;
    *)
        # Default to interactive mode
        export INTERACTIVE=true
        main "$@"
        ;;
esac