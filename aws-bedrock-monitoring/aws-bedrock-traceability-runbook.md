# Runbook: AWS Bedrock Traceability (Users, Tokens, Cost)

**Audience:** AWS Account Administrators, IAM / Security, AI Governance  
**Purpose:** Provide a step-by-step operational guide to enable and validate per-user traceability, token usage visibility, and cost attribution for AWS Bedrock usage (e.g., Claude models).  
**Scope:** Human users (developers, admins) accessing Bedrock via IAM Identity Center (SSO).  
**Out of Scope:** Prompt storage, source code logging, model output retention.

---

## 1. Overview

This runbook explains how AWS-native services work together to answer three core questions:

- **WHO** used AWS Bedrock?
- **HOW MUCH** did they use (tokens)?
- **HOW MUCH DID IT COST?**

### AWS Services Involved
- **IAM Identity Center (SSO)** – user identity
- **AWS STS** – temporary credentials
- **AWS CloudTrail** – audit trail (who + what)
- **Amazon CloudWatch** – usage metrics (tokens)
- **AWS Billing / Cost Explorer** – cost attribution

---

## 2. Prerequisites

### 2.1 IAM Identity Center
Confirm:
- IAM Identity Center is enabled
- Users authenticate via corporate IdP
- Developers use `aws sso login`

### 2.2 Identity Smoke Test
Have a user run:

```bash
aws sts get-caller-identity --profile bedrock-dev
```

**Expected pattern:**
```text
arn:aws:sts::<account-id>:assumed-role/AWSReservedSSO_<PermissionSet>/<user@company.com>
```

If the ARN does not include `AWSReservedSSO` and the user email, stop and fix SSO first.

---

## 3. Identity Configuration (WHO)

### 3.1 Permission Sets
Create and manage permission sets such as:
- `BedrockDeveloper`
- `BedrockAdmin` (optional)

Minimum required permissions:
- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- `bedrock:Converse`
- `bedrock:ConverseStream`

### 3.2 Group-Based Access
Assign permission sets to Identity Center groups:
- `dev-bedrock-pilot`
- `ai-platform-admins`

Avoid individual user assignments.

### 3.3 Prohibited Patterns
Ensure the following are **not used**:
- Shared IAM users
- Static access keys
- Shared Bedrock roles without per-user sessions

---

## 4. CloudTrail Configuration (WHO + WHAT)

### 4.1 Enable Management Events
In the CloudTrail console:
- Enable **Management events**
- Set **Read and Write** events
- Enable **Global service events**
- Ensure coverage for all Bedrock regions in use

This captures:
- `InvokeModel`
- `Converse`
- Caller identity ARN
- Model ID
- Timestamp and region

---

### 4.2 Configure Event Storage
Choose **one** of the following:

#### Option A — CloudTrail Lake (Recommended)
- Create an Event Data Store
- Include management events
- Set retention (e.g., 30–90 days for pilots)

#### Option B — S3 + Athena
- Configure trail to write to S3
- Create Athena tables for CloudTrail logs

Without this step, events are not practically queryable.

---

## 5. CloudWatch Configuration (TOKENS)

### 5.1 Verify Bedrock Metrics
Navigate to:
```
CloudWatch → Metrics → AWS/Bedrock
```

Confirm metrics are available:
- `InputTokens`
- `OutputTokens`
- `TotalTokens`
- `Latency`
- `Errors`

Dimensions typically include:
- `ModelId`
- `Region`

⚠️ Metrics are **not user-dimensioned** by design.

---

## 6. Cost Attribution (COST)

### 6.1 Enable Cost Allocation Tags
In **Billing → Cost Allocation Tags**, enable relevant tags such as:
- `Project`
- `Team`
- `Environment`

Apply tags according to organizational standards (account or role level).

---

### 6.2 Cost Calculation Model
Cost is derived as:

```
(InputTokens × InputTokenPrice) + (OutputTokens × OutputTokenPrice)
```

Pricing comes from AWS Bedrock published rates for each model.

---

## 7. Correlation Model (How Data Is Joined)

| Signal | Source | Answers |
|------|--------|--------|
| User identity | CloudTrail | WHO |
| Model invoked | CloudTrail | WHAT |
| Token usage | CloudWatch | HOW MUCH |
| Cost | Pricing × Tokens | COST |

Correlation keys:
- Time window
- AWS account
- Region
- Model ID

---

## 8. Validation Tests

### Test 1 — Identity
```bash
aws sts get-caller-identity --profile bedrock-dev
```
Confirm ARN includes user email.

---

### Test 2 — CloudTrail
1. Invoke a Bedrock model
2. Wait 2–5 minutes
3. Query CloudTrail

Verify:
- `eventSource = bedrock.amazonaws.com`
- `userIdentity.arn` includes the user email
- Correct model ID is present

---

### Test 3 — CloudWatch
Within a few minutes:
- Token metrics increase for the invoked model
- Metrics appear in the correct region

---

## 9. Common Issues & Resolutions

| Issue | Likely Cause | Resolution |
|----|----|----|
| Unable to locate credentials | Wrong AWS profile | Set `AWS_PROFILE` or pass `--profile` |
| Same ARN for all users | Shared role or user | Enforce IAM Identity Center |
| No CloudTrail events | Management events disabled | Enable CloudTrail management events |
| Token metrics missing | Wrong region or delay | Verify region, wait 5–10 minutes |
| Cost unclear | Tags not enabled | Enable cost allocation tags |

---

## 10. Security & Governance Notes

- Prompts and responses are not stored
- Source code is not logged
- Identity, usage, and cost are tracked using AWS-native controls
- Aligns with least-privilege and privacy-first principles

---

## 11. Completion Criteria

This runbook is complete when:

- SSO-based assumed-role ARNs are visible in CloudTrail
- Bedrock management events are queryable
- Token metrics are visible in CloudWatch
- Cost can be estimated per model and time window
- No shared credentials are in use

---

## Admin Summary Statement

> Identity comes from IAM Identity Center, usage comes from CloudWatch, and audit comes from CloudTrail. We join them by time and model to achieve per-user cost visibility without storing prompts.

---

**End of Runbook**
