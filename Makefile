.PHONY: help install_backend install_dashboard build_dashboard run_dashboard start_dashboard db_setup db_clean db_optimize services_start service_analytics service_data service_auth stop_services clean logs

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
	@echo "  db_setup        - Initialize database schema and functions"
	@echo "  db_clean        - Clean/drop all database tables and functions"
	@echo "  db_optimize     - Optimize database indexes and statistics"
	@echo ""
	@echo "Backend Services:"
	@echo "  install_backend - Install Python dependencies with uv"
	@echo "  services_start  - Start all three backend services"
	@echo "  service_analytics - Start analytics service only (port 8001)"
	@echo "  service_data    - Start data service only (port 8002)"
	@echo "  service_auth    - Start auth service only (port 8003)"
	@echo "  stop_services   - Stop all running services"
	@echo ""
	@echo "Frontend Dashboard:"
	@echo "  install_dashboard - Install Node.js dependencies"
	@echo "  run_dashboard   - Start development server"
	@echo "  build_dashboard - Build for production"
	@echo "  start_dashboard - Start production server"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean          - Clean logs and temporary files"
	@echo "  logs           - View service logs"

# ================================
# DATABASE MANAGEMENT
# ================================

db_setup:
	@echo "Setting up database schema and functions..."
	cd $(BACKEND_DIR) && uv run python scripts/init_db.py

db_clean:
	@echo "Cleaning database (WARNING: This will delete all data)..."
	cd $(BACKEND_DIR) && uv run python scripts/clear_db.py

db_optimize:
	@echo "Optimizing database indexes and statistics..."
	@echo "This will add covering indexes and update statistics for better query performance"
	cd $(BACKEND_DIR) && uv run python scripts/optimize_indexes.py

# ================================
# BACKEND SERVICES
# ================================

install_backend:
	@echo "Installing backend dependencies with uv..."
	cd $(BACKEND_DIR) && uv sync --dev

services_start:
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

service_analytics:
	@echo "Starting Analytics Service on port 8001..."
	@echo "API docs: http://localhost:8001/docs"
	cd $(BACKEND_DIR) && uv run uvicorn services.analytics_service:app --port 8001 --reload

service_data:
	@echo "Starting Data Service on port 8002..."
	@echo "API docs: http://localhost:8002/docs"
	cd $(BACKEND_DIR) && uv run uvicorn services.data_service:app --port 8002 --reload

service_auth:
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
	@make -j2 services_start run_dashboard

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
# SETUP HELPERS
# ================================

setup: install_backend install_dashboard db_setup
	@echo ""
	@echo "Setup completed! Next steps:"
	@echo "1. Configure your environment variables"
	@echo "2. Run 'make dev' to start the development environment"
	@echo "3. Visit http://localhost:3000 to access the dashboard" 