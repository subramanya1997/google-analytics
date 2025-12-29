# ADR-006: Parallel BigQuery Extraction

## Status

**Accepted** (December 2025)

## Context

Data ingestion needs to extract 6 event types from BigQuery for a given date range:
1. `purchase`
2. `add_to_cart`
3. `page_view`
4. `view_item`
5. `view_search_results`
6. `no_search_results`

### Performance Problem

Sequential extraction was too slow:
- Each query: 30 seconds - 2 minutes
- Total time: 3-12 minutes for 6 queries
- Users waiting for jobs to complete

### Constraints

- BigQuery client is not async-native
- Python GIL limits true parallelism
- Need to avoid overwhelming BigQuery quotas
- Memory usage must be controlled

## Decision

We will use a **ThreadPoolExecutor** to run BigQuery queries in parallel:

```python
from concurrent.futures import ThreadPoolExecutor

# Module-level executor (shared across requests)
_BIGQUERY_EXECUTOR = ThreadPoolExecutor(
    max_workers=6,  # One per event type
    thread_name_prefix="bigquery-worker"
)

async def get_date_range_events_async(self, start_date: str, end_date: str):
    """Extract all event types in parallel."""
    
    event_extractors = {
        "purchase": self._extract_purchase_events,
        "add_to_cart": self._extract_add_to_cart_events,
        "page_view": self._extract_page_view_events,
        "view_search_results": self._extract_view_search_results_events,
        "no_search_results": self._extract_no_search_results_events,
        "view_item": self._extract_view_item_events,
    }

    loop = asyncio.get_event_loop()
    tasks = []
    
    for event_type, extractor in event_extractors.items():
        # Schedule each extraction in thread pool
        task = loop.run_in_executor(
            _BIGQUERY_EXECUTOR, 
            extractor, 
            start_date, 
            end_date
        )
        tasks.append((event_type, task))

    # Wait for all to complete
    results = {}
    for event_type, task in tasks:
        try:
            events = await task
            results[event_type] = events
        except Exception as e:
            logger.error(f"Error extracting {event_type}: {e}")
            results[event_type] = []

    return results
```

## Consequences

### Positive

- **6x Faster**: All queries run simultaneously
- **Predictable Time**: Job time = slowest single query
- **Non-Blocking**: Doesn't block event loop
- **Resource Control**: Fixed thread pool size
- **Error Isolation**: One query failure doesn't affect others

### Negative

- **Memory Usage**: 6 result sets in memory simultaneously
- **BigQuery Load**: 6 concurrent queries (within quotas)
- **Thread Management**: Need to handle pool lifecycle
- **Debugging**: Parallel execution harder to trace

### Mitigations

- **Pool Size Limit**: Fixed at 6 workers
- **Module-Level Pool**: Reused across requests
- **Individual Error Handling**: Each task wrapped in try/except
- **Logging**: Each task logs its event type

## Performance Results

| Scenario | Sequential | Parallel | Improvement |
|----------|------------|----------|-------------|
| 1 day data | 3 min | 45 sec | 4x |
| 1 week data | 8 min | 1.5 min | 5.3x |
| 1 month data | 25 min | 5 min | 5x |

## Alternatives Considered

### Async BigQuery Client

**Pros**: True async, no threads  
**Cons**: Google doesn't provide async client, would need custom implementation

**Rejected because**: Significant development effort for custom async client.

### ProcessPoolExecutor

**Pros**: True parallelism (bypasses GIL)  
**Cons**: Serialization overhead, can't share BigQuery client

**Rejected because**: BigQuery client isn't picklable, overhead too high.

### Batch Query API

**Pros**: Single API call, BigQuery handles parallelism  
**Cons**: More complex result handling, still waiting on BigQuery

**Considered for future**: May help with very large date ranges.

### Single Combined Query

**Pros**: One round-trip, BigQuery optimizes  
**Cons**: Extremely complex SQL, harder to maintain, memory issues

**Rejected because**: Query would be unmaintainable.

## Thread Pool Configuration

```python
_BIGQUERY_EXECUTOR = ThreadPoolExecutor(
    max_workers=6,        # Match number of event types
    thread_name_prefix="bigquery-worker"  # For debugging
)
```

### Why 6 Workers?

- Exactly 6 event types to extract
- More workers = wasted resources
- Fewer workers = sequential bottleneck
- BigQuery handles concurrent queries well

## References

- [Python ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html)
- [asyncio run_in_executor](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.run_in_executor)
- [BigQuery Quotas](https://cloud.google.com/bigquery/quotas)

