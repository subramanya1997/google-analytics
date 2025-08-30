#!/usr/bin/env python3
"""
Unified runner for all backend services.
Starts all services on different ports with proper environment setup.
"""

import os
import sys
import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Service configurations
SERVICES = {
    "analytics": {
        "name": "analytics-service",
        "module": "services.analytics_service.app.main:app",
        "port": 8001,
        "description": "Analytics Service - Analytics and reporting"
    },
    "data": {
        "name": "data-ingestion-service", 
        "module": "services.data_service.app.main:app",
        "port": 8002,
        "description": "Data Service - Data ingestion and processing"
    },
    "auth": {
        "name": "auth-service",
        "module": "services.auth_service.main:app",
        "port": 8003,
        "description": "Auth Service - Authentication and authorization"
    }
}


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def check_poetry():
    """Check if Poetry is installed."""
    try:
        result = subprocess.run(['poetry', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Poetry not found. Please install Poetry first:")
    print("   curl -sSL https://install.python-poetry.org | python3 -")
    return False


def check_config_files():
    """Check if required configuration files exist."""
    config_dir = Path("config")
    required_configs = ["postgres.json", "bigquery.json", "sftp.json"]
    
    missing_configs = []
    for config_file in required_configs:
        config_path = config_dir / config_file
        if not config_path.exists():
            missing_configs.append(config_file)
        else:
            print(f"✅ Found {config_file}")
    
    if missing_configs:
        print(f"❌ Missing configuration files: {', '.join(missing_configs)}")
        print("💡 Please copy from examples:")
        for config in missing_configs:
            example_file = f"{config}.example"
            print(f"   cp config/{example_file} config/{config}")
        return False
    
    return True


def validate_postgres_config():
    """Validate PostgreSQL configuration."""
    try:
        with open("config/postgres.json", 'r') as f:
            config = json.load(f)
        
        required_keys = ["host", "port", "user", "password", "database"]
        missing_keys = [key for key in required_keys if not config.get(key)]
        
        if missing_keys:
            print(f"❌ Missing PostgreSQL config keys: {', '.join(missing_keys)}")
            return False
        
        print("✅ PostgreSQL configuration is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating PostgreSQL config: {e}")
        return False


def setup_environment():
    """Set up environment variables."""
    env_file = Path(".env")
    
    if env_file.exists():
        load_dotenv(env_file)
        print("✅ Loaded environment variables from .env")
    else:
        print("⚠️  No .env file found, using default settings")
    
    # Set Python path to include backend directory
    backend_dir = Path(__file__).parent.absolute()
    python_path = os.environ.get('PYTHONPATH', '')
    if str(backend_dir) not in python_path:
        os.environ['PYTHONPATH'] = f"{backend_dir}:{python_path}" if python_path else str(backend_dir)
        print(f"✅ Updated PYTHONPATH to include {backend_dir}")


def install_dependencies():
    """Install Python dependencies using Poetry."""
    print("📦 Installing dependencies...")
    try:
        subprocess.run(['poetry', 'install'], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def run_service(service_key: str, service_config: Dict) -> subprocess.Popen:
    """Run a single service."""
    cmd = [
        'poetry', 'run', 'uvicorn',
        service_config['module'],
        '--host', '0.0.0.0',
        '--port', str(service_config['port']),
        '--reload'
    ]
    
    # Set service-specific environment variable
    env = os.environ.copy()
    env['SERVICE_NAME'] = service_config['name']
    
    print(f"🚀 Starting {service_config['description']} on port {service_config['port']}")
    
    try:
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        return process
    except Exception as e:
        print(f"❌ Failed to start {service_config['name']}: {e}")
        return None


def monitor_service(service_key: str, process: subprocess.Popen):
    """Monitor service output."""
    service_name = SERVICES[service_key]['name']
    port = SERVICES[service_key]['port']
    
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[{service_name}:{port}] {line.rstrip()}")
    except Exception as e:
        print(f"❌ Error monitoring {service_name}: {e}")


def main():
    """Main execution function."""
    print("🔧 Google Analytics Backend Services Runner")
    print("=" * 50)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Run all checks
    check_python_version()
    
    if not check_poetry():
        sys.exit(1)
    
    if not check_config_files():
        print("\n💡 Create configuration files and try again.")
        sys.exit(1)
    
    if not validate_postgres_config():
        sys.exit(1)
    
    setup_environment()
    
    if not install_dependencies():
        sys.exit(1)
    
    print("\n✅ All checks passed! Starting services...")
    print("=" * 50)
    
    # Start all services
    processes = {}
    threads = {}
    
    try:
        for service_key, service_config in SERVICES.items():
            process = run_service(service_key, service_config)
            if process:
                processes[service_key] = process
                
                # Start monitoring thread
                thread = threading.Thread(
                    target=monitor_service,
                    args=(service_key, process),
                    daemon=True
                )
                thread.start()
                threads[service_key] = thread
                
                # Small delay between service starts
                time.sleep(2)
        
        if not processes:
            print("❌ No services started successfully")
            sys.exit(1)
        
        print(f"\n🎉 Started {len(processes)} services successfully!")
        print("\n📍 Service URLs:")
        for service_key, service_config in SERVICES.items():
            if service_key in processes:
                port = service_config['port']
                print(f"   • {service_config['description']}: http://localhost:{port}")
                print(f"     - API Docs: http://localhost:{port}/docs")
                print(f"     - Health: http://localhost:{port}/health")
        
        print("\n🛑 Press Ctrl+C to stop all services")
        print("=" * 50)
        
        # Wait for all processes
        while True:
            time.sleep(1)
            
            # Check if any process has died
            for service_key, process in list(processes.items()):
                if process.poll() is not None:
                    print(f"⚠️  Service {service_key} has stopped")
                    del processes[service_key]
            
            if not processes:
                print("❌ All services have stopped")
                break
    
    except KeyboardInterrupt:
        print("\n👋 Stopping all services...")
        
        # Terminate all processes
        for service_key, process in processes.items():
            try:
                process.terminate()
                print(f"✅ Stopped {service_key}")
            except Exception as e:
                print(f"❌ Error stopping {service_key}: {e}")
        
        # Wait for processes to terminate
        for process in processes.values():
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
