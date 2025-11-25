# ADR-003: Async-First Design Pattern

## Status

**Accepted** (October 2024)

## Context

The backend services handle:
- HTTP API requests (I/O bound)
- Database queries (I/O bound)
- External API calls (I/O bound - BigQuery, SFTP, IdP)
- Email sending (I/O bound - SMTP)

Traditional synchronous Python blocks the thread during I/O operations, limiting concurrency to the number of threads/processes.

### Concurrency Requirements

| Operation | Typical Latency | Concurrent Users |
|-----------|-----------------|------------------|
| Dashboard API | 50-200ms | 50-100 |
| Data Ingestion | 5-30 minutes | 5-10 jobs |
| Auth Validation | 100-500ms | 50-100 |

## Decision

We will use **async/await throughout the codebase**:

1. **FastAPI with async endpoints**
2. **SQLAlchemy async sessions** with asyncpg driver
3. **httpx for async HTTP clients**
4. **Async context managers for database sessions**

### Implementation Pattern

```python
# Async endpoint
@router.get("/stats")
async def get_stats(tenant_id: str = Depends(get_current_tenant)):
    async with get_async_db_session("analytics-service") as session:
        result = await session.execute(text("SELECT ..."))
        return result.scalar()

# Async database session
@asynccontextmanager
async def get_async_db_session(service_name: str = None):
    session = async_session_maker()
    try:
        yield session
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()
```

### Parallel Operations

For CPU-bound or blocking operations, use ThreadPoolExecutor:

```python
# BigQuery extraction runs 6 queries in parallel
async def get_date_range_events_async(self, start_date: str, end_date: str):
    loop = asyncio.get_event_loop()
    tasks = []
    for event_type, extractor in event_extractors.items():
        task = loop.run_in_executor(_EXECUTOR, extractor, start_date, end_date)
        tasks.append((event_type, task))
    
    results = {}
    for event_type, task in tasks:
        results[event_type] = await task
    return results
```

## Consequences

### Positive

- **High Concurrency**: Handle 100s of concurrent requests with minimal threads
- **Resource Efficiency**: Single process handles many I/O operations
- **Responsive APIs**: Non-blocking I/O prevents request queuing
- **Natural Fit**: FastAPI is async-first
- **Ecosystem**: Rich async library ecosystem (httpx, asyncpg)

### Negative

- **Code Complexity**: Async/await syntax everywhere
- **Debugging Difficulty**: Stack traces less intuitive
- **Blocking Code Risk**: One blocking call can stall entire service
- **Learning Curve**: Team must understand async patterns
- **Library Compatibility**: Some libraries don't support async

### Mitigations

- **Blocking Code Detection**: Use `asyncio.to_thread()` for blocking operations
- **Timeouts**: Always use timeouts on async operations
- **Testing**: Use `pytest-asyncio` for async test support

## Alternatives Considered

### Synchronous with Thread Pool

**Pros**: Simpler code, familiar patterns  
**Cons**: Higher memory usage (threads), context switching overhead

**Rejected because**: Resource usage scales poorly with concurrency.

### Synchronous with Multiple Processes (Gunicorn)

**Pros**: True parallelism, process isolation  
**Cons**: Memory duplication, IPC complexity, connection pool per process

**Rejected because**: Database connection limits with many processes.

### Mixed Sync/Async

**Pros**: Use async only where needed  
**Cons**: Confusing codebase, easy to accidentally block

**Rejected because**: Consistency is more maintainable.

## Code Patterns

### DO: Async Database Operations

```python
async with get_async_db_session() as session:
    result = await session.execute(query)
```

### DON'T: Blocking in Async Context

```python
# BAD - blocks event loop
async def bad_example():
    time.sleep(5)  # Blocks!
    requests.get(url)  # Blocks!

# GOOD - non-blocking
async def good_example():
    await asyncio.sleep(5)
    async with httpx.AsyncClient() as client:
        await client.get(url)
```

### DO: Use Executor for Blocking Libraries

```python
async def process_with_blocking_lib():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, blocking_function, arg1, arg2)
    return result
```

## References

- [FastAPI Async](https://fastapi.tiangolo.com/async/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

