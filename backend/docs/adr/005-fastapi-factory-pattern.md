# ADR-005: FastAPI Application Factory Pattern

## Status

**Accepted** (December 2025)

## Context

With three microservices, we need:
- Consistent configuration across services
- Shared middleware (CORS, timing, error handling)
- Standard health check and root endpoints
- Reduced boilerplate in each service
- Consistent logging setup

Each service was duplicating ~100 lines of FastAPI setup code.

## Decision

We will implement a **factory function** that creates FastAPI applications with standard configuration:

```python
# common/fastapi/app_factory.py
def create_fastapi_app(
    service_name: str,
    description: str,
    api_router = None,
    additional_setup: Optional[callable] = None,
    root_path: str = ""
) -> FastAPI:
    """Create a FastAPI app with common configuration."""
    
    # Setup logging
    setup_logging(service_name)
    
    # Get settings
    settings = get_settings(service_name)
    
    # Create app
    app = FastAPI(
        title=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        description=description,
        root_path=root_path if settings.ENVIRONMENT != "DEV" else ""
    )
    
    # Add CORS middleware
    app.add_middleware(CORSMiddleware, ...)
    
    # Add timing middleware
    @app.middleware("http")
    async def add_process_time_header(request, call_next):
        ...
    
    # Add standard endpoints
    @app.get("/health")
    async def health_check():
        ...
    
    @app.get("/")
    async def root():
        ...
    
    # Add global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        ...
    
    # Include API router
    if api_router:
        app.include_router(api_router, prefix=settings.API_V1_STR)
    
    return app
```

### Service Usage

```python
# services/analytics_service/main.py
from common.fastapi import create_fastapi_app
from services.analytics_service.api.v1.api import api_router

app = create_fastapi_app(
    service_name="analytics-service",
    description="Analytics service for Google Analytics intelligence",
    api_router=api_router,
    root_path="/analytics",
)
```

## Consequences

### Positive

- **DRY**: ~15 lines per service vs ~100
- **Consistency**: All services behave identically
- **Centralized Updates**: Fix once, deploy everywhere
- **Best Practices**: Standard patterns enforced
- **Testing**: Factory can be tested independently

### Negative

- **Hidden Complexity**: Magic in the factory
- **Flexibility Trade-off**: Less customization per service
- **Debugging**: Need to understand factory internals

### Mitigations

- **additional_setup Callback**: For service-specific setup
- **Documentation**: Clear factory documentation
- **Simple Factory**: Keep factory code straightforward

## Alternatives Considered

### Base Class Inheritance

**Pros**: Familiar OOP pattern  
**Cons**: FastAPI doesn't use class-based views, awkward fit

**Rejected because**: Doesn't match FastAPI's design patterns.

### Copy-Paste with Comments

**Pros**: Explicit, no hidden behavior  
**Cons**: Drift over time, update burden, inconsistency

**Rejected because**: Maintenance burden, inevitable drift.

### Configuration File

**Pros**: Declarative, easy to understand  
**Cons**: Limited flexibility, another syntax to learn

**Rejected because**: Python factory is more flexible and familiar.

## Factory Features

| Feature | Description |
|---------|-------------|
| Logging Setup | Configures Loguru with service-specific log files |
| CORS | Environment-aware CORS configuration |
| Request Timing | `X-Process-Time` header on all responses |
| Health Check | `/health` endpoint with service info |
| Root Endpoint | `/` with service status and docs link |
| Error Handling | Global exception handler with logging |
| API Prefix | Consistent `/api/v1` prefix |
| OpenAPI | Automatic documentation at `/docs` |

## References

- [FastAPI Application Factory](https://fastapi.tiangolo.com/advanced/sub-applications/)
- [Flask Application Factory](https://flask.palletsprojects.com/patterns/appfactories/)

