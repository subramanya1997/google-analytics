#!/bin/bash

# Docker entrypoint script for Google Analytics Backend Services
# Runs all 3 services with individual log files

echo "🔧 Starting Google Analytics Backend Services"
echo "================================================"

# Set Python path to include the current directory
export PYTHONPATH=/app:$PYTHONPATH

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Function to start a service with logging
start_service() {
    local service_name="$1"
    local service_module="$2"
    local port="$3"
    local log_file="/app/logs/${service_name}.log"
    
    echo "🚀 Starting $service_name on port $port"
    echo "📄 Logs will be written to $log_file"
    
    # Set service-specific environment variable
    export SERVICE_NAME="$service_name"
    
    # Start the service in background with logging
    poetry run uvicorn "$service_module" \
        --host 0.0.0.0 \
        --port "$port" \
        --log-level info \
        --no-access-log \
        > "$log_file" 2>&1 &
    
    # Store the process ID
    eval "${service_name//-/_}_PID=$!"
    echo "✅ Started $service_name (PID: $(eval echo \$${service_name//-/_}_PID))"
}

# Start all services
start_service "analytics-service" "services.analytics_service.app.main:app" 8001
start_service "data-ingestion-service" "services.data_service.app.main:app" 8002
start_service "auth-service" "services.auth_service.app.main:app" 8003

echo "================================================"
echo "🎉 All services started successfully!"
echo ""
echo "📍 Service URLs:"
echo "   • Analytics Service: http://localhost:8001"
echo "   • Data Service: http://localhost:8002"
echo "   • Auth Service: http://localhost:8003"
echo ""
echo "📄 Log Files:"
echo "   • Analytics Service: /app/logs/analytics-service.log"
echo "   • Data Service: /app/logs/data-ingestion-service.log"
echo "   • Auth Service: /app/logs/auth-service.log"
echo ""
echo "🔍 Health checks:"
echo "   • Analytics: http://localhost:8001/health"
echo "   • Data: http://localhost:8002/health"
echo "   • Auth: http://localhost:8003/health"
echo ""
echo "📚 API Documentation:"
echo "   • Analytics: http://localhost:8001/docs"
echo "   • Data: http://localhost:8002/docs"
echo "   • Auth: http://localhost:8003/docs"
echo "================================================"

# Function to handle shutdown
shutdown() {
    echo ""
    echo "🛑 Shutting down services..."
    
    # Kill all background processes
    if [ ! -z "$analytics_service_PID" ]; then
        kill $analytics_service_PID 2>/dev/null
        echo "✅ Stopped analytics-service"
    fi
    
    if [ ! -z "$data_ingestion_service_PID" ]; then
        kill $data_ingestion_service_PID 2>/dev/null
        echo "✅ Stopped data-ingestion-service"
    fi
    
    if [ ! -z "$auth_service_PID" ]; then
        kill $auth_service_PID 2>/dev/null
        echo "✅ Stopped auth-service"
    fi
    
    echo "👋 All services stopped. Goodbye!"
    exit 0
}

# Set up signal handlers for graceful shutdown
trap shutdown SIGTERM SIGINT

# Function to check if services are running
check_services() {
    local failed_count=0
    
    if [ ! -z "$analytics_service_PID" ] && ! kill -0 $analytics_service_PID 2>/dev/null; then
        echo "❌ analytics-service has stopped"
        failed_count=$((failed_count + 1))
    fi
    
    if [ ! -z "$data_ingestion_service_PID" ] && ! kill -0 $data_ingestion_service_PID 2>/dev/null; then
        echo "❌ data-ingestion-service has stopped"
        failed_count=$((failed_count + 1))
    fi
    
    if [ ! -z "$auth_service_PID" ] && ! kill -0 $auth_service_PID 2>/dev/null; then
        echo "❌ auth-service has stopped"
        failed_count=$((failed_count + 1))
    fi
    
    if [ $failed_count -eq 3 ]; then
        echo "❌ All services have failed. Exiting."
        exit 1
    elif [ $failed_count -gt 0 ]; then
        echo "⚠️  $failed_count service(s) have failed, but others are still running."
    fi
}

# Monitor services
echo "🔍 Monitoring services... (Press Ctrl+C to stop)"
while true; do
    sleep 30
    check_services
done
