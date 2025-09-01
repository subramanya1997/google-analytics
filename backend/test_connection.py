#!/usr/bin/env python3
"""
Test script to debug authentication API responses and configuration issues.
"""
import asyncio
import httpx
import json
from common.config import get_settings

async def test_auth_with_code(code: str):
    """Test authentication with a real code and show API responses."""
    settings = get_settings("auth-service")
    base_url = settings.BASE_URL
    
    print(f"🔍 Testing authentication with base URL: {base_url}")
    print(f"🔑 Using code: {code[:10]}...")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Test getappproperity endpoint
            print("📡 Step 1: Calling getappproperity endpoint...")
            auth_url = f"{base_url}/manage/auth/getappproperity"
            print(f"URL: {auth_url}")
            
            app_property_response = await client.get(
                auth_url,
                params={"code": code}
            )
            
            print(f"Status Code: {app_property_response.status_code}")
            
            if app_property_response.status_code == 200:
                app_property_data = app_property_response.json()
                print("✅ App Property Response:")
                print(json.dumps(app_property_data, indent=2))
                
                # Extract fields
                app_instance_id = app_property_data.get("appInstanceId")
                access_token = app_property_data.get("accessToken")
                account_id = app_property_data.get("accountId")
                
                if app_instance_id and access_token:
                    print("\n" + "=" * 60)
                    print("📡 Step 2: Calling settings endpoint...")
                    
                    # Step 2: Test settings endpoint
                    settings_url = f"{base_url}/developerApp/accountAppInstance/settings/{app_instance_id}"
                    print(f"URL: {settings_url}")
                    print(f"Authorization: Bearer {access_token[:20]}...")
                    
                    settings_response = await client.get(
                        settings_url,
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    
                    print(f"Status Code: {settings_response.status_code}")
                    
                    if settings_response.status_code == 200:
                        settings_data = settings_response.json()
                        print("✅ Settings Response:")
                        print(json.dumps(settings_data, indent=2))
                        
                        # Check for configurations
                        print("\n" + "=" * 60)
                        print("🔍 Configuration Analysis:")
                        
                        # Parse settingsValues
                        settings_values_str = settings_data.get("settingsValues", "{}")
                        print(f"Raw settingsValues: {settings_values_str}")
                        
                        try:
                            parsed_settings = json.loads(settings_values_str) if settings_values_str else {}
                            print(f"\n📋 Parsed settings keys: {list(parsed_settings.keys())}")
                            
                            # Extract configurations with correct key names
                            postgres_config = parsed_settings.get("postgres-config", {})
                            bigquery_raw_config = parsed_settings.get("BigQuery", {})  # Note: "BigQuery" not "bigquery-config"
                            sftp_config = parsed_settings.get("SFTP Config", {})
                            
                            print(f"\npostgres-config present: {'✅' if postgres_config else '❌'}")
                            if postgres_config:
                                print(f"  Type: {type(postgres_config)}")
                                if isinstance(postgres_config, dict):
                                    print(f"  Keys: {list(postgres_config.keys())}")
                                    print(f"  Sample: host={postgres_config.get('host')}, user={postgres_config.get('user')}")
                            
                            print(f"BigQuery present: {'✅' if bigquery_raw_config else '❌'}")
                            if bigquery_raw_config:
                                print(f"  Type: {type(bigquery_raw_config)}")
                                if isinstance(bigquery_raw_config, dict):
                                    print(f"  Keys: {list(bigquery_raw_config.keys())}")
                                    print(f"  Sample: project_id={bigquery_raw_config.get('project_id')}, dataset_id={bigquery_raw_config.get('dataset_id')}")
                                    
                                    # Show service account parsing
                                    service_account_str = bigquery_raw_config.get("service_account", "")
                                    if service_account_str:
                                        try:
                                            service_account = json.loads(service_account_str)
                                            print(f"  Service Account: ✅ (type: {service_account.get('type')}, client_email: {service_account.get('client_email')})")
                                        except json.JSONDecodeError:
                                            print(f"  Service Account: ❌ (invalid JSON)")
                            
                            print(f"SFTP Config present: {'✅' if sftp_config else '❌'}")
                            if sftp_config:
                                print(f"  Type: {type(sftp_config)}")
                                if isinstance(sftp_config, dict):
                                    print(f"  Keys: {list(sftp_config.keys())}")
                                    print(f"  Sample: host={sftp_config.get('host')}")
                            
                        except json.JSONDecodeError as e:
                            print(f"❌ Failed to parse settingsValues: {e}")
                        
                        # Show all top-level keys in response
                        print(f"\n📋 All response keys: {list(settings_data.keys())}")
                        
                    else:
                        print(f"❌ Settings request failed: {settings_response.status_code}")
                        print("Response:", settings_response.text)
                else:
                    print("❌ Missing appInstanceId or accessToken in response")
            else:
                print(f"❌ Auth request failed: {app_property_response.status_code}")
                print("Response:", app_property_response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_connection():
    """Test basic connectivity to the authentication API."""
    settings = get_settings("auth-service")
    base_url = settings.BASE_URL
    
    print(f"Testing connection to: {base_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test basic connectivity
            response = await client.get(f"{base_url}/")
            print(f"✅ Base URL is reachable. Status: {response.status_code}")
            
    except httpx.ConnectError as e:
        print(f"❌ Connection failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # If code provided as argument, test with that code
        code = sys.argv[1]
        print("🧪 Testing with provided authentication code...")
        asyncio.run(test_auth_with_code(code))
    else:
        # Otherwise just test connectivity
        print("🧪 Testing basic connectivity...")
        print("💡 To test with authentication code, run: python test_connection.py YOUR_CODE")
        asyncio.run(test_connection())
