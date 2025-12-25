# Appendix: Diagrams — AWS Bedrock Traceability (Users, Tokens, Cost)

**Purpose:** Visual-only appendix to support the *AWS Bedrock Traceability Runbook*.  
**Audience:** AWS Admins, Security, Architecture, Executives  
**Note:** This appendix contains **diagrams only** (no prose) for easy presentation and reuse.

---

## A1. End-to-End Traceability Flow (WHO + HOW MUCH + COST)

```mermaid
flowchart LR
    U[User<br/>aws sso login] --> IC[IAM Identity Center]
    IC --> STS[STS Temporary Credentials<br/>Assumed Role + Email]
    STS --> TOOL[VS Code / Claude Code]
    TOOL --> BR[AWS Bedrock API]

    BR --> CT[CloudTrail<br/>WHO + MODEL]
    BR --> CW[CloudWatch<br/>TOKENS]

    CT --> Q[Trail Lake / Athena]
    CW --> Q

    Q --> R[Per-User Usage & Cost Reports]
```

---

## A2. Identity Model: Shared vs SSO (Critical Difference)

```mermaid
flowchart TB
    subgraph BAD["❌ Shared IAM User / Shared Role"]
        S1[Multiple Humans] --> I1[Single AWS Identity]
        I1 --> L1[CloudTrail Logs]
        L1 --> X1[No Human Attribution]
    end

    subgraph GOOD["✅ IAM Identity Center (SSO)"]
        S2[Each Human User] --> I2[Unique SSO Session]
        I2 --> L2[CloudTrail Logs]
        L2 --> Y1[Per-User Attribution]
    end
```

---

## A3. How the Assumed-Role ARN Is Formed

```mermaid
sequenceDiagram
    participant User as User (email)
    participant IdP as Corporate IdP
    participant SSO as IAM Identity Center
    participant STS as AWS STS
    participant AWS as AWS Service (Bedrock)

    User->>IdP: Authenticate
    IdP->>SSO: Identity Assertion
    SSO->>STS: AssumeRole (Permission Set)
    STS-->>User: Temporary Credentials
    User->>AWS: API Call
```

**Resulting ARN format:**
```
arn:aws:sts::<account-id>:assumed-role/AWSReservedSSO_<PermissionSet>/<user@company.com>
```

---

## A4. Separation of Concerns (Governance-Friendly)

```mermaid
flowchart LR
    ID[Identity] --> CT[CloudTrail]
    USE[Usage] --> CW[CloudWatch]
    COST[Pricing] --> CALC[Cost Calculation]

    CT --> JOIN[Correlation Layer]
    CW --> JOIN
    CALC --> JOIN

    JOIN --> GOV[Governance & Reporting]
```

---

## A5. What Is and Is NOT Logged

```mermaid
flowchart TB
    subgraph LOGGED["✅ Logged"]
        L1[User Identity ARN]
        L2[Model ID]
        L3[Token Counts]
        L4[Latency / Errors]
    end

    subgraph NOTLOGGED["❌ Not Logged"]
        N1[Prompt Text]
        N2[Source Code]
        N3[Model Responses]
        N4[Chat History]
    end
```

---

## A6. Minimum Viable Admin Configuration (Visual Checklist)

```mermaid
flowchart LR
    A[IAM Identity Center<br/>Enabled] --> B[SSO Permission Sets]
    B --> C[CloudTrail<br/>Management Events]
    C --> D[CloudTrail Lake or S3]
    D --> E[CloudWatch Bedrock Metrics]
    E --> F[Cost Allocation Tags]
    F --> G[Per-User Cost Visibility]
```

---

## A7. Incident / Audit Question Mapping

```mermaid
flowchart TB
    Q1["Who used Bedrock?"] --> CT[CloudTrail]
    Q2["Which model?"] --> CT
    Q3["How many tokens?"] --> CW[CloudWatch]
    Q4["What did it cost?"] --> COST[Pricing x Tokens]
```

---

**End of Diagram Appendix**
