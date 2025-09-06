#!/bin/bash

# Setup script for Google Analytics Backend with uv
echo "🔧 Setting up Google Analytics Backend with uv"
echo "=============================================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    pip install uv
fi

# Install dependencies using uv sync
echo "📚 Installing dependencies..."
if [[ "$1" == "--dev" ]]; then
    echo "🛠️ Installing with development dependencies..."
    uv sync --dev
else
    echo "📦 Installing production dependencies only..."
    uv sync
fi

# Create .env file if it doesn't exist
if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        echo "📄 Creating .env file from example..."
        cp .env.example .env
        echo "Please edit .env with your configuration"
    fi
fi

echo "✅ Setup complete!"
echo ""
echo "To run all services:"
echo "  ./docker-entrypoint.sh"
echo ""
echo "To run individual services:"
echo "  uv run uvicorn services.analytics_service.main:app --port 8001"
echo "  uv run uvicorn services.data_service.main:app --port 8002"
echo "  uv run uvicorn services.auth_service.main:app --port 8003"
