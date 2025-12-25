# 🚀 AWS Bedrock Monitoring - Quick Launch Guide

**Ready-to-deploy AWS Bedrock monitoring system with comprehensive IAM permissions guide**

## ⚡ Quick Start (30 seconds)

```bash
# 1. Configure AWS credentials
aws configure

# 2. Deploy everything
cd aws-bedrock-monitoring
chmod +x *.sh
./0-setup-all.sh
```

## 🔐 Required AWS IAM Permissions

### **Minimum Required Policy for Deployment User/Role**

Create this IAM policy and attach it to your deployment user or role:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockMonitoringDeployment",
            "Effect": "Allow",
            "Action": [
                "bedrock:*",
                "cloudwatch:*",
                "logs:*",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:GetRole",
                "iam:ListRoles",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:GetRolePolicy",
                "iam:ListRolePolicies",
                "iam:PassRole",
                "s3:CreateBucket",
                "s3:DeleteBucket",
                "s3:GetBucketLocation",
                "s3:GetBucketVersioning",
                "s3:PutBucketVersioning",
                "s3:PutBucketLifecycleConfiguration",
                "s3:GetBucketLifecycleConfiguration",
                "s3:PutBucketPolicy",
                "s3:GetBucketPolicy",
                "s3:DeleteBucketPolicy",
                "s3:PutBucketPublicAccessBlock",
                "s3:GetBucketPublicAccessBlock",
                "s3:ListBucket",
                "s3:DeleteObject",
                "sns:CreateTopic",
                "sns:DeleteTopic",
                "sns:GetTopicAttributes",
                "sns:SetTopicAttributes",
                "sns:ListTopics",
                "sns:Subscribe",
                "sns:Unsubscribe",
                "sns:ListSubscriptions",
                "sns:ListSubscriptionsByTopic",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

### **Script-by-Script Permission Breakdown**

#### **1. Main Orchestration (`0-setup-all.sh`)**
```json
{
    "Action": [
        "sts:GetCallerIdentity"
    ],
    "Resource": "*"
}
```

#### **2. IAM Role Setup (`1-setup-iam-role.sh`)**
```json
{
    "Action": [
        "iam:CreateRole",
        "iam:GetRole",
        "iam:PutRolePolicy",
        "iam:AttachRolePolicy",
        "iam:ListRoles",
        "sts:GetCallerIdentity"
    ],
    "Resource": [
        "arn:aws:iam::*:role/BedrockCloudWatchLoggingRole",
        "arn:aws:iam::*:policy/*"
    ]
}
```

#### **3. S3 Bucket Setup (`2-create-s3-bucket.sh`)**
```json
{
    "Action": [
        "s3:CreateBucket",
        "s3:GetBucketLocation",
        "s3:PutBucketVersioning",
        "s3:GetBucketVersioning",
        "s3:PutBucketLifecycleConfiguration",
        "s3:GetBucketLifecycleConfiguration",
        "s3:PutBucketPolicy",
        "s3:PutBucketPublicAccessBlock",
        "sts:GetCallerIdentity"
    ],
    "Resource": [
        "arn:aws:s3:::bedrock-logs-*",
        "arn:aws:s3:::bedrock-logs-*/*"
    ]
}
```

#### **4. CloudWatch Log Group (`2b-create-log-group.sh`)**
```json
{
    "Action": [
        "logs:CreateLogGroup",
        "logs:DescribeLogGroups",
        "logs:PutRetentionPolicy",
        "logs:TagLogGroup"
    ],
    "Resource": [
        "arn:aws:logs:*:*:log-group:/aws/bedrock/modelinvocations",
        "arn:aws:logs:*:*:log-group:/aws/bedrock/modelinvocations:*"
    ]
}
```

#### **5. Bedrock Logging Config (`3-enable-bedrock-logging.sh`)**
```json
{
    "Action": [
        "bedrock:PutModelInvocationLoggingConfiguration",
        "bedrock:GetModelInvocationLoggingConfiguration",
        "bedrock:DeleteModelInvocationLoggingConfiguration",
        "iam:GetRole",
        "iam:PassRole"
    ],
    "Resource": [
        "*",
        "arn:aws:iam::*:role/BedrockCloudWatchLoggingRole"
    ]
}
```

#### **6. CloudWatch Dashboard (`4-create-cloudwatch-dashboard.sh`)**
```json
{
    "Action": [
        "cloudwatch:PutDashboard",
        "cloudwatch:GetDashboard",
        "cloudwatch:ListDashboards",
        "cloudwatch:DeleteDashboards"
    ],
    "Resource": [
        "arn:aws:cloudwatch::*:dashboard/BedrockUsageMonitoring"
    ]
}
```

#### **7. CloudWatch Alarms (`5-create-cloudwatch-alarms.sh`)**
```json
{
    "Action": [
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:DeleteAlarms",
        "sns:CreateTopic",
        "sns:GetTopicAttributes",
        "sns:SetTopicAttributes",
        "sns:ListTopics"
    ],
    "Resource": [
        "arn:aws:cloudwatch:*:*:alarm:Bedrock-*",
        "arn:aws:sns:*:*:bedrock-usage-alerts"
    ]
}
```

#### **8. Usage Reports (`6-usage-report.py`)**
```json
{
    "Action": [
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "logs:FilterLogEvents",
        "logs:DescribeLogGroups",
        "bedrock:GetModelInvocationLoggingConfiguration"
    ],
    "Resource": "*"
}
```

#### **9. Cleanup Script (`7-cleanup-resources.sh`)**
```json
{
    "Action": [
        "cloudwatch:DeleteDashboards",
        "cloudwatch:DeleteAlarms",
        "sns:DeleteTopic",
        "sns:ListTopics",
        "bedrock:DeleteModelInvocationLoggingConfiguration",
        "logs:DeleteLogGroup",
        "s3:DeleteBucket",
        "s3:ListBucket",
        "s3:DeleteObject",
        "iam:DeleteRole",
        "iam:DeleteRolePolicy",
        "iam:DetachRolePolicy",
        "iam:ListRolePolicies"
    ],
    "Resource": "*"
}
```

## 🏢 Enterprise/Organization Setup

### **Option 1: Create Dedicated IAM User**

```bash
# Create deployment user
aws iam create-user --user-name bedrock-monitoring-deployer

# Attach policy (replace POLICY_ARN with your policy ARN)
aws iam attach-user-policy \
  --user-name bedrock-monitoring-deployer \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/BedrockMonitoringDeploymentPolicy

# Create access keys
aws iam create-access-key --user-name bedrock-monitoring-deployer
```

### **Option 2: Create Dedicated IAM Role (for Cross-Account)**

```bash
# Create role with trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::TRUSTED_ACCOUNT_ID:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name BedrockMonitoringDeploymentRole \
  --assume-role-policy-document file://trust-policy.json

# Attach policy
aws iam attach-role-policy \
  --role-name BedrockMonitoringDeploymentRole \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/BedrockMonitoringDeploymentPolicy
```

### **Option 3: Use Existing Admin Role (Quick Start)**

If you have admin access, you can deploy immediately:

```bash
# Verify admin access
aws sts get-caller-identity

# Deploy directly
./0-setup-all.sh
```

## 🔒 Security Best Practices

### **Principle of Least Privilege**

The provided policy follows least privilege principles:
- ✅ **Resource-specific permissions** where possible
- ✅ **Action-specific permissions** (no wildcards except where necessary)
- ✅ **Account-scoped resources** (prevents cross-account access)
- ✅ **Service-specific permissions** (only required AWS services)

### **Temporary Access Pattern**

For enhanced security, use temporary credentials:

```bash
# Assume deployment role
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/BedrockMonitoringDeploymentRole \
  --role-session-name bedrock-monitoring-deployment

# Export temporary credentials
export AWS_ACCESS_KEY_ID=<temporary-access-key>
export AWS_SECRET_ACCESS_KEY=<temporary-secret-key>
export AWS_SESSION_TOKEN=<temporary-session-token>

# Deploy with temporary credentials
./0-setup-all.sh
```

### **Audit and Compliance**

The deployment creates these resources (for compliance tracking):

| Resource Type | Resource Name | Purpose |
|---------------|---------------|---------|
| IAM Role | `BedrockCloudWatchLoggingRole` | Bedrock logging permissions |
| S3 Bucket | `bedrock-logs-{ACCOUNT_ID}` | Log storage and archival |
| CloudWatch Log Group | `/aws/bedrock/modelinvocations` | Real-time log access |
| CloudWatch Dashboard | `BedrockUsageMonitoring` | Metrics visualization |
| CloudWatch Alarms | `Bedrock-*` (4 alarms) | Automated monitoring |
| SNS Topic | `bedrock-usage-alerts` | Alert notifications |

## 🚨 Common Permission Issues & Solutions

### **Issue 1: "Access Denied" during IAM role creation**
```bash
# Error: User is not authorized to perform: iam:CreateRole
# Solution: Add IAM permissions to your user/role
aws iam attach-user-policy --user-name YOUR_USER --policy-arn arn:aws:iam::aws:policy/IAMFullAccess
```

### **Issue 2: "Access Denied" during S3 bucket creation**
```bash
# Error: Access Denied when creating S3 bucket
# Solution: Ensure S3 permissions and unique bucket naming
export BUCKET_PREFIX="bedrock-logs-$(date +%s)"  # Add timestamp for uniqueness
```

### **Issue 3: "Access Denied" for Bedrock operations**
```bash
# Error: User is not authorized to perform: bedrock:PutModelInvocationLoggingConfiguration
# Solution: Ensure Bedrock permissions are included
aws iam attach-user-policy --user-name YOUR_USER --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

### **Issue 4: Cross-region resource conflicts**
```bash
# Error: Resources created in wrong region
# Solution: Set consistent AWS region
export AWS_DEFAULT_REGION=us-east-1
aws configure set region us-east-1
```

## 🎯 Deployment Validation

After deployment, validate permissions are working:

```bash
# Test 1: Verify IAM role exists
aws iam get-role --role-name BedrockCloudWatchLoggingRole

# Test 2: Verify S3 bucket exists
aws s3 ls | grep bedrock-logs

# Test 3: Verify CloudWatch log group
aws logs describe-log-groups --log-group-name-prefix /aws/bedrock

# Test 4: Verify Bedrock logging is enabled
aws bedrock get-model-invocation-logging-configuration

# Test 5: Verify dashboard exists
aws cloudwatch list-dashboards | grep BedrockUsageMonitoring

# Test 6: Verify alarms exist
aws cloudwatch describe-alarms --alarm-name-prefix Bedrock-

# Test 7: Generate usage report
python3 6-usage-report.py 1
```

## 📞 Support & Troubleshooting

### **Permission Debugging**

Enable AWS CLI debug mode:
```bash
export AWS_CLI_FILE_ENCODING=UTF-8
aws configure set cli_follow_redirects false
aws --debug sts get-caller-identity
```

### **Policy Simulator**

Test permissions before deployment:
```bash
# Use AWS Policy Simulator
# https://policysim.aws.amazon.com/
```

### **CloudTrail Monitoring**

Monitor API calls during deployment:
```bash
# View recent API calls
aws logs filter-log-events \
  --log-group-name CloudTrail/BedrockMonitoringDeployment \
  --start-time $(date -d '1 hour ago' +%s)000
```

---

## 🎉 Ready to Deploy!

With the proper IAM permissions configured, you can now deploy the complete AWS Bedrock monitoring system:

```bash
cd aws-bedrock-monitoring
./0-setup-all.sh
```

The system will create comprehensive monitoring for your Bedrock usage with real-time dashboards, automated alerts, and detailed cost analysis.