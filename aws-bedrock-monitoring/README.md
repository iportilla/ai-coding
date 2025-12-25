# AWS Bedrock Usage Monitoring Setup

Complete setup for monitoring AWS Bedrock usage, including CloudWatch logging, dashboards, alarms, and cost tracking. This system provides comprehensive observability for Bedrock API usage with automated setup and real-time monitoring.

## 📋 Prerequisites

- **AWS CLI** configured with credentials (`aws configure`)
- **jq** for JSON parsing (`brew install jq` or `apt-get install jq`)
- **Python 3.x** with boto3 for usage reports (`pip install boto3`)
- **IAM Permissions**: bedrock:*, cloudwatch:*, logs:*, iam:*, s3:*, sns:*

## 🚀 Quick Start

### Option 1: Complete Setup (Recommended)

Run the orchestration script for automated setup with error recovery:

```bash
# Make all scripts executable and run complete setup
chmod +x *.sh
./0-setup-all.sh
```

The orchestration script will:
- ✅ Validate prerequisites and AWS configuration
- ✅ Run all setup steps in the correct sequence
- ✅ Handle existing resources gracefully
- ✅ Provide interactive error recovery options
- ✅ Display comprehensive setup summary

### Option 2: Manual Step-by-Step Setup

Run individual scripts in order:

```bash
# 1. Create IAM role for Bedrock logging
./1-setup-iam-role.sh

# 2. Create S3 bucket for large logs
./2-create-s3-bucket.sh

# 3. Create CloudWatch log group
./2b-create-log-group.sh

# 4. Enable Bedrock CloudWatch logging
./3-enable-bedrock-logging.sh

# 5. Create CloudWatch dashboard
./4-create-cloudwatch-dashboard.sh

# 6. Set up CloudWatch alarms
./5-create-cloudwatch-alarms.sh

# 7. Generate usage report
python3 6-usage-report.py 24  # Last 24 hours
```

### Option 3: Non-Interactive Setup

For CI/CD or automated deployments:

```bash
./0-setup-all.sh --non-interactive
```

## 📊 What Gets Set Up

### 1. IAM Role (`1-setup-iam-role.sh`)
Creates `BedrockCloudWatchLoggingRole` with minimal permissions:
- **CloudWatch Logs**: CreateLogGroup, CreateLogStream, PutLogEvents
- **S3 Access**: PutObject to account-specific bucket
- **Security**: Account-specific resource ARNs and Bedrock service trust policy

### 2. S3 Bucket (`2-create-s3-bucket.sh`)
Creates `bedrock-logs-{ACCOUNT_ID}` bucket with:
- **Versioning**: Enabled for data protection
- **Lifecycle Policy**: Automatic deletion after 90 days
- **Encryption**: AES256 server-side encryption
- **Access Control**: Bedrock service access only, public access blocked

### 3. CloudWatch Log Group (`2b-create-log-group.sh`)
Creates `/aws/bedrock/modelinvocations` log group with:
- **Retention**: 30-day default (configurable)
- **Tagging**: Purpose and component identification
- **Permissions**: Integrated with IAM role

### 4. Bedrock Logging Configuration (`3-enable-bedrock-logging.sh`)
Enables comprehensive logging with:
- **Dual Destinations**: CloudWatch Logs + S3 bucket
- **Text Data Delivery**: Full request/response logging
- **Configuration Validation**: Existing setup detection and updates
- **Verification**: Post-setup configuration validation

### 5. CloudWatch Dashboard (`4-create-cloudwatch-dashboard.sh`)
Creates `BedrockUsageMonitoring` dashboard with:
- **Invocation Metrics**: Total calls by model type over time
- **Token Usage**: Separate input/output token tracking
- **Latency Metrics**: Average and 99th percentile response times
- **Error Tracking**: Client and server error monitoring
- **Log Viewer**: Recent invocations with key metrics

### 6. CloudWatch Alarms (`5-create-cloudwatch-alarms.sh`)
Sets up 4 critical monitoring alarms:
- **High Token Usage**: >100k input tokens/hour (cost monitoring)
- **High Error Rate**: >10 errors/5min (reliability monitoring)
- **Invocation Spike**: >1000 calls/hour (anomaly detection)
- **High Latency**: >10s average (performance monitoring)
- **SNS Integration**: Email notifications for all alarm states

### 7. Usage Report Script (`6-usage-report.py`)
Comprehensive Python reporting tool:
- **Usage Analytics**: Total invocations and token consumption
- **Model Breakdown**: Usage by model (Sonnet, Opus, Haiku)
- **Cost Analysis**: Real-time cost estimates with current pricing
- **Projections**: Monthly usage and cost forecasting
- **Performance**: Latency statistics and error analysis
- **CLI Interface**: Configurable time periods and output formats

### 8. Cleanup Script (`7-cleanup-resources.sh`)
Complete resource removal tool:
- **Safe Cleanup**: Confirmation prompts and resource validation
- **Comprehensive**: Removes all created AWS resources
- **Selective**: Option to preserve specific components
- **Verification**: Post-cleanup validation

## 📈 Viewing Your Data

### AWS Console

**CloudWatch Dashboard:**
```
https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#dashboards:name=BedrockUsageMonitoring
```

**CloudWatch Logs:**
```
https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#logsV2:log-groups/log-group/$252Faws$252Fbedrock$252Fmodelinvocations
```

**CloudWatch Alarms:**
```
https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#alarmsV2:
```

**Cost Explorer:**
```
https://console.aws.amazon.com/cost-management/home#/custom
```
Filter by Service: "Amazon Bedrock"

### Command Line

**View current metrics:**
```bash
# Get your account ID and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Last 24 hours input tokens
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name InputTokenCount \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum

# Last 24 hours invocations by model
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=ModelId,Value=anthropic.claude-3-sonnet-20240229-v1:0 \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Check current logging configuration
aws bedrock get-model-invocation-logging-configuration
```

**View recent logs:**
```bash
# Tail logs in real-time
aws logs tail /aws/bedrock/modelinvocations --follow

# Get recent log events
aws logs filter-log-events \
  --log-group-name /aws/bedrock/modelinvocations \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Generate usage reports:**
```bash
# Last 24 hours
python3 6-usage-report.py 24

# Last 7 days with detailed breakdown
python3 6-usage-report.py 168

# Last 30 days
python3 6-usage-report.py 720

# Custom time period (in hours)
python3 6-usage-report.py 48  # Last 2 days
```

## 🔍 CloudWatch Logs Insights Queries

Query your Bedrock logs directly in the AWS Console or via CLI:

**Total tokens by model (last 24h):**
```sql
fields @timestamp, modelId, inputTokenCount, outputTokenCount
| stats sum(inputTokenCount) as TotalInput,
        sum(outputTokenCount) as TotalOutput,
        count(*) as Invocations by modelId
| sort Invocations desc
```

**Most expensive requests:**
```sql
fields @timestamp, modelId, inputTokenCount, outputTokenCount,
       (inputTokenCount * 0.000003 + outputTokenCount * 0.000015) as estimatedCost
| sort estimatedCost desc
| limit 20
```

**Requests by hour:**
```sql
fields @timestamp, modelId
| stats count(*) as requests by bin(1h)
| sort @timestamp desc
```

**Average latency by model:**
```sql
fields @timestamp, modelId, invocationLatency
| filter ispresent(invocationLatency)
| stats avg(invocationLatency) as avgLatency by modelId
| sort avgLatency desc
```

**Error analysis:**
```sql
fields @timestamp, modelId, @message
| filter @message like /error/
| stats count() as errorCount by modelId
| sort errorCount desc
```

**Run queries via CLI:**
```bash
# Start a query
QUERY_ID=$(aws logs start-query \
  --log-group-name /aws/bedrock/modelinvocations \
  --start-time $(date -d '24 hours ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, modelId, inputTokenCount | stats sum(inputTokenCount) by modelId' \
  --query 'queryId' --output text)

# Get results
aws logs get-query-results --query-id $QUERY_ID
```

## 💰 Cost Tracking

### Current Pricing (as of December 2024)
- **Claude 3.5 Sonnet**: $3/MTok input, $15/MTok output
- **Claude 3 Opus**: $15/MTok input, $75/MTok output  
- **Claude 3 Haiku**: $0.25/MTok input, $1.25/MTok output
- **Claude Instant**: $0.80/MTok input, $2.40/MTok output

*Note: Pricing may change. Check [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) for current rates.*

### Monitor Costs
1. **Real-time Estimates**: Use `6-usage-report.py` for instant cost calculations
2. **CloudWatch Metrics**: Monitor token usage in real-time
3. **Cost Explorer**: View actual billing data (24-hour delay)
4. **Budget Alerts**: Set up proactive cost monitoring

### Set Up Budget Alerts

Create a budget configuration file:
```bash
# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create budget for Bedrock costs
cat > bedrock-budget.json << EOF
{
  "BudgetName": "BedrockUsageBudget",
  "BudgetLimit": {
    "Amount": "100.00",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST",
  "CostFilters": {
    "Service": ["Amazon Bedrock"]
  }
}
EOF

# Create budget
aws budgets create-budget \
  --account-id $ACCOUNT_ID \
  --budget file://bedrock-budget.json
```

### Cost Optimization Tips
- **Use Haiku for simple tasks**: 12x cheaper than Sonnet for input tokens
- **Optimize prompts**: Reduce unnecessary context and verbose instructions
- **Monitor token usage**: Set up alerts for unusual spikes
- **Batch requests**: Combine multiple queries when possible
- **Review usage patterns**: Use reports to identify optimization opportunities

## 🔔 Setting Up Email Alerts

Subscribe to SNS topic for alarm notifications:

```bash
# Get your SNS topic ARN (created during setup)
TOPIC_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'bedrock-usage-alerts')].TopicArn" --output text)

# Subscribe your email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com
```

**After subscribing:**
1. Check your email for a confirmation message
2. Click the confirmation link to activate notifications
3. You'll receive alerts for:
   - High token usage (cost monitoring)
   - Error spikes (reliability issues)
   - Unusual activity (anomaly detection)
   - Performance degradation (latency issues)

**Customize notification preferences:**
```bash
# List current subscriptions
aws sns list-subscriptions-by-topic --topic-arn $TOPIC_ARN

# Unsubscribe if needed
aws sns unsubscribe --subscription-arn <subscription-arn>
```

## 🛠️ Customization

### Environment Variables
All scripts support environment variables for customization:

```bash
# IAM and S3 Configuration
export IAM_ROLE_NAME="BedrockCloudWatchLoggingRole"
export BUCKET_PREFIX="bedrock-logs"
export LIFECYCLE_DAYS=90

# CloudWatch Configuration  
export LOG_GROUP_NAME="/aws/bedrock/modelinvocations"
export RETENTION_DAYS=30
export DASHBOARD_NAME="BedrockUsageMonitoring"

# Alarm Thresholds
export HIGH_TOKEN_THRESHOLD=100000      # tokens/hour
export ERROR_RATE_THRESHOLD=10          # errors/5min
export INVOCATION_THRESHOLD=1000        # invocations/hour
export HIGH_LATENCY_THRESHOLD=10000     # milliseconds

# SNS Configuration
export SNS_TOPIC_NAME="bedrock-usage-alerts"
```

### Adjust Alarm Thresholds
Customize thresholds before running the alarms script:

```bash
# Set custom thresholds
export HIGH_TOKEN_THRESHOLD=50000   # Lower threshold for tighter cost control
export ERROR_RATE_THRESHOLD=5       # More sensitive error detection
export INVOCATION_THRESHOLD=500     # Detect smaller usage spikes
export HIGH_LATENCY_THRESHOLD=5000  # 5-second latency threshold

# Run alarms setup with custom thresholds
./5-create-cloudwatch-alarms.sh
```

### Change Log Retention
```bash
# Update retention policy (valid values: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653)
aws logs put-retention-policy \
  --log-group-name /aws/bedrock/modelinvocations \
  --retention-in-days 90
```

### Modify Dashboard Widgets
Edit `4-create-cloudwatch-dashboard.sh` to:
- Add new model IDs to track
- Change time periods for widgets
- Add custom metrics or annotations
- Modify widget layouts and sizes

### Disable/Enable Logging
```bash
# Disable logging
aws bedrock delete-model-invocation-logging-configuration

# Re-enable logging (run the logging script)
./3-enable-bedrock-logging.sh

# Check current status
aws bedrock get-model-invocation-logging-configuration
```

## 🧹 Cleanup

### Complete Cleanup (Automated)

Use the cleanup script to remove all resources:

```bash
# Run cleanup script with confirmation prompts
./7-cleanup-resources.sh

# Non-interactive cleanup (use with caution)
./7-cleanup-resources.sh --force
```

### Manual Cleanup

If you prefer to remove resources manually:

```bash
# Get your account ID and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Delete dashboard
aws cloudwatch delete-dashboards --dashboard-names BedrockUsageMonitoring

# Delete alarms
aws cloudwatch delete-alarms \
  --alarm-names Bedrock-HighInputTokenUsage \
                Bedrock-HighErrorRate \
                Bedrock-UnusualInvocationSpike \
                Bedrock-HighLatency

# Delete SNS topic
TOPIC_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'bedrock-usage-alerts')].TopicArn" --output text)
aws sns delete-topic --topic-arn $TOPIC_ARN

# Disable logging
aws bedrock delete-model-invocation-logging-configuration

# Delete log group
aws logs delete-log-group --log-group-name /aws/bedrock/modelinvocations

# Delete S3 bucket (empty it first)
aws s3 rm s3://bedrock-logs-$ACCOUNT_ID --recursive
aws s3 rb s3://bedrock-logs-$ACCOUNT_ID

# Delete IAM role
aws iam delete-role-policy --role-name BedrockCloudWatchLoggingRole --policy-name BedrockCloudWatchLoggingPolicy
aws iam delete-role --role-name BedrockCloudWatchLoggingRole
```

### Selective Cleanup

Remove only specific components:

```bash
# Disable only logging (keep infrastructure)
aws bedrock delete-model-invocation-logging-configuration

# Remove only alarms (keep monitoring)
aws cloudwatch delete-alarms --alarm-names Bedrock-HighInputTokenUsage

# Delete only dashboard
aws cloudwatch delete-dashboards --dashboard-names BedrockUsageMonitoring
```

## 🆘 Troubleshooting

### Common Issues and Solutions

#### No Metrics Showing in Dashboard
**Symptoms**: Dashboard widgets show "No data available"

**Solutions**:
1. **Wait for data**: Metrics appear 5-15 minutes after first Bedrock usage
2. **Verify logging is enabled**:
   ```bash
   aws bedrock get-model-invocation-logging-configuration
   ```
3. **Check IAM role permissions**: Ensure role has CloudWatch write permissions
4. **Make test API calls**: Generate some Bedrock usage to populate metrics

#### Permission Errors During Setup
**Symptoms**: "Access Denied" or "Insufficient permissions" errors

**Solutions**:
1. **Check IAM permissions**: Ensure your user/role has required permissions:
   ```bash
   # Required permissions
   bedrock:*
   cloudwatch:*
   logs:*
   iam:CreateRole, iam:AttachRolePolicy, iam:GetRole
   s3:CreateBucket, s3:PutBucketPolicy
   sns:CreateTopic, sns:Subscribe
   ```
2. **Verify AWS CLI configuration**:
   ```bash
   aws sts get-caller-identity
   aws configure list
   ```
3. **Check region consistency**: Ensure all resources are in the same region

#### High Costs or Unexpected Charges
**Symptoms**: Higher than expected AWS bills

**Solutions**:
1. **Review usage patterns**:
   ```bash
   python3 6-usage-report.py 168  # Last 7 days
   ```
2. **Check for runaway processes**: Look for unusual invocation spikes in dashboard
3. **Optimize prompts**: Reduce token usage by improving prompt efficiency
4. **Set up budget alerts**: Monitor costs proactively
5. **Use cheaper models**: Switch to Haiku for simple tasks

#### Logging Configuration Issues
**Symptoms**: Logs not appearing in CloudWatch or S3

**Solutions**:
1. **Verify Bedrock logging status**:
   ```bash
   aws bedrock get-model-invocation-logging-configuration
   ```
2. **Check IAM role trust policy**: Ensure Bedrock service can assume the role
3. **Validate S3 bucket policy**: Confirm Bedrock has write permissions
4. **Test with simple API call**: Make a basic Bedrock request to generate logs

#### Dashboard or Alarms Not Working
**Symptoms**: Dashboard shows errors or alarms don't trigger

**Solutions**:
1. **Check CloudWatch permissions**: Ensure proper access to CloudWatch APIs
2. **Verify metric availability**: Confirm Bedrock metrics are being generated
3. **Review alarm configuration**: Check thresholds and evaluation periods
4. **Test SNS notifications**: Verify email subscription is confirmed

#### Script Execution Failures
**Symptoms**: Setup scripts fail with various errors

**Solutions**:
1. **Check prerequisites**:
   ```bash
   # Verify required tools
   aws --version
   jq --version
   python3 --version
   ```
2. **Make scripts executable**:
   ```bash
   chmod +x *.sh
   ```
3. **Run with verbose output**:
   ```bash
   bash -x ./1-setup-iam-role.sh
   ```
4. **Use interactive setup**:
   ```bash
   ./0-setup-all.sh --interactive
   ```

### Getting Help

#### Check Script Status
```bash
# View current configuration
./3-enable-bedrock-logging.sh --status

# Test individual components
aws bedrock get-model-invocation-logging-configuration
aws cloudwatch list-dashboards
aws sns list-topics
```

#### Enable Debug Logging
```bash
# Run scripts with debug output
export AWS_CLI_FILE_ENCODING=UTF-8
export AWS_DEFAULT_OUTPUT=json
bash -x ./0-setup-all.sh
```

#### Validate Setup
```bash
# Check all components are working
python3 6-usage-report.py 1  # Last hour (should work even with no data)
aws logs describe-log-groups --log-group-name-prefix /aws/bedrock
aws cloudwatch list-metrics --namespace AWS/Bedrock
```

### Support Resources
- **AWS Bedrock Documentation**: [docs.aws.amazon.com/bedrock](https://docs.aws.amazon.com/bedrock/)
- **CloudWatch Troubleshooting**: [docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/troubleshooting-CloudWatch.html](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/troubleshooting-CloudWatch.html)
- **AWS CLI Troubleshooting**: [docs.aws.amazon.com/cli/latest/userguide/cli-chap-troubleshooting.html](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-troubleshooting.html)

## 📝 Important Notes

- **Data Latency**: Metrics appear 5-15 minutes after first Bedrock usage
- **Sensitive Data**: CloudWatch Logs contain full request/response data - review for sensitive information
- **Large Responses**: Responses >256KB are automatically routed to S3 for cost optimization
- **Pricing**: Cost estimates use current AWS pricing; verify rates at [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- **Regional Resources**: All resources are created in your configured AWS region
- **Existing Resources**: Scripts handle existing resources gracefully and update configurations as needed

## 📚 Additional Resources

- **[AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)**: Complete service documentation
- **[CloudWatch Metrics for Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-cw.html)**: Available metrics and dimensions
- **[CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)**: Query language and examples
- **[AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)**: Cost analysis and optimization
- **[AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/)**: Proactive cost monitoring and alerts
- **[Bedrock Model Pricing](https://aws.amazon.com/bedrock/pricing/)**: Current pricing for all models

## 🤝 Contributing

Found an issue or want to improve the monitoring setup? 

1. **Report Issues**: Document any problems with setup or configuration
2. **Suggest Improvements**: Propose enhancements to monitoring capabilities
3. **Share Queries**: Contribute useful CloudWatch Logs Insights queries
4. **Update Pricing**: Help keep cost calculations current

## 📄 License

This monitoring setup is provided as-is for educational and operational use. Modify and adapt as needed for your specific requirements.
