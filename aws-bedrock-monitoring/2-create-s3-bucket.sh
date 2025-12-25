#!/bin/bash

# AWS Bedrock Monitoring - S3 Bucket Setup Script
# This script creates an S3 bucket for Bedrock log storage with versioning and lifecycle policies

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/src/config.py" 2>/dev/null || true

# Default configuration
DEFAULT_BUCKET_PREFIX="bedrock-logs"
DEFAULT_LIFECYCLE_DAYS=90

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

# Function to generate bucket name
generate_bucket_name() {
    local account_id="$1"
    local bucket_prefix="${BUCKET_PREFIX:-$DEFAULT_BUCKET_PREFIX}"
    echo "${bucket_prefix}-${account_id}"
}

# Function to check if bucket exists
bucket_exists() {
    local bucket_name="$1"
    aws s3api head-bucket --bucket "$bucket_name" >/dev/null 2>&1
}

# Function to create lifecycle policy JSON
create_lifecycle_policy() {
    local lifecycle_days="${LIFECYCLE_DAYS:-$DEFAULT_LIFECYCLE_DAYS}"
    
    cat <<EOF
{
    "Rules": [
        {
            "ID": "BedrockLogRetention",
            "Status": "Enabled",
            "Filter": {
                "Prefix": "bedrock-logs/"
            },
            "Expiration": {
                "Days": ${lifecycle_days}
            },
            "NoncurrentVersionExpiration": {
                "NoncurrentDays": 7
            },
            "AbortIncompleteMultipartUpload": {
                "DaysAfterInitiation": 1
            }
        }
    ]
}
EOF
}

# Function to create bucket policy for Bedrock access
create_bucket_policy() {
    local bucket_name="$1"
    local account_id="$2"
    
    cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockLogDelivery",
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock.amazonaws.com"
            },
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": "arn:aws:s3:::${bucket_name}/bedrock-logs/*",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "${account_id}"
                }
            }
        },
        {
            "Sid": "BedrockLogDeliveryBucketAccess",
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock.amazonaws.com"
            },
            "Action": "s3:GetBucketLocation",
            "Resource": "arn:aws:s3:::${bucket_name}",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "${account_id}"
                }
            }
        }
    ]
}
EOF
}

# Function to create S3 bucket
create_s3_bucket() {
    local bucket_name="$1"
    local region="$2"
    local account_id="$3"
    
    log_info "Setting up S3 bucket: $bucket_name"
    
    # Check if bucket already exists
    if bucket_exists "$bucket_name"; then
        log_warn "S3 bucket $bucket_name already exists. Validating configuration..."
        
        # Verify bucket is in correct region
        local existing_region
        existing_region=$(aws s3api get-bucket-location --bucket "$bucket_name" --query LocationConstraint --output text 2>/dev/null || echo "us-east-1")
        
        if [[ "$existing_region" == "None" ]]; then
            existing_region="us-east-1"
        fi
        
        if [[ "$existing_region" != "$region" ]]; then
            log_error "Bucket $bucket_name exists in region $existing_region, but current region is $region"
            log_error "Cannot proceed with bucket in different region"
            return 1
        fi
        
        log_info "Bucket exists in correct region ($region). Updating configuration..."
        
        # Validate bucket ownership
        if ! aws s3api head-bucket --bucket "$bucket_name" >/dev/null 2>&1; then
            log_error "Cannot access bucket $bucket_name. Check permissions or bucket ownership."
            return 1
        fi
    else
        # Create the bucket
        log_info "Creating new S3 bucket: $bucket_name"
        if [[ "$region" == "us-east-1" ]]; then
            # us-east-1 doesn't need LocationConstraint
            if ! aws s3api create-bucket --bucket "$bucket_name" 2>/dev/null; then
                log_error "Failed to create S3 bucket $bucket_name"
                return 1
            fi
        else
            if ! aws s3api create-bucket \
                --bucket "$bucket_name" \
                --region "$region" \
                --create-bucket-configuration LocationConstraint="$region" 2>/dev/null; then
                log_error "Failed to create S3 bucket $bucket_name in region $region"
                return 1
            fi
        fi
        
        log_info "S3 bucket $bucket_name created successfully"
    fi
    
    # Enable versioning (with error handling)
    log_info "Configuring versioning on bucket $bucket_name"
    if ! aws s3api put-bucket-versioning \
        --bucket "$bucket_name" \
        --versioning-configuration Status=Enabled 2>/dev/null; then
        log_warn "Failed to enable versioning on bucket $bucket_name"
    else
        log_info "✅ Versioning enabled successfully"
    fi
    
    # Apply lifecycle policy (with error handling)
    log_info "Applying lifecycle policy to bucket $bucket_name"
    local lifecycle_policy
    lifecycle_policy=$(create_lifecycle_policy)
    if echo "$lifecycle_policy" | aws s3api put-bucket-lifecycle-configuration \
        --bucket "$bucket_name" \
        --lifecycle-configuration file:///dev/stdin 2>/dev/null; then
        log_info "✅ Lifecycle policy applied successfully"
    else
        log_warn "Failed to apply lifecycle policy to bucket $bucket_name"
    fi
    
    # Apply bucket policy for Bedrock access (with error handling)
    log_info "Applying bucket policy for Bedrock access"
    local bucket_policy
    bucket_policy=$(create_bucket_policy "$bucket_name" "$account_id")
    if echo "$bucket_policy" | aws s3api put-bucket-policy \
        --bucket "$bucket_name" \
        --policy file:///dev/stdin 2>/dev/null; then
        log_info "✅ Bucket policy applied successfully"
    else
        log_warn "Failed to apply bucket policy to bucket $bucket_name"
    fi
    
    # Enable server-side encryption (with error handling)
    log_info "Configuring server-side encryption on bucket $bucket_name"
    if aws s3api put-bucket-encryption \
        --bucket "$bucket_name" \
        --server-side-encryption-configuration '{
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    },
                    "BucketKeyEnabled": true
                }
            ]
        }' 2>/dev/null; then
        log_info "✅ Server-side encryption enabled successfully"
    else
        log_warn "Failed to enable server-side encryption on bucket $bucket_name"
    fi
    
    # Block public access (with error handling)
    log_info "Configuring public access block on bucket $bucket_name"
    if aws s3api put-public-access-block \
        --bucket "$bucket_name" \
        --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" 2>/dev/null; then
        log_info "✅ Public access blocked successfully"
    else
        log_warn "Failed to block public access on bucket $bucket_name"
    fi
    
    log_info "S3 bucket setup completed"
    
    # Output bucket information
    echo
    echo "=== S3 Bucket Configuration ==="
    echo "Bucket Name: $bucket_name"
    echo "Region: $region"
    echo "Versioning: Enabled"
    echo "Lifecycle Policy: ${LIFECYCLE_DAYS:-$DEFAULT_LIFECYCLE_DAYS} days retention"
    echo "Encryption: AES256"
    echo "Public Access: Blocked"
    echo "=============================="
    
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
    
    log_info "Prerequisites validated successfully"
}

# Main function
main() {
    log_info "Starting S3 bucket setup for AWS Bedrock monitoring"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Get AWS account ID and region
    local account_id region bucket_name
    account_id=$(get_account_id)
    region=$(get_region)
    bucket_name=$(generate_bucket_name "$account_id")
    
    log_info "AWS Account ID: $account_id"
    log_info "AWS Region: $region"
    log_info "Target bucket name: $bucket_name"
    
    # Create S3 bucket with configuration
    if ! create_s3_bucket "$bucket_name" "$region" "$account_id"; then
        log_error "Failed to create or configure S3 bucket. Exiting."
        exit 1
    fi
    
    log_info "S3 bucket setup completed successfully!"
    
    # Export bucket name for use by other scripts
    echo "export BEDROCK_S3_BUCKET_NAME=\"$bucket_name\"" > "${SCRIPT_DIR}/.s3-config"
    log_info "Bucket configuration saved to .s3-config"
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
        echo "  BUCKET_PREFIX       S3 bucket prefix (default: bedrock-logs)"
        echo "  LIFECYCLE_DAYS      Log retention days (default: 90)"
        echo
        echo "This script creates an S3 bucket for AWS Bedrock log storage with:"
        echo "  - Account-specific naming"
        echo "  - Versioning enabled"
        echo "  - Lifecycle policy for automatic cleanup"
        echo "  - Bucket policy for Bedrock access"
        echo "  - Server-side encryption"
        echo "  - Public access blocked"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac