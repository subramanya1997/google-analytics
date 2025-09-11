# Google Analytics Intelligence System

A comprehensive sales intelligence and analytics platform that transforms Google Analytics 4 data into actionable business insights. Built with a modern microservices architecture featuring FastAPI backend services and a Next.js dashboard for optimal performance and scalability.

## 🎯 Overview

This system empowers sales teams with data-driven insights by processing Google Analytics data to identify sales opportunities, track customer behavior, and automate follow-up tasks. The platform supports multi-tenant, multi-location operations with advanced reporting and email automation capabilities.

## ✨ Key Features

### 🏗️ Microservices Architecture
- **Analytics Service**: Report generation, task management, and email automation
- **Data Service**: Google Analytics data ingestion and processing
- **Auth Service**: OAuth authentication and multi-tenant management
- **Dashboard**: Modern React-based web interface

### 📊 Business Intelligence
- **Real-time Analytics**: Revenue, purchases, cart abandonment, search patterns
- **Location-based Insights**: Branch/warehouse performance comparison
- **Customer Journey Tracking**: Complete user behavior analysis
- **Performance Monitoring**: UX metrics and optimization opportunities

### 📋 Task Management
- **Purchase Follow-ups**: Automated customer contact workflows
- **Cart Recovery**: Abandoned cart recovery campaigns
- **Search Optimization**: Failed search term analysis and improvement
- **Repeat Visitor Conversion**: High-engagement visitor targeting
- **Performance Issues**: UX problem identification and resolution

### 📧 Email Automation
- **Branch-wise Reports**: Automated HTML report generation and sending
- **Sales Rep Mapping**: Configure report recipients by branch
- **Email Tracking**: Complete audit trail with delivery status
- **Template Management**: Customizable HTML email templates

### 🔧 Data Management
- **GA4 Integration**: Direct Google Analytics 4 data ingestion
- **Multi-tenant Support**: Isolated data access per organization
- **Job Monitoring**: Real-time data processing status
- **Data Availability**: Historical data range tracking

## 🛠️ Technology Stack

### Backend Services
- **FastAPI**: High-performance Python web framework
- **PostgreSQL**: Advanced database with custom functions
- **SQLAlchemy**: ORM with raw SQL optimization
- **uv**: Ultra-fast Python package manager
- **Jinja2**: HTML template rendering for emails
- **Loguru**: Structured logging and monitoring

### Frontend Dashboard
- **Next.js 15**: React framework with App Router
- **TypeScript**: Complete type safety
- **Tailwind CSS 4**: Utility-first styling
- **Shadcn/ui**: High-quality component library
- **Recharts**: Interactive data visualization
- **TanStack Query**: Server state management

### Infrastructure
- **OAuth 2.0**: Secure authentication flow
- **JWT**: Token-based authorization
- **SMTP**: Email delivery with template rendering
- **API Proxies**: Seamless frontend-backend communication

## 📋 Prerequisites

### System Requirements
- **Python 3.11+** with uv package manager
- **Node.js 18+** with npm/yarn
- **PostgreSQL 14+** database server
- **Google Analytics 4** property with API access

### Setup Dependencies
```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Node.js (via nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
```

## 🚀 Quick Start

### 1. Clone Repository
   ```bash
git clone <repository_url>
   cd google-analytics
   ```

### 2. Complete Setup
```bash
# Install all dependencies and setup database
make setup
```

### 3. Start Development Environment
   ```bash
# Start all services (backend + frontend)
make dev
```

### 4. Access Applications
- **Dashboard**: http://localhost:3000
- **Analytics API**: http://localhost:8001/docs
- **Data API**: http://localhost:8002/docs
- **Auth API**: http://localhost:8003/docs

## 🔧 Configuration

### Environment Variables

#### Backend Configuration (`backend/.env`)
```env
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=analytics_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DATABASE=google_analytics_db

# Service Ports
ANALYTICS_SERVICE_PORT=8001
DATA_SERVICE_PORT=8002
AUTH_SERVICE_PORT=8003

# Environment Settings
ENVIRONMENT=DEV
DEBUG=false
LOG_LEVEL=INFO

# CORS Origins (for frontend integration)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Auth Service Configuration
BASE_URL=https://your-domain.com
```

#### Frontend Configuration (`dashboard/.env.local`)
```env
# Backend API URLs
NEXT_PUBLIC_ANALYTICS_API_URL=http://localhost:8001/api/v1
NEXT_PUBLIC_DATA_API_URL=http://localhost:8002/api/v1
NEXT_PUBLIC_AUTH_API_URL=http://localhost:8003/api/v1

# Optional: Default tenant for development
NEXT_PUBLIC_TENANT_ID=your_default_tenant_id
```

### Database Setup

1. **Create PostgreSQL Database**
   ```sql
   CREATE DATABASE google_analytics_db;
   CREATE USER analytics_user WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE google_analytics_db TO analytics_user;
   ```

2. **Initialize Schema**
   ```bash
   make db_setup
   ```

## 📁 Project Structure

```
google-analytics/
├── Makefile                    # Build automation and service management
├── README.md                   # This file
├── .gitignore                  # Git ignore patterns
│
├── backend/                    # Backend microservices
│   ├── common/                # Shared utilities and configurations
│   │   ├── config/           # Settings management
│   │   ├── database/         # Database connections and sessions
│   │   ├── fastapi/          # FastAPI common utilities
│   │   ├── models/           # Shared data models
│   │   └── logging.py        # Centralized logging
│   ├── database/             # Database schema and functions
│   │   ├── tables/          # PostgreSQL table definitions
│   │   └── functions/       # Optimized database functions
│   ├── scripts/             # Database management scripts
│   │   ├── init_db.py      # Schema initialization
│   │   └── clear_db.py     # Database cleanup
│   ├── services/            # Microservices
│   │   ├── analytics_service/ # Analytics and reporting
│   │   ├── data_service/     # Data ingestion and processing
│   │   └── auth_service/     # Authentication and authorization
│   ├── logs/                # Service logs (auto-generated)
│   ├── pyproject.toml       # Python project configuration
│   ├── uv.lock             # Dependency lock file
│   └── README.md           # Backend documentation
│
├── dashboard/               # Frontend web application
│   ├── src/
│   │   ├── app/            # Next.js App Router pages
│   │   │   ├── (dashboard)/ # Main dashboard pages
│   │   │   ├── oauth/      # Authentication pages
│   │   │   └── layout.tsx  # Root layout
│   │   ├── components/     # React components
│   │   │   ├── charts/    # Data visualization
│   │   │   ├── email-management/ # Email features
│   │   │   ├── tasks/     # Task management
│   │   │   └── ui/        # Base UI components
│   │   ├── contexts/      # React Context providers
│   │   ├── hooks/         # Custom React hooks
│   │   ├── lib/           # Utility functions
│   │   └── types/         # TypeScript definitions
│   ├── public/            # Static assets
│   ├── package.json       # Frontend dependencies
│   ├── next.config.ts     # Next.js configuration
│   └── README.md          # Frontend documentation
```

## 🎛️ Available Commands

### Database Management
```bash
make db_setup              # Initialize database schema and functions
make db_clean              # Clean/drop all database tables (WARNING: Deletes data)
```

### Backend Services
```bash
make install_backend       # Install Python dependencies with uv
make services_start        # Start all three backend services
make service_analytics     # Start analytics service only (port 8001)
make service_data         # Start data service only (port 8002)
make service_auth         # Start auth service only (port 8003)
make stop_services        # Stop all running services
```

### Frontend Dashboard
```bash
make install_dashboard     # Install Node.js dependencies
make run_dashboard        # Start development server (port 3000)
make build_dashboard      # Build for production
make start_dashboard      # Start production server
```

### Development Workflow
```bash
make setup                # Complete setup (backend + frontend + database)
make dev                  # Start full development environment
make clean                # Clean logs and temporary files
make logs                 # View service logs
make help                 # Show all available commands
```

## 🔌 API Services

### Analytics Service (Port 8001)
**Purpose**: Business intelligence, reporting, and email automation

**Key Endpoints**:
- `GET /analytics/stats` - Dashboard statistics and metrics
- `GET /analytics/locations` - Active branch locations
- `GET /analytics/tasks/purchases` - Purchase follow-up tasks
- `GET /analytics/tasks/cart-abandonment` - Cart recovery tasks
- `GET /analytics/tasks/search-analysis` - Search optimization tasks
- `GET /analytics/tasks/repeat-visits` - Repeat visitor engagement
- `POST /analytics/email/send-reports` - Send automated reports
- `GET /analytics/email/mappings` - Branch email configurations

### Data Service (Port 8002)
**Purpose**: Google Analytics data ingestion and processing

**Key Endpoints**:
- `POST /data/ingest/start` - Start data ingestion job
- `GET /data/ingest/jobs` - Monitor ingestion job status
- `GET /data/availability` - Check available data ranges
- `POST /data/events` - Manual event submission
- `GET /data/users/{user_id}` - User profile information

### Auth Service (Port 8003)
**Purpose**: Authentication, authorization, and tenant management

**Key Endpoints**:
- `GET /auth/login` - Get OAuth login URL
- `POST /auth/callback` - Handle OAuth callback
- `POST /auth/logout` - User logout
- `GET /auth/me` - Current user information
- `GET /auth/tenants` - Tenant management

## 🔍 Usage Examples

### Authentication Flow
```bash
# 1. Get login URL
curl http://localhost:8003/auth/login

# 2. After OAuth authorization, get token
export TOKEN="your_jwt_token"
export TENANT_ID="your_tenant_id"
```

### Data Ingestion
```bash
# Start Google Analytics data import
curl -X POST "http://localhost:8002/data/ingest/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "data_types": ["events", "users", "locations"]
  }'
```

### Analytics & Reporting
```bash
# Get dashboard statistics
curl -X GET "http://localhost:8001/analytics/stats?start_date=2024-01-01&end_date=2024-01-31" \
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

## 🎨 Dashboard Features

### Main Dashboard
- **Metrics Overview**: Revenue, purchases, abandonment rates, visitor counts
- **Activity Timeline**: Interactive charts with hourly/daily/weekly granularity
- **Location Performance**: Branch-wise performance comparison
- **Real-time Updates**: Live data refresh and status monitoring

### Task Management
- **Purchase Tasks**: Customer follow-up with contact details and order history
- **Cart Recovery**: Abandoned cart workflows with item details and customer info
- **Search Analysis**: Failed search optimization with customer context
- **Repeat Visitors**: High-engagement visitor conversion opportunities
- **Performance Issues**: Page bounce rate analysis and UX improvements

### Email Management
- **Branch Mappings**: Configure sales representative assignments
- **Report Automation**: Schedule and send branch-specific reports
- **Email History**: Complete audit trail with delivery status
- **Job Monitoring**: Track email sending progress and errors

### Data Management
- **Import Controls**: Google Analytics data ingestion management
- **Job Monitoring**: Real-time processing status and progress
- **Data Availability**: Historical data range and statistics
- **Error Handling**: Failed job recovery and retry mechanisms

## 🔐 Security Features

### Authentication & Authorization
- **OAuth 2.0**: Secure authentication with external providers
- **JWT Tokens**: Stateless authentication with configurable expiration
- **Multi-tenant**: Complete data isolation between organizations
- **Role-based Access**: Granular permissions and access control

### Data Security
- **SQL Injection Protection**: Parameterized queries throughout
- **CORS Configuration**: Controlled cross-origin access
- **Input Validation**: Comprehensive data validation and sanitization
- **Audit Trails**: Complete logging of all user actions

## 🚀 Deployment

### Development
```bash
# Complete development setup
make setup

# Start all services
make dev

# Individual service management
make service_analytics    # Port 8001
make service_data        # Port 8002
make service_auth        # Port 8003
make run_dashboard       # Port 3000
```

### Production
```bash
# Backend services
uv run uvicorn services.analytics_service:app --host 0.0.0.0 --port 8001
uv run uvicorn services.data_service:app --host 0.0.0.0 --port 8002
uv run uvicorn services.auth_service:app --host 0.0.0.0 --port 8003

# Frontend dashboard
npm run build && npm start
```

### Docker Deployment
```yaml
# docker-compose.yml
version: '3.8'
services:
  analytics-service:
    build: ./backend
    ports:
      - "8001:8001"
    environment:
      - SERVICE_TYPE=analytics
  
  data-service:
    build: ./backend
    ports:
      - "8002:8002"
    environment:
      - SERVICE_TYPE=data
  
  auth-service:
    build: ./backend
    ports:
      - "8003:8003"
    environment:
      - SERVICE_TYPE=auth
  
  dashboard:
    build: ./dashboard
    ports:
      - "3000:3000"
    depends_on:
      - analytics-service
      - data-service
      - auth-service
```

## 📊 Data Flow Architecture

```
Google Analytics 4
        ↓
Data Service (Port 8002)
        ↓
PostgreSQL Database
        ↓
Analytics Service (Port 8001)
        ↓
Email Reports & Dashboard API
        ↓
Dashboard (Port 3000)
        ↓
Sales Team Interface
```

### Authentication Flow
```
User → Dashboard → Auth Service → OAuth Provider → Callback → JWT Token → Authenticated Session
```

### Report Generation Flow
```
Schedule → Analytics Service → Database Query → Template Rendering → Email Service → SMTP → Recipients
```

## 🔧 Configuration

### Required Setup

1. **PostgreSQL Database**
   ```sql
   CREATE DATABASE google_analytics_db;
   CREATE USER analytics_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE google_analytics_db TO analytics_user;
   ```

2. **Environment Files**
   ```bash
   # Backend configuration
   cp backend/.env.example backend/.env
   
   # Frontend configuration  
   cp dashboard/env.example dashboard/.env.local
   ```

3. **Google Analytics Setup**
   - Create service account in Google Cloud Console
   - Enable Google Analytics Reporting API
   - Add service account to GA4 property with Viewer role
   - Download credentials JSON file

4. **OAuth Configuration**
   - Configure OAuth application in your provider
   - Set redirect URI to `http://localhost:3000/oauth/callback`
   - Add client ID and secret to environment variables

## 🎮 Usage

### Daily Operations

1. **Start System**
   ```bash
   make dev  # Starts all services and dashboard
   ```

2. **Access Dashboard**
   - Navigate to http://localhost:3000
   - Login via OAuth flow
   - View analytics and manage tasks

3. **Data Management**
   - Monitor data ingestion jobs
   - Configure branch email mappings
   - Send manual reports

4. **Task Management**
   - Review purchase follow-ups
   - Process cart abandonment recovery
   - Analyze search optimization opportunities
   - Engage repeat visitors

### Administrative Tasks

```bash
# Database operations
make db_setup              # Initialize schema
make db_clean              # Reset database

# Service management
make services_start        # Start backend services
make stop_services         # Stop all services

# Maintenance
make clean                 # Clear logs and cache
make logs                  # View service logs
```

## 🧪 Development

### Adding New Features

#### Backend API Endpoint
1. Create endpoint in appropriate service (`services/analytics_service/api/v1/endpoints/`)
2. Add database function if needed (`database/functions/`)
3. Register endpoint in API router (`services/analytics_service/api/v1/api.py`)
4. Update database client (`services/analytics_service/database/postgres_client.py`)

#### Frontend Page/Component
1. Create page in `dashboard/src/app/(dashboard)/`
2. Add navigation link in `dashboard/src/components/app-sidebar.tsx`
3. Create components in `dashboard/src/components/`
4. Add API functions in `dashboard/src/lib/api-utils.ts`
5. Define types in `dashboard/src/types/`

### Testing
```bash
# Backend testing
cd backend
uv run pytest

# Frontend testing
cd dashboard
npm run lint
npm run build
```

## 🐛 Troubleshooting

### Common Issues

1. **Services Won't Start**
   ```bash
   # Check if ports are in use
   lsof -i :8001 :8002 :8003 :3000
   
   # Kill conflicting processes
   make stop_services
   ```

2. **Database Connection Failed**
   ```bash
   # Verify PostgreSQL is running
   sudo systemctl status postgresql  # Linux
   brew services list | grep postgres  # macOS
   
   # Test connection
   psql -h localhost -U analytics_user -d google_analytics_db
   ```

3. **Authentication Issues**
   ```bash
   # Check auth service logs
   tail -f backend/logs/auth-service-error.log
   
   # Verify OAuth configuration
   curl http://localhost:8003/auth/login
   ```

4. **Frontend Build Errors**
   ```bash
   # Clear Next.js cache
   cd dashboard
   rm -rf .next
   npm install
   npm run build
   ```

### Debug Mode
```bash
# Start services with debug logging
LOG_LEVEL=DEBUG make services_start

# Start dashboard with verbose output
cd dashboard
npm run dev -- --verbose
```

## 📈 Performance & Monitoring

### Health Checks
```bash
# Service health endpoints
curl http://localhost:8001/health  # Analytics
curl http://localhost:8002/health  # Data
curl http://localhost:8003/health  # Auth
```

### Monitoring
- Service logs in `backend/logs/`
- Database performance via PostgreSQL stats
- Frontend performance via Next.js analytics
- Email delivery tracking via audit trails

### Backup & Recovery
```bash
# Database backup
pg_dump -h localhost -U analytics_user google_analytics_db > backup.sql

# Restore database
psql -h localhost -U analytics_user google_analytics_db < backup.sql
```

## 🔒 Security

### Built-in Security Features
- **SQL Injection Protection**: Parameterized queries
- **XSS Prevention**: Input sanitization and output encoding
- **CSRF Protection**: Token-based request validation
- **Authentication**: OAuth 2.0 with JWT tokens
- **Authorization**: Multi-tenant data isolation
- **Audit Logging**: Complete action tracking

### Production Security Checklist
- [ ] Use HTTPS for all services
- [ ] Configure strong JWT secrets
- [ ] Set up database SSL connections
- [ ] Enable rate limiting
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Regular security updates

## 🤝 Contributing

### Development Process
1. **Fork Repository**
2. **Create Feature Branch**: `git checkout -b feature/new-feature`
3. **Setup Development Environment**: `make setup`
4. **Make Changes**: Follow coding standards
5. **Test Changes**: Run tests and quality checks
6. **Submit PR**: Include description and testing notes

### Code Standards
- **Backend**: PEP 8, type hints, docstrings, unit tests
- **Frontend**: ESLint rules, TypeScript strict mode, component documentation
- **Database**: Normalized schema, indexed queries, function documentation
- **API**: OpenAPI documentation, consistent response formats

## 📞 Support

### Getting Help
1. **Check Logs**: `make logs`
2. **Review Documentation**: Service-specific README files
3. **Test Connectivity**: Use health check endpoints
4. **Verify Configuration**: Check environment variables

### Quick Reference
```bash
# Complete setup from scratch
make setup && make dev

# Restart all services
make stop_services && make services_start

# Reset database (development only)
make db_clean && make db_setup

# View all available commands
make help
```

## 🏆 Features Summary

This system provides:
- **Real-time Analytics**: Live dashboard with comprehensive metrics
- **Task Automation**: Automated customer follow-up workflows
- **Email Intelligence**: Automated report generation and delivery
- **Multi-tenant Support**: Isolated, scalable architecture
- **Performance Monitoring**: UX optimization insights
- **Data Integration**: Seamless Google Analytics 4 connectivity

Built for modern sales teams who need actionable insights, automated workflows, and comprehensive customer intelligence to drive revenue growth and improve customer experience.

---

For detailed service-specific documentation, see:
- [Backend Documentation](backend/README.md)
- [Frontend Documentation](dashboard/README.md)