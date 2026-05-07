# Architecture

This document describes the cloud architecture of `serverless-dashboard-aws`,
how requests flow through the system, and the rationale behind each design
decision.

## High-level diagram

![AWS architecture](./architecture-diagram.png)

The PNG above is generated from [`architecture-diagram.py`](./architecture-diagram.py)
using the `diagrams` Python library. To regenerate it:

```bash
cd docs
pip install diagrams
python architecture-diagram.py
```

## Components

| Component | Purpose |
|---|---|
| **CloudFront** | Edge cache and HTTPS for the SPA |
| **S3 (private)** | Static hosting for the React build, accessed only via CloudFront OAC |
| **API Gateway HTTP API** | Public REST endpoint, JWT authorizer for protected routes, CORS |
| **Cognito User Pool** | Identity provider; signs JWTs validated by the authorizer |
| **AWS Lambda (Python 3.12)** | All compute. One handler per route, packaged together but routed individually |
| **DynamoDB (single-table)** | Profile + event storage; pay-per-request, point-in-time recovery enabled |
| **EventBridge custom bus** | Fan-out target for outbound integrations (`/integrations/dispatch`) |

## Component diagram (Mermaid)

```mermaid
graph LR
  user([User / External System])
  subgraph Edge
    cf[CloudFront]
    s3[(S3 private bucket)]
  end
  subgraph API
    apigw[API Gateway HTTP API]
    auth[(Cognito User Pool)]
  end
  subgraph Compute
    reg[Lambda auth/register]
    login[Lambda auth/login]
    me[Lambda users/me]
    stats[Lambda dashboard/stats]
    wh[Lambda integrations/webhook]
    disp[Lambda integrations/dispatch]
  end
  ddb[(DynamoDB single-table)]
  bus[EventBridge bus]

  user -- HTTPS --> cf --> s3
  user -- HTTPS / Bearer JWT --> apigw
  user -- HTTPS / X-API-Key --> wh
  apigw -- JWT authorizer --> auth
  apigw --> reg & login & me & stats & wh & disp
  reg --> auth
  login --> auth
  me --> ddb
  stats --> ddb
  wh --> ddb
  disp --> ddb
  disp --> bus
```

## Sequence — Login

```mermaid
sequenceDiagram
  participant U as User
  participant SPA as React SPA
  participant API as API Gateway
  participant L as auth/login Lambda
  participant C as Cognito User Pool

  U->>SPA: enters email + password
  SPA->>API: POST /auth/login {email, password}
  API->>L: invoke
  L->>C: InitiateAuth(USER_PASSWORD_AUTH)
  C-->>L: AuthenticationResult (idToken, accessToken, refreshToken)
  L-->>API: 200 { tokens }
  API-->>SPA: 200 { tokens }
  SPA->>SPA: persist session (localStorage)
  SPA-->>U: redirect to /dashboard
```

## Sequence — Authenticated dashboard load

```mermaid
sequenceDiagram
  participant SPA as React SPA
  participant API as API Gateway
  participant Auth as JWT authorizer
  participant ME as users/me Lambda
  participant ST as dashboard/stats Lambda
  participant DB as DynamoDB

  SPA->>API: GET /users/me (Bearer idToken)
  API->>Auth: validate JWT (issuer + audience)
  Auth-->>API: claims {sub, email, ...}
  API->>ME: invoke with claims
  ME->>DB: GetItem PK=USER#sub SK=PROFILE
  DB-->>ME: profile
  ME-->>SPA: 200 { profile }

  SPA->>API: GET /dashboard/stats (Bearer idToken)
  API->>ST: invoke with claims
  ST->>DB: Query PK=USER#sub SK begins_with EVENT#
  DB-->>ST: events
  ST-->>SPA: 200 { totals + byType + latest }
```

## Sequence — Inbound webhook (system integration)

```mermaid
sequenceDiagram
  participant Ext as External System
  participant API as API Gateway
  participant WH as integrations/webhook Lambda
  participant DB as DynamoDB

  Ext->>API: POST /integrations/webhook (X-API-Key, body)
  API->>WH: invoke
  WH->>WH: validate X-API-Key against WEBHOOK_API_KEY
  WH->>DB: PutItem PK=USER#sub SK=EVENT#ts
  DB-->>WH: ok
  WH-->>API: 201 { id, eventType, createdAt }
  API-->>Ext: 201
```

## Sequence — Outbound dispatch (fan-out)

```mermaid
sequenceDiagram
  participant SPA as React SPA
  participant API as API Gateway
  participant D as integrations/dispatch Lambda
  participant DB as DynamoDB
  participant EB as EventBridge

  SPA->>API: POST /integrations/dispatch (Bearer idToken)
  API->>D: invoke with claims
  D->>EB: PutEvents (Source=serverless-dashboard.app)
  EB-->>D: ok
  D->>DB: PutItem PK=USER#sub SK=EVENT#ts
  D-->>SPA: 201 { id, createdAt }
```

## DynamoDB single-table design

| PK | SK | type | Notes |
|---|---|---|---|
| `USER#<sub>` | `PROFILE` | `USER_PROFILE` | One row per Cognito user |
| `USER#<sub>` | `EVENT#<iso-ts>` | `EVENT` | Tracking events per user, sorted desc |

`GSI1` is reserved for cross-user listings. Events use
`GSI1PK = "EVENT_TYPE#<type>"` so future dashboards can aggregate without scans.

## Security

- All routes except `/auth/*` and `/integrations/webhook` require a Cognito-issued JWT.
- `/integrations/webhook` is gated by a shared `X-API-Key` provided in the `WEBHOOK_API_KEY` env var (rotate it per environment).
- S3 bucket is **private**; access goes through CloudFront with **Origin Access Control (OAC)**.
- Lambdas use an IAM role with **least-privilege** statements scoped to the deployed table, user pool and event bus.
- DynamoDB has Point-in-Time Recovery enabled.

## Cost considerations

- Lambda + HTTP API + DynamoDB + Cognito + S3 + CloudFront are all pay-per-use.
- Idle cost is essentially zero outside of CloudFront and S3 storage.
