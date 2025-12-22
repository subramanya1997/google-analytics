# ADR-001: Microservices Architecture

## Status

**Accepted** (October 2024)

## Context

We need to build a backend system for processing Google Analytics data that:
- Serves a dashboard frontend
- Ingests data from external sources (BigQuery, SFTP)
- Handles authentication with an external identity provider
- Sends automated email reports
- Supports multiple tenants

The system needs to be:
- Maintainable by a small team
- Deployable independently for different concerns
- Scalable based on workload type

### Workload Characteristics

| Concern | Characteristics |
|---------|-----------------|
| Authentication | Low volume, security-critical |
| Data Ingestion | Batch processing, CPU/memory intensive |
| Analytics API | High read volume, low latency required |
| Email Sending | Batch processing, external SMTP dependency |

## Decision

We will implement a **microservices architecture** with three services:

1. **Auth Service (Port 8003)**
   - OAuth 2.0 authentication
   - Token validation
   - Tenant configuration management

2. **Data Service (Port 8002)**
   - BigQuery data extraction
   - SFTP file processing
   - Job management

3. **Analytics Service (Port 8001)**
   - Dashboard statistics API
   - Task list queries
   - Email report generation and sending

All services share:
- A common PostgreSQL database
- Shared library code (`common/` package)
- Consistent API patterns

## Consequences

### Positive

- **Independent Deployment**: Services can be updated without affecting others
- **Resource Isolation**: Data ingestion won't impact dashboard responsiveness
- **Team Scalability**: Different team members can own different services
- **Technology Flexibility**: Services can be optimized independently
- **Failure Isolation**: A crash in data service doesn't affect authentication

### Negative

- **Operational Complexity**: Three services to monitor and deploy
- **Shared Database**: Not true microservices (shared state)
- **Code Duplication Risk**: Need discipline to use shared `common/` package
- **Cross-Service Testing**: Integration testing is more complex

### Neutral

- **Network Overhead**: Minimal since services communicate via shared database
- **Deployment Tooling**: Required regardless of architecture

## Alternatives Considered

### Monolithic Application

**Pros**: Simpler deployment, easier testing, no network overhead  
**Cons**: Resource contention between data ingestion and API serving, harder to scale specific workloads

**Rejected because**: Data ingestion jobs would block API requests, and we need independent scaling.

### Full Microservices (Separate Databases)

**Pros**: True isolation, independent scaling, polyglot persistence  
**Cons**: Data synchronization complexity, eventual consistency issues, much higher operational burden

**Rejected because**: Overkill for our team size and data consistency requirements.

### Serverless Functions

**Pros**: Auto-scaling, pay-per-use, no infrastructure management  
**Cons**: Cold start latency, 15-minute execution limits for ingestion, vendor lock-in

**Rejected because**: Ingestion jobs can run for 30+ minutes, and we need consistent low-latency API responses.

## References

- [Microservices by Martin Fowler](https://martinfowler.com/articles/microservices.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

