#!/usr/bin/env python3
"""
Windows-compatible runner for the Analytics Service

This script provides a convenient way to run the analytics service on Windows
with proper environment setup and configuration validation.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any

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
    required_configs = ["supabase.json"]
    
    missing_configs = []
    for config_file in required_configs:
        config_path = config_dir / config_file
        if not config_path.exists():
            missing_configs.append(config_file)
        else:
            print(f"✅ Found {config_file}")
    
    if missing_configs:
        print(f"❌ Missing configuration files: {', '.join(missing_configs)}")
        print("   Please copy from data service or create them:")
        for config in missing_configs:
            print(f"   cp ../data_service/config/{config} config/{config}")
        return False
    
    return True

def validate_supabase_config():
    """Validate Supabase configuration."""
    try:
        with open("config/supabase.json", 'r') as f:
            config = json.load(f)
        
        required_keys = ["project_url", "service_role_key"]
        missing_keys = [key for key in required_keys if not config.get(key)]
        
        if missing_keys:
            print(f"❌ Missing Supabase config keys: {', '.join(missing_keys)}")
            return False
        
        print("✅ Supabase configuration is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating Supabase config: {e}")
        return False

def setup_environment():
    """Set up environment variables."""
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_file.exists() and env_example.exists():
        print("📝 Creating .env file from template...")
        # Copy env.example to .env
        with open(env_example, 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print("✅ Created .env file - please review and update the configuration")
    elif env_file.exists():
        print("✅ .env file exists")
    else:
        print("⚠️  No .env file found, using default settings")

def install_dependencies():
    """Install Python dependencies using Poetry."""
    print("📦 Installing dependencies...")
    try:
        result = subprocess.run(['poetry', 'install'], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def run_service():
    """Run the analytics service."""
    print("🚀 Starting Analytics Service...")
    print("📍 Service will be available at: http://localhost:8002")
    print("📚 API Documentation: http://localhost:8002/docs")
    print("🏥 Health Check: http://localhost:8002/health")
    print("\n" + "="*50)
    
    try:
        # Run using Poetry
        subprocess.run([
            'poetry', 'run', 'uvicorn', 
            'app.main:app', 
            '--host', '0.0.0.0',
            '--port', '8005',
            '--reload'
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start service: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Service stopped by user")

def main():
    """Main execution function."""
    print("🔧 Analytics Service Setup & Runner")
    print("="*40)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Run all checks
    check_python_version()
    
    if not check_poetry():
        sys.exit(1)
    
    if not check_config_files():
        sys.exit(1)
    
    if not validate_supabase_config():
        sys.exit(1)
    
    setup_environment()
    
    if not install_dependencies():
        sys.exit(1)
    
    print("\n✅ All checks passed! Starting service...")
    print("-" * 40)
    
    run_service()

if __name__ == "__main__":
    main()
