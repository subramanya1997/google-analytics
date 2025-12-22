# Google Analytics Intelligence System - Backend

A comprehensive backend system for processing Google Analytics data and generating actionable business intelligence reports. Built with FastAPI, PostgreSQL, and a microservices architecture.

## 🏗️ Architecture Overview

The backend consists of three main microservices:

- **Analytics Service** (Port 8001): Report generation, email management, and analytics processing
- **Data Service** (Port 8002): Google Analytics data ingestion and processing
- **Auth Service** (Port 8003): Authentication, authorization, and tenant management

### Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with custom functions
- **Package Manager**: uv (ultra-fast Python package manager)
- **ORM**: SQLAlchemy with raw SQL for performance
- **Authentication**: OAuth 2.0 flow
- **Email**: SMTP with HTML template rendering (Jinja2)
- **Logging**: Loguru with structured logging
- **API Documentation**: Automatic OpenAPI/Swagger docs

## 📋 Prerequisites

### Required Software

1. **Python 3.11 or higher**
   ```bash
   python --version  # Should be 3.11+
   ```

2. **uv Package Manager**
   ```bash
   # Install uv (if not already installed)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Or via pip
   pip install uv
   ```

3. **PostgreSQL 14 or higher**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   
   # macOS (with Homebrew)
   brew install postgresql
   brew services start postgresql
   
   # Windows
   # Download from https://www.postgresql.org/download/windows/
   ```

### Database Setup

1. **Create Database and User**
   ```sql
   -- Connect to PostgreSQL as superuser
   sudo -u postgres psql
   
   -- Create database
   CREATE DATABASE google_analytics_db;
   
   -- Create user with password
   CREATE USER analytics_user WITH PASSWORD 'your_secure_password';
   
   -- Grant privileges
   GRANT ALL PRIVILEGES ON DATABASE google_analytics_db TO analytics_user;
   GRANT CREATE ON SCHEMA public TO analytics_user;
   
   -- Exit psql
   \q
   ```

2. **Environment Configuration**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env with your database credentials
   nano .env
   ```

   Required environment variables:
   ```env
   # Database Configuration (PostgreSQL)
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=analytics_user
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DATABASE=google_analytics_db
   
   # Database Connection Pool Settings
   DATABASE_POOL_SIZE=10
   DATABASE_MAX_OVERFLOW=5
   
   # Service Configuration
   ANALYTICS_SERVICE_PORT=8001
   DATA_SERVICE_PORT=8002
   AUTH_SERVICE_PORT=8003
   
   # Environment Settings
   ENVIRONMENT=DEV
   DEBUG=false
   LOG_LEVEL=INFO
   
   # CORS Origins (comma-separated)
   CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   
   # Auth Service Base URL
   BASE_URL=https://your-domain.com
   ```

## 🚀 Installation & Setup

### 1. Clone and Navigate
```bash
git clone <repository_url>
cd google-analytics/backend
```

### 2. Install Dependencies
```bash
# Install all dependencies including development tools
uv sync --dev

# Or just production dependencies
uv sync
```

### 3. Database Schema Setup
```bash
# Initialize database tables and functions
make db_setup

# Or manually
uv run python scripts/init_db.py
```

### 4. Verify Installation
```bash
# Test database connection
uv run python -c "
from common.database.session import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1')).scalar()
    print(f'Database connection successful: {result}')
"
```

## 🎯 Quick Start

### Start All Services (Development)
```bash
# Using Makefile (recommended)
make services_start

# Or start individual services
make service_analytics  # Port 8001
make service_data      # Port 8002  
make service_auth      # Port 8003
```

### Start Individual Services
```bash
# Analytics Service
cd backend
uv run uvicorn services.analytics_service:app --port 8001 --reload

# Data Service  
cd backend
uv run uvicorn services.data_service:app --port 8002 --reload

# Auth Service
cd backend
uv run uvicorn services.auth_service:app --port 8003 --reload
```

### Access API Documentation
- **Analytics Service**: http://localhost:8001/docs
- **Data Service**: http://localhost:8002/docs
- **Auth Service**: http://localhost:8003/docs

## 📊 Service Details

### Analytics Service (Port 8001)

**Purpose**: Generate reports, manage email campaigns, and provide analytics insights.

**Key Features**:
- Branch-wise sales report generation
- Email template rendering and sending
- Task management (purchases, cart abandonment, search analysis)
- Performance analytics

**Main Endpoints**:
```
GET  /analytics/locations           # Get active locations
GET  /analytics/stats              # Dashboard statistics
GET  /analytics/tasks/purchases    # Purchase follow-up tasks
GET  /analytics/tasks/cart-abandonment  # Cart recovery tasks
GET  /analytics/tasks/search-analysis   # Search optimization tasks
GET  /analytics/tasks/repeat-visits     # Repeat visitor engagement
POST /analytics/email/send-reports     # Send email reports
GET  /analytics/email/mappings         # Branch email mappings
```

**Database Functions Used**:
- `get_purchase_tasks()`
- `get_cart_abandonment_tasks()`
- `get_search_analysis_tasks()`
- `get_repeat_visit_tasks()`
- `get_complete_dashboard_data()`

### Data Service (Port 8002)

**Purpose**: Ingest and process Google Analytics data.

**Key Features**:
- Google Analytics 4 data ingestion
- Event processing and transformation
- User and session management
- Data availability reporting

**Main Endpoints**:
```
POST /data/ingest/start           # Start data ingestion job
GET  /data/ingest/jobs           # Get ingestion job status
GET  /data/availability         # Check data availability
POST /data/events               # Manual event submission
GET  /data/users/{user_id}      # Get user details
```

**Data Processing**:
- Page views, purchases, cart events
- Search events and user interactions
- Location-based event filtering
- Real-time and batch processing

### Auth Service (Port 8003)

**Purpose**: Handle authentication, tenant management, and access control.

**Key Features**:
- OAuth 2.0 authentication flow
- Multi-tenant architecture
- JWT token management
- User profile management

**Main Endpoints**:
```
GET  /auth/login                # Get OAuth login URL
POST /auth/callback             # Handle OAuth callback
POST /auth/logout               # Logout user
GET  /auth/me                   # Get current user info
GET  /auth/tenants              # Tenant management
```

## 🗄️ Database Schema

### Core Tables

1. **tenants** - Multi-tenant configuration
   ```sql
   - id (UUID, primary key)
   - name (text)
   - email_config (jsonb)
   - google_analytics_config (jsonb)
   - created_at, updated_at (timestamp)
   ```

2. **users** - User profiles and contact information
   ```sql
   - user_id (text, primary key)
   - tenant_id (UUID, foreign key)
   - buying_company_name (text)
   - email, cell_phone, office_phone (text)
   - created_at, updated_at (timestamp)
   ```

3. **locations** - Branch/location information
   ```sql
   - location_id (text, primary key)
   - tenant_id (UUID, foreign key)
   - location_name, city, state (text)
   - created_at, updated_at (timestamp)
   ```

### Event Tables

4. **page_view** - Website page view events
5. **purchase** - E-commerce purchase events
6. **add_to_cart** - Cart addition events
7. **view_item** - Product view events
8. **view_search_results** - Search result views
9. **no_search_results** - Failed search events

### Email Management Tables

10. **branch_email_mappings** - Branch to sales rep mappings
11. **email_sending_jobs** - Email job tracking
12. **email_send_history** - Individual email send records

### Database Functions

The system uses PostgreSQL functions for optimized queries:

- `get_purchase_tasks()` - Retrieve purchase follow-up tasks
- `get_cart_abandonment_tasks()` - Get abandoned cart recovery tasks
- `get_search_analysis_tasks()` - Analyze search patterns
- `get_repeat_visit_tasks()` - Identify repeat visitor opportunities
- `get_complete_dashboard_data()` - Comprehensive dashboard metrics
- `get_locations_with_activity_table()` - Active locations

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Database Configuration (PostgreSQL)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=analytics_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DATABASE=google_analytics_db

# Database Connection Pool Settings
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=5

# Service Ports
ANALYTICS_SERVICE_PORT=8001
DATA_SERVICE_PORT=8002
AUTH_SERVICE_PORT=8003

# Environment Settings
ENVIRONMENT=DEV
DEBUG=false
LOG_LEVEL=INFO

# CORS Origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Google Analytics Configuration
GOOGLE_ANALYTICS_PROPERTY_ID=123456789
GOOGLE_ANALYTICS_CREDENTIALS_PATH=/path/to/service-account.json

# OAuth (Auth Service)
OAUTH_CLIENT_ID=your_oauth_client_id
OAUTH_CLIENT_SECRET=your_oauth_client_secret
OAUTH_REDIRECT_URI=http://localhost:3000/oauth/callback

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Auth Service Base URL
BASE_URL=https://your-domain.com

# Email Configuration (Optional - can be configured via API)
DEFAULT_SMTP_SERVER=smtp.gmail.com
DEFAULT_SMTP_PORT=587
DEFAULT_FROM_EMAIL=reports@company.com
DEFAULT_SMTP_USERNAME=username
DEFAULT_SMTP_PASSWORD=password
DEFAULT_USE_TLS=true
```

### Google Analytics Setup

1. **Create Service Account**:
   - Go to Google Cloud Console
   - Create a new project or select existing
   - Enable Google Analytics Reporting API
   - Create service account with Analytics Viewer role
   - Download JSON credentials file

2. **Configure Analytics Property**:
   - Add service account email to GA4 property with Viewer permissions
   - Note your GA4 Property ID (found in GA4 Admin → Property Settings)

### Email Configuration

Email settings can be configured in two ways:

1. **Via Environment Variables** (system-wide default)
2. **Via API** (per-tenant configuration)

```python
# Example API configuration
POST /analytics/email/config
{
  "server": "smtp.gmail.com",
  "port": 587,
  "from_address": "reports@company.com",
  "username": "username",
  "password": "app_password",
  "use_tls": true
}
```

## 🚦 Running the Services

### Development Mode (All Services)
```bash
# Start all services with auto-reload
make services_start

# Or manually start each service
make service_analytics &
make service_data &
make service_auth &
```

### Production Mode
```bash
# Install production dependencies only
uv sync --no-dev

# Start with production settings
uv run uvicorn services.analytics_service:app --host 0.0.0.0 --port 8001
uv run uvicorn services.data_service:app --host 0.0.0.0 --port 8002
uv run uvicorn services.auth_service:app --host 0.0.0.0 --port 8003
```

## 🔍 API Usage Examples

### Authentication Flow
```bash
# 1. Get login URL
curl -X GET "http://localhost:8003/auth/login"

# 2. User visits returned URL and authorizes

# 3. Handle callback (done by frontend)
curl -X POST "http://localhost:8003/auth/callback" \
  -H "Content-Type: application/json" \
  -d '{"code": "auth_code_from_oauth"}'

# 4. Use returned token for subsequent requests
export TOKEN="your_jwt_token"
export TENANT_ID="your_tenant_id"
```

### Data Ingestion
```bash
# Start data ingestion for date range
curl -X POST "http://localhost:8002/data/ingest/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "data_types": ["events", "users", "locations"]
  }'

# Check ingestion status
curl -X GET "http://localhost:8002/data/ingest/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID"
```

### Analytics and Reporting
```bash
# Get dashboard statistics
curl -X GET "http://localhost:8001/analytics/stats?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID"

# Get purchase tasks
curl -X GET "http://localhost:8001/analytics/tasks/purchases?page=1&limit=50" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID"

# Send email reports
curl -X POST "http://localhost:8001/analytics/email/send-reports" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "report_date": "2024-01-31",
    "branch_codes": ["D01", "D02"]
  }'
```

## 📁 Project Structure

```
backend/
├── common/                     # Shared utilities and configurations
│   ├── config/                # Configuration management
│   ├── database/             # Database connection and session management
│   ├── fastapi/             # FastAPI common utilities
│   ├── models/              # Shared data models
│   └── logging.py           # Centralized logging configuration
├── database/                 # Database schema and functions
│   ├── tables/              # Table creation scripts
│   └── functions/           # PostgreSQL function definitions
├── scripts/                  # Database management scripts
│   ├── init_db.py           # Initialize database schema
│   └── clear_db.py          # Clean database (development)
├── services/                 # Microservices
│   ├── analytics_service/    # Analytics and reporting service
│   ├── data_service/         # Data ingestion service
│   └── auth_service/         # Authentication service
├── logs/                     # Service logs (auto-created)
├── pyproject.toml           # Python project configuration
├── uv.lock                  # Dependency lock file
└── README.md               # This file
```

## 🔧 Development

### Code Style and Quality
```bash
# Install development dependencies
uv sync --dev

# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy .
```

### Database Operations
```bash
# Setup database
make db_setup

# Clean database (WARNING: Deletes all data)
make db_clean

# Manual database operations
uv run python scripts/init_db.py
uv run python scripts/clear_db.py
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check PostgreSQL is running
   sudo systemctl status postgresql  # Linux
   brew services list | grep postgres  # macOS
   
   # Test connection (using environment variables)
   psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DATABASE
   
   # Or with explicit values
   psql -h localhost -U analytics_user -d google_analytics_db
   ```

2. **Port Already in Use**
   ```bash
   # Find process using port
   lsof -i :8001
   
   # Kill process
   kill -9 <PID>
   
   # Or use different port
   uv run uvicorn services.analytics_service:app --port 8011 --reload
   ```

3. **Module Import Errors**
   ```bash
   # Ensure you're in the backend directory
   cd backend
   
   # Reinstall dependencies
   uv sync --dev
   ```

### Logging and Debugging

**View Logs**:
```bash
# Real-time log viewing
tail -f backend/logs/analytics-service.log
tail -f backend/logs/analytics-service-error.log

# View all error logs
make logs

# Search logs for specific errors
grep -r "ERROR" backend/logs/
```

**Debug Mode**:
```bash
# Start service with debug logging
LOG_LEVEL=DEBUG uv run uvicorn services.analytics_service:app --port 8001 --reload
```

## 🚀 Deployment

### Production Checklist

1. **Environment Setup**:
   - [ ] Set production environment variables
   - [ ] Configure production database
   - [ ] Set up SSL certificates
   - [ ] Configure reverse proxy (nginx)

2. **Security**:
   - [ ] Change default passwords
   - [ ] Use strong JWT secret keys
   - [ ] Enable HTTPS
   - [ ] Configure firewall rules
   - [ ] Set up database backups

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feat/new-feature`
3. Make changes and add tests
4. Run quality checks: `make lint test`
5. Commit changes: `git commit -m "Add new feature"`
6. Push to branch: `git push origin feat/new-feature`
7. Create Pull Request

### Code Standards
- Follow PEP 8 style guide
- Add type hints to all functions
- Write docstrings for public methods
- Add unit tests for new functionality
- Update API documentation

## 📞 Support

### Getting Help
- Check the logs first: `make logs`
- Review API documentation: `http://localhost:800X/docs`
- Check database connections and permissions
- Verify environment variable configuration

### Common Commands Summary
```bash
# Full setup from scratch
make setup

# Start development environment
make dev

# Database operations
make db_setup
make db_clean

# Individual services
make service_analytics
make service_data  
make service_auth

# Maintenance
make clean
make logs
```

This backend system provides a robust, scalable foundation for Google Analytics intelligence with comprehensive reporting, email automation, and multi-tenant support.
