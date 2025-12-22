# ADR-004: Multi-Tenant Row-Level Isolation

## Status

**Accepted** (October 2024)

## Context

The system serves multiple tenants (customers) with strict data isolation requirements:
- Tenant A must never see Tenant B's data
- Each tenant has their own BigQuery, SFTP, and SMTP configurations
- Tenants share the same application infrastructure
- Future requirement: per-tenant billing based on usage

### Security Requirements

- **Data Isolation**: Complete separation of tenant data
- **Configuration Isolation**: Per-tenant external service credentials
- **Audit Trail**: Track which tenant performed which action
- **Compliance**: Meet SOC 2 and GDPR requirements

## Decision

We will implement **row-level tenant isolation** using a `tenant_id` column in all tables:

### Schema Pattern

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),  -- Always present
    event_data JSONB,
    ...
);

CREATE INDEX idx_events_tenant ON events(tenant_id);  -- Always indexed
```

### Enforcement Pattern

```python
# Every query includes tenant_id
async def get_data(tenant_id: str):
    result = await session.execute(
        text("SELECT * FROM table WHERE tenant_id = :tenant_id"),
        {"tenant_id": tenant_id}
    )
```

### Request Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         REQUEST                                  │
│  Authorization: Bearer <token>                                   │
│  X-Tenant-Id: <uuid>                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DEPENDENCY INJECTION                          │
│  1. Validate token                                               │
│  2. Extract tenant_id from header                                │
│  3. Verify tenant exists and is active                          │
│  4. Pass tenant_id to endpoint                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       ENDPOINT                                   │
│  async def get_data(tenant_id: str = Depends(get_tenant)):      │
│      # tenant_id is guaranteed valid                             │
│      return await db.query_with_tenant(tenant_id, ...)          │
└─────────────────────────────────────────────────────────────────┘
```

## Consequences

### Positive

- **Simple Implementation**: No complex database configuration
- **Portable**: Works with any PostgreSQL deployment
- **Flexible Queries**: Easy to aggregate across tenants if needed (admin)
- **Standard Tooling**: Normal backups, restores, migrations
- **Proven Pattern**: Used by Salesforce, Slack, many SaaS companies

### Negative

- **Developer Discipline**: Must remember to filter by tenant_id
- **Index Overhead**: Every table needs tenant_id index
- **Query Complexity**: All queries slightly more complex
- **No Database Isolation**: Noisy neighbor possible

### Mitigations

- **Code Review**: Check all queries for tenant filtering
- **PostgreSQL RLS**: Could add Row-Level Security policies as additional layer
- **Audit Logging**: Log tenant_id with every database operation

## Alternatives Considered

### Separate Database Per Tenant

**Pros**: Complete isolation, easy backup/restore per tenant, no index overhead  
**Cons**: Connection pool explosion, complex migrations, operational nightmare

**Rejected because**: Doesn't scale with 100+ tenants, operational burden too high.

### Schema-Per-Tenant

**Pros**: Good isolation, single database, familiar pattern  
**Cons**: Complex migrations, connection string management, search_path issues

**Rejected because**: Migrations across 100+ schemas is error-prone.

### PostgreSQL Row-Level Security (RLS)

**Pros**: Database-enforced isolation, can't accidentally skip filter  
**Cons**: Complexity, performance overhead, harder to debug

**Considered for future**: May add as additional security layer.

### Application-Level Virtual Databases

**Pros**: Complete abstraction, flexible routing  
**Cons**: Custom implementation, no tooling support, testing complexity

**Rejected because**: Reinventing the wheel.

## Implementation Details

### Tenant ID Extraction

```python
# FastAPI dependency
async def get_current_tenant(
    x_tenant_id: str = Header(...),
    authorization: str = Header(...),
) -> str:
    # Validate token
    token_data = await validate_token(authorization)
    
    # Verify tenant matches token
    if token_data.tenant_id != x_tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    
    # Verify tenant is active
    tenant = await get_tenant(x_tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant not found or inactive")
    
    return x_tenant_id
```

### Query Pattern

```python
# All queries include tenant_id as first filter
async def get_purchases(tenant_id: str, start_date: str, end_date: str):
    return await session.execute(
        text("""
            SELECT * FROM purchase 
            WHERE tenant_id = :tenant_id 
            AND event_date BETWEEN :start AND :end
        """),
        {"tenant_id": tenant_id, "start": start_date, "end": end_date}
    )
```

## References

- [Multi-Tenant Data Architecture](https://docs.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/storage-data)
- [Row-Level Security in PostgreSQL](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Slack's Multi-Tenant Architecture](https://slack.engineering/)

