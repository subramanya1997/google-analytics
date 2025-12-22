# ADR-002: PostgreSQL Functions for Analytics Queries

## Status

**Accepted** (October 2024)

## Context

The analytics service needs to execute complex queries that:
- Aggregate data across multiple tables (events, users, locations)
- Support pagination and filtering
- Return JSON-structured responses
- Execute within acceptable latency (< 500ms for dashboard)

Initial prototypes using SQLAlchemy ORM showed:
- Complex JOIN queries were slow (2-5 seconds)
- Multiple round-trips for related data
- Python-side aggregation was inefficient
- Query optimization was difficult

### Example Query Complexity

A "purchase tasks" query requires:
1. Join purchase events with user data
2. Join with location data
3. Aggregate by user
4. Filter by date range and location
5. Apply pagination
6. Return nested JSON structure

## Decision

We will implement **complex analytics queries as PostgreSQL PL/pgSQL functions** that:
- Accept filter parameters
- Perform all joins and aggregations in the database
- Return JSON/JSONB directly
- Are called via simple `SELECT function_name(params)` from Python

### Example

```sql
CREATE OR REPLACE FUNCTION get_purchase_tasks(
    p_tenant_id UUID,
    p_page INTEGER,
    p_limit INTEGER,
    p_location_id TEXT DEFAULT NULL,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    -- Complex query with CTEs, aggregations, JSON building
    WITH filtered_purchases AS (...)
    SELECT jsonb_build_object(
        'data', jsonb_agg(...),
        'total', count(*),
        'page', p_page,
        'limit', p_limit,
        'has_more', ...
    ) INTO result
    FROM ...;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;
```

### Python Calling Code

```python
async def get_purchase_tasks(self, tenant_id: str, page: int, limit: int, ...):
    async with get_async_db_session() as session:
        result = await session.execute(
            text("SELECT get_purchase_tasks(:tenant_id, :page, :limit, ...)"),
            {"tenant_id": tenant_id, "page": page, "limit": limit, ...}
        )
        return result.scalar()  # Returns ready-to-use dict
```

## Consequences

### Positive

- **Performance**: 10-100x faster than ORM queries (single round-trip)
- **Query Optimization**: PostgreSQL query planner optimizes entire query
- **Reduced Network**: Only results transmitted, not intermediate data
- **Maintainability**: SQL experts can optimize without Python changes
- **Testing**: Functions can be tested directly in psql
- **Caching**: PostgreSQL can cache query plans

### Negative

- **Two Languages**: Developers must know SQL and Python
- **Deployment Coupling**: Schema changes require coordinated deployment
- **Debugging**: Harder to debug than Python code
- **IDE Support**: Less tooling for PL/pgSQL than Python
- **Version Control**: SQL files need separate management

### Mitigations

- **Debugging**: Use `RAISE NOTICE` for logging in functions
- **IDE Support**: Use DataGrip or similar for SQL development
- **Version Control**: All functions in `database/functions/` directory

## Alternatives Considered

### SQLAlchemy ORM Only

**Pros**: Single language, familiar patterns, automatic query generation  
**Cons**: Poor performance for complex analytics, N+1 query issues

**Rejected because**: Latency requirements not met (2-5 seconds vs < 500ms).

### Raw SQL in Python

**Pros**: Single codebase, easier debugging  
**Cons**: String concatenation risks, harder to optimize, still multiple round-trips

**Rejected because**: Same performance issues as ORM, plus SQL injection risks.

### Materialized Views

**Pros**: Pre-computed results, very fast reads  
**Cons**: Stale data, refresh overhead, storage costs, complex invalidation

**Considered for future**: May add for dashboard summary metrics.

### External Query Engine (e.g., Trino)

**Pros**: Scalable, federated queries  
**Cons**: Additional infrastructure, operational complexity, overkill for our scale

**Rejected because**: Adds unnecessary complexity for current data volumes.

## Performance Results

| Query | ORM | PostgreSQL Function | Improvement |
|-------|-----|---------------------|-------------|
| Purchase Tasks (1000 rows) | 2.3s | 0.08s | 28x |
| Dashboard Stats | 1.8s | 0.05s | 36x |
| Cart Abandonment | 3.1s | 0.12s | 25x |
| Search Analysis | 2.5s | 0.09s | 27x |

## References

- [PostgreSQL PL/pgSQL Documentation](https://www.postgresql.org/docs/current/plpgsql.html)
- [When to Use Stored Procedures](https://www.postgresql.org/docs/current/xplang.html)

