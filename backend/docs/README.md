# Backend Documentation

> **Google Analytics Intelligence System**  
> **Version**: 1.0.0  
> **Last Updated**: December 2025

## Documentation Index

Welcome to the backend documentation. This documentation follows MAANG-style standards for comprehensive technical documentation.

---

## 📚 Core Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, design principles, data flow | All developers |
| [API.md](./API.md) | Complete API reference with examples | Frontend devs, integrators |
| [DATABASE.md](./DATABASE.md) | Schema, tables, functions, indexes | Backend devs, DBAs |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Setup guide, coding standards, debugging | New developers |
| [RUNBOOK.md](./RUNBOOK.md) | Operations guide, incident response | On-call engineers |
| [AZURE_FUNCTIONS_DEPLOYMENT.md](./AZURE_FUNCTIONS_DEPLOYMENT.md) | Azure Functions deployment guide | DevOps, Backend devs |

---

## 🏛️ Architecture Decision Records (ADRs)

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](./adr/001-microservices-architecture.md) | Microservices Architecture | Accepted |
| [ADR-002](./adr/002-postgresql-functions.md) | PostgreSQL Functions for Analytics | Accepted |
| [ADR-003](./adr/003-async-first-design.md) | Async-First Design Pattern | Accepted |
| [ADR-004](./adr/004-multi-tenant-isolation.md) | Multi-Tenant Row-Level Isolation | Accepted |
| [ADR-005](./adr/005-fastapi-factory-pattern.md) | FastAPI Application Factory | Accepted |
| [ADR-006](./adr/006-bigquery-parallel-extraction.md) | Parallel BigQuery Extraction | Accepted |

---

## 🔧 Service Documentation

Each microservice has its own README with specific details:

| Service | Port | Documentation |
|---------|------|---------------|
| Analytics Service | 8001 | [README](../services/analytics_service/README.md) |
| Data Service | 8002 | [README](../services/data_service/README.md) |
| Auth Service | 8003 | [README](../services/auth_service/README.md) |
| Azure Functions | Serverless | [README](../services/functions/README.md) |

---

## 🚀 Quick Links

### Getting Started
```bash
cd google-analytics/backend
uv sync --dev
cp .env.example .env
make db_setup
make services_start
```

### Common Commands
```bash
make services_start    # Start all services
make service_analytics # Start analytics only (8001)
make service_data      # Start data only (8002)
make service_auth      # Start auth only (8003)
make db_setup          # Initialize database
make db_clean          # Clear database
```

### API Documentation
- Analytics: http://localhost:8001/docs
- Data: http://localhost:8002/docs
- Auth: http://localhost:8003/docs

---

## 📁 Documentation Structure

```
docs/
├── README.md              # This file - documentation index
├── ARCHITECTURE.md        # System architecture
├── API.md                 # API reference
├── DATABASE.md            # Database schema
├── DEVELOPMENT.md         # Development guide
├── RUNBOOK.md             # Operations runbook
├── CONTRIBUTING.md        # Contribution guide
└── adr/                   # Architecture Decision Records
    ├── README.md          # ADR index
    ├── 001-*.md           # Individual ADRs
    └── ...
```

---

## 🔄 Keeping Docs Updated

Documentation should be updated when:
- Adding new API endpoints → Update [API.md](./API.md)
- Changing database schema → Update [DATABASE.md](./DATABASE.md)
- Making architecture decisions → Add new [ADR](./adr/)
- Adding new features → Update relevant service README
- Changing operations procedures → Update [RUNBOOK.md](./RUNBOOK.md)

---

## 📞 Support

- **Technical Questions**: Check documentation first, then ask in team Slack
- **Bug Reports**: Report with reproduction steps
- **Feature Requests**: Describe the use case and requirements

---

