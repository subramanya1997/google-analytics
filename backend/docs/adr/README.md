# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the Google Analytics Intelligence System backend.

## What is an ADR?

An Architecture Decision Record captures an important architectural decision made along with its context and consequences.

## ADR Template

```markdown
# ADR-XXX: Title

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Consequences
What becomes easier or harder after this change?

## Alternatives Considered
What other options did we evaluate?
```

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](./001-microservices-architecture.md) | Microservices Architecture | Accepted | 2025-12 |
| [002](./002-postgresql-functions.md) | PostgreSQL Functions for Analytics | Accepted | 2025-12 |
| [003](./003-async-first-design.md) | Async-First Design Pattern | Accepted | 2025-12 |
| [004](./004-multi-tenant-isolation.md) | Multi-Tenant Row-Level Isolation | Accepted | 2025-12 |
| [005](./005-fastapi-factory-pattern.md) | FastAPI Application Factory | Accepted | 2025-12 |
| [006](./006-bigquery-parallel-extraction.md) | Parallel BigQuery Extraction | Accepted | 2025-12 |

## Creating a New ADR

1. Copy the template above
2. Create new file: `XXX-short-title.md`
3. Fill in all sections
4. Update this index

