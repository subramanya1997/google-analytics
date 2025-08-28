#!/usr/bin/env python3
"""
Windows development runner for the data ingestion service
"""
import os
import sys

from pathlib import Path
from dotenv import load_dotenv

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Load environment variables
env_file = app_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    print(f"⚠️  No .env file found at {env_file}")
    print("Please create a .env file based on env.example")
    sys.exit(1)


def check_config_files():
    """Check if required configuration files exist."""
    print("🔧 Checking configuration files...")
    
    config_dir = app_dir / 'config'
    supabase_config = config_dir / 'supabase.json'
    bigquery_config = config_dir / 'bigquery.json'
    sftp_config = config_dir / 'sftp.json'
    
    missing_files = []
    
    if not supabase_config.exists():
        missing_files.append('config/supabase.json')
    else:
        print("   ✅ Supabase configuration found")
    
    if not bigquery_config.exists():
        missing_files.append('config/bigquery.json')
    else:
        print("   ✅ BigQuery configuration found")
    
    if not sftp_config.exists():
        missing_files.append('config/sftp.json')
    else:
        print("   ✅ SFTP configuration found")
    
    if missing_files:
        print(f"❌ Missing configuration files: {', '.join(missing_files)}")
        print("\n💡 Please create these files from the examples:")
        for file in missing_files:
            print(f"   cp {file}.example {file}")
        return False
    
    return True





def test_supabase_connection():
    """Test Supabase connection."""
    print("🔄 Testing Supabase connection...")
    
    try:
        # Import here to avoid circular imports
        sys.path.insert(0, str(app_dir))
        from app.core.config import settings
        from app.database.supabase_client import SupabaseClient
        
        supabase_config = settings.get_supabase_client_config()
        supabase_client = SupabaseClient(supabase_config)
        
        # Test connection
        result = supabase_client.test_connection()
        
        if result['success']:
            print("✅ Supabase connection successful!")
            print(f"   Project URL: {supabase_client.project_url}")
            print(f"   Connection test: {result['message']}")
            return True
        else:
            print(f"❌ Supabase connection failed: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Supabase connection: {e}")
        return False


def start_server():
    """Start the FastAPI server."""
    print("🚀 Starting FastAPI server...")
    
    try:
        import uvicorn
        from app.main import app
        
        # Get configuration from environment
        host = os.getenv('HOST', '127.0.0.1')
        port = int(os.getenv('PORT', '8005'))
        debug = os.getenv('DEBUG', 'true').lower() == 'true'
        
        print(f"   Server will run at: http://{host}:{port}")
        print(f"   Debug mode: {debug}")
        print(f"   API docs: http://{host}:{port}/docs")
        print(f"   Health check: http://{host}:{port}/health")
        
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=debug,
            log_level="info" if debug else "warning"
        )
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Please install dependencies with: poetry install")
    except Exception as e:
        print(f"❌ Error starting server: {e}")


def main():
    """Main function to set up and start the service."""
    print("=" * 60)
    print("🔥 Google Analytics Data Ingestion Service")
    print("=" * 60)
    
    # Check configuration files
    if not check_config_files():
        print("\n💡 Please create the required configuration files and try again.")
        return
    
    # Test Supabase connection
    if not test_supabase_connection():
        print("\n💡 Please fix the Supabase connection and try again.")
        return
    
    print("\n✅ All checks passed! Starting the server...")
    print("   Press Ctrl+C to stop the server")
    print("-" * 60)
    
    # Start the server
    start_server()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
