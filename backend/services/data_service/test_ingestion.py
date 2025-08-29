#!/usr/bin/env python3
"""
Test script for comprehensive data ingestion
"""
import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8001"
TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"  # Valid UUID for test tenant
START_DATE = "2025-08-01"
END_DATE = "2025-08-04"

def test_health_check():
    """Test if the service is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Service is running")
            return True
        else:
            print(f"❌ Service health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to service. Is it running?")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def trigger_data_ingestion():
    """Trigger comprehensive data ingestion."""
    
    payload = {
        "tenant_id": TENANT_ID,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "data_types": ["events", "users", "locations"],
        "force_refresh": True
    }
    
    print(f"\n🚀 Triggering data ingestion for {START_DATE} to {END_DATE}")
    print(f"   Tenant: {TENANT_ID}")
    print(f"   Data types: {payload['data_types']}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/data/ingest",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✅ Data ingestion job created successfully!")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {result.get('status')}")
            return job_id
        else:
            print(f"❌ Data ingestion failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to service. Is it running on port 8001?")
        return None
    except Exception as e:
        print(f"❌ Data ingestion error: {e}")
        return None

def check_job_status(job_id):
    """Check the status of a processing job."""
    if not job_id:
        return None
        
    try:
        # Note: We'd need to implement a job status endpoint
        # For now, we'll just wait and assume it's processing
        print(f"\n⏳ Job {job_id} is processing...")
        print("   This may take several minutes depending on data volume")
        return "processing"
        
    except Exception as e:
        print(f"❌ Error checking job status: {e}")
        return None

def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 COMPREHENSIVE DATA INGESTION TEST")
    print("=" * 60)
    
    # Test service health
    if not test_health_check():
        print("\n💡 Please start the service first:")
        print("   poetry run python run_windows.py")
        return
    
    # Trigger data ingestion
    job_id = trigger_data_ingestion()
    
    if job_id:
        print(f"\n📊 Expected Data Processing:")
        print("   ✅ Purchase events (revenue tracking)")
        print("   ✅ Add to cart events (abandonment analysis)")
        print("   ✅ Page view events (traffic analysis)")
        print("   ✅ Search results events (successful searches)")
        print("   ✅ No search results events (failed searches)")
        print("   ✅ View item events (product analytics)")
        print("   ✅ User data from SFTP")
        print("   ✅ Location data from SFTP")
        
        print(f"\n🔍 To monitor progress:")
        print(f"   1. Check service logs")
        print(f"   2. Check Supabase tables for data")
        print(f"   3. Look for job status updates")
        
        print(f"\n📋 Verification Steps:")
        print(f"   1. Check processing_jobs table for job {job_id}")
        print(f"   2. Verify data in event tables (purchase, add_to_cart, etc.)")
        print(f"   3. Check users and locations tables")
        print(f"   4. Confirm date range {START_DATE} to {END_DATE}")
        
        # Check job status
        check_job_status(job_id)
        
        print(f"\n✅ Test initiated successfully!")
        print(f"   Job ID: {job_id}")
    else:
        print(f"\n❌ Test failed to start data ingestion")

if __name__ == "__main__":
    main()
