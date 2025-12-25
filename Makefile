.PHONY: help install_backend install_dashboard build_dashboard run_dashboard start_dashboard db_setup db_clean start_services start_service_analytics start_service_data start_service_auth stop_services clean logs lint format type-check security-check test test-cov quality-check pre-commit-install

# Variables
BACKEND_DIR = backend
DASHBOARD_DIR = dashboard
SCRIPTS_DIR = $(BACKEND_DIR)/scripts

# Default target
all: help

# Help target
help:
	@echo "Google Analytics Intelligence System - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@echo "Database Management:"
	@echo "  db_setup               - Initialize database schema and functions"
	@echo "  db_clean               - Clean/drop all database tables and functions"
	@echo ""
	@echo "Backend Services:"
	@echo "  install_backend        - Install Python dependencies with uv"
	@echo "  start_services         - Start all three backend services"
	@echo "  start_service_analytics - Start analytics service only (port 8001)"
	@echo "  start_service_data     - Start data service only (port 8002)"
	@echo "  start_service_auth     - Start auth service only (port 8003)"
	@echo "  stop_services          - Stop all running services"
	@echo ""
	@echo "Frontend Dashboard:"
	@echo "  install_dashboard      - Install Node.js dependencies"
	@echo "  run_dashboard          - Start development server"
	@echo "  build_dashboard        - Build for production"
	@echo "  start_dashboard        - Start production server"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint                   - Run linters (ruff)"
	@echo "  format                 - Format code (ruff format)"
	@echo "  type-check             - Run type checker (mypy)"
	@echo "  security-check         - Run security scanner (bandit)"
	@echo "  test                   - Run tests"
	@echo "  test-cov               - Run tests with coverage"
	@echo "  quality-check          - Run all quality checks"
	@echo "  pre-commit-install     - Install pre-commit hooks"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean                  - Clean logs and temporary files"
	@echo "  logs                   - View service logs"

# ================================
# DATABASE MANAGEMENT
# ================================

db_setup:
	@echo "Setting up database schema and functions..."
	cd $(BACKEND_DIR) && uv run python scripts/init_db.py

db_clean:
	@echo "Cleaning database (WARNING: This will delete all data)..."
	cd $(BACKEND_DIR) && uv run python scripts/clear_db.py

# ================================
# BACKEND SERVICES
# ================================

install_backend:
	@echo "Installing backend dependencies with uv..."
	cd $(BACKEND_DIR) && uv sync --dev

start_services:
	@echo "Starting all backend services..."
	@echo "Analytics Service: http://localhost:8001"
	@echo "Data Service: http://localhost:8002" 
	@echo "Auth Service: http://localhost:8003"
	@echo ""
	@echo "Press Ctrl+C to stop all services"
	cd $(BACKEND_DIR) && \
	(uv run uvicorn services.analytics_service:app --port 8001 --reload &) && \
	(uv run uvicorn services.data_service:app --port 8002 --reload &) && \
	(uv run uvicorn services.auth_service:app --port 8003 --reload &) && \
	wait

start_service_analytics:
	@echo "Starting Analytics Service on port 8001..."
	@echo "API docs: http://localhost:8001/docs"
	cd $(BACKEND_DIR) && uv run uvicorn services.analytics_service:app --port 8001 --reload

start_service_data:
	@echo "Starting Data Service on port 8002..."
	@echo "API docs: http://localhost:8002/docs"
	cd $(BACKEND_DIR) && uv run uvicorn services.data_service:app --port 8002 --reload

start_service_auth:
	@echo "Starting Auth Service on port 8003..."
	@echo "API docs: http://localhost:8003/docs"
	cd $(BACKEND_DIR) && uv run uvicorn services.auth_service:app --port 8003 --reload

stop_services:
	@echo "Stopping all backend services..."
	@pkill -f "uvicorn.*analytics_service" || true
	@pkill -f "uvicorn.*data_service" || true
	@pkill -f "uvicorn.*auth_service" || true
	@echo "All services stopped"

# ================================
# FRONTEND DASHBOARD
# ================================

install_dashboard:
	@echo "Installing dashboard dependencies..."
	cd $(DASHBOARD_DIR) && npm install

run_dashboard:
	@echo "Starting dashboard development server..."
	@echo "Dashboard: http://localhost:3000"
	cd $(DASHBOARD_DIR) && npm run dev

build_dashboard:
	@echo "Building dashboard for production..."
	cd $(DASHBOARD_DIR) && npm run build

start_dashboard:
	@echo "Starting dashboard production server..."
	cd $(DASHBOARD_DIR) && npm start

# ================================
# DEVELOPMENT WORKFLOW
# ================================

dev: install_backend install_dashboard
	@echo "Starting full development environment..."
	@echo ""
	@echo "This will start:"
	@echo "- All backend services (ports 8001-8003)"
	@echo "- Frontend dashboard (port 3000)"
	@echo ""
	@echo "Press Ctrl+C to stop all services"
	@make -j2 start_services run_dashboard

# ================================
# MAINTENANCE
# ================================

clean:
	@echo "Cleaning logs and temporary files..."
	rm -rf $(BACKEND_DIR)/logs/*.log
	rm -rf $(DASHBOARD_DIR)/.next
	rm -rf $(DASHBOARD_DIR)/out
	@echo "Cleanup completed"

logs:
	@echo "Viewing service logs..."
	@echo "Available log files:"
	@ls -la $(BACKEND_DIR)/logs/ | grep -E "\.(log|err)$$" || echo "No log files found"
	@echo ""
	@echo "Use 'tail -f backend/logs/<service>-error.log' to follow specific logs"

# ================================
# CODE QUALITY
# ================================

lint:
	@echo "Running linters..."
	cd $(BACKEND_DIR) && uv run ruff check .

format:
	@echo "Formatting code..."
	cd $(BACKEND_DIR) && uv run ruff format .

type-check:
	@echo "Running type checker..."
	cd $(BACKEND_DIR) && uv run mypy common services

security-check:
	@echo "Running security scanner..."
	cd $(BACKEND_DIR) && uv run bandit -r . -f json -o bandit-report.json || true
	@echo "Security scan complete. Check bandit-report.json for details."

test:
	@echo "Running tests..."
	cd $(BACKEND_DIR) && uv run pytest -v

test-cov:
	@echo "Running tests with coverage..."
	cd $(BACKEND_DIR) && uv run pytest --cov=common --cov=services --cov-report=term-missing --cov-report=html

quality-check: lint type-check security-check test
	@echo ""
	@echo "✅ All quality checks passed!"

pre-commit-install:
	@echo "Installing pre-commit hooks..."
	cd $(BACKEND_DIR) && uv run pre-commit install
	@echo "Pre-commit hooks installed successfully!"
	@echo "Hooks will run automatically on git commit."

# ================================
# SETUP HELPERS
# ================================

setup: install_backend install_dashboard db_setup pre-commit-install
	@echo ""
	@echo "Setup completed! Next steps:"
	@echo "1. Configure your environment variables"
	@echo "2. Run 'make dev' to start the development environment"
	@echo "3. Visit http://localhost:3000 to access the dashboard"
	@echo "4. Run 'make quality-check' to verify code quality" 