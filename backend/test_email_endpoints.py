"""
Test script for email functionality endpoints
"""

import requests
import json
import time
from datetime import date, timedelta

# Configuration
BASE_URL = "http://localhost:8002/api/v1"
TENANT_ID = "e0f01854-6c2e-4b76-bf7b-67f3c28dbdac"  # Replace with actual tenant ID

HEADERS = {
    "Content-Type": "application/json",
    "X-Tenant-Id": TENANT_ID
}

def test_email_config():
    """Test email configuration endpoint"""
    print("🔧 Testing Email Configuration...")
    
    response = requests.get(f"{BASE_URL}/email/config", headers=HEADERS)
    
    if response.status_code == 200:
        config = response.json()
        print(f"✅ Email config retrieved: {config['configured']}")
        if config['configured']:
            print(f"📧 SMTP Server: {config['config'].get('server')}")
            print(f"📫 From Address: {config['config'].get('from_address')}")
        return True
    else:
        print(f"❌ Failed to get email config: {response.status_code}")
        print(response.text)
        return False

def test_branch_mappings():
    """Test branch email mappings"""
    print("\n📋 Testing Branch Email Mappings...")
    
    # First, get current mappings
    response = requests.get(f"{BASE_URL}/email/mappings", headers=HEADERS)
    print(f"📊 Current mappings: {len(response.json()) if response.status_code == 200 else 0}")
    
    # Real branch configuration data
    branch_config = {
        "D01": {
            "branch_name": "Downtown Branch",
            "email": "tasheer10@gmail.com",
            "name": "Dan Bronson",
            "enabled": True
        },
        "D02": {
            "branch_name": "Uptown Branch", 
            "email": "tasheer10@gmail.com",
            "name": "Subramanya N",
            "enabled": True
        },
        "D03": {
            "branch_name": "West Side Branch",
            "email": "tasheer10@gmail.com",
            "name": "Subramanya N",
            "enabled": True
        },
        "D04": {
            "branch_name": "East Side Branch",
            "email": "tasheer10@gmail.com", 
            "name": "Subramanya N",
            "enabled": False
        },
        "D06": {
            "branch_name": "Temp Branch",
            "email": "tasheer10@gmail.com",
            "name": "Subramanya N",
            "enabled": True
        }
    }
    
    # Convert to API format
    test_mappings = []
    for branch_code, config in branch_config.items():
        test_mappings.append({
            "branch_code": branch_code,
            "branch_name": config["branch_name"],
            "sales_rep_email": config["email"],
            "sales_rep_name": config["name"],
            "is_enabled": config["enabled"]
        })
    
    print(f"📝 Setting up {len(test_mappings)} branch mappings...")
    for mapping in test_mappings:
        status = "✅ enabled" if mapping["is_enabled"] else "❌ disabled"
        print(f"  📍 {mapping['branch_code']}: {mapping['branch_name']} → {mapping['sales_rep_name']} ({status})")
    
    response = requests.put(
        f"{BASE_URL}/email/mappings",
        headers=HEADERS,
        data=json.dumps(test_mappings)
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Mappings updated: {result['total']} mappings")
        print(f"   📊 Created: {result['created']}, Updated: {result['updated']}")
        return True
    else:
        print(f"❌ Failed to update mappings: {response.status_code}")
        print(response.text)
        return False

def test_send_reports(branch_codes=["D01", "D02"]):
    """Test sending combined reports"""
    print("\n📧 Testing Combined Report Sending...")
    
    # Use yesterday's date for testing
    test_date = (date.today() - timedelta(days=8)).strftime("%Y-%m-%d")
    
    send_request = {
        "report_date": test_date,
        "branch_codes": branch_codes  # None for all branches, or list of specific codes
    }
    
    print(f"📅 Report date: {test_date}")
    if branch_codes:
        print(f"📍 Target branches: {', '.join(branch_codes)}")
    else:
        print("📍 Target: All branches with mappings")
    
    response = requests.post(
        f"{BASE_URL}/email/send-reports",
        headers=HEADERS,
        data=json.dumps(send_request)
    )
    
    if response.status_code == 200:
        job = response.json()
        job_id = job['job_id']
        print(f"✅ Email job created: {job_id}")
        
        # Monitor job status
        print("⏳ Monitoring job status...")
        for i in range(10):  # Check for up to 30 seconds
            time.sleep(3)
            
            status_response = requests.get(
                f"{BASE_URL}/email/jobs/{job_id}",
                headers=HEADERS
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"📊 Job Status: {status['status']}")
                
                if status['status'] in ['completed', 'failed']:
                    if status['status'] == 'completed':
                        print(f"✅ Emails sent: {status['emails_sent']}/{status['total_emails']}")
                    else:
                        print(f"❌ Job failed: {status.get('error_message')}")
                    break
            else:
                print(f"❌ Failed to get job status: {status_response.status_code}")
                break
        
        return job_id
    else:
        print(f"❌ Failed to create email job: {response.status_code}")
        print(response.text)
        return None

def test_email_history():
    """Test email history"""
    print("\n📜 Testing Email History...")
    
    response = requests.get(
        f"{BASE_URL}/email/history?page=1&limit=5",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        history = response.json()
        print(f"📊 Email history records: {len(history['data'])}")
        
        for email in history['data']:
            print(f"📧 {email['sales_rep_email']} - {email['status']} - {email['subject']}")
        
        return True
    else:
        print(f"❌ Failed to get email history: {response.status_code}")
        print(response.text)
        return False

def test_all_branches():
    """Test sending to all branches"""
    print("\n🌍 Testing Send to All Branches...")
    return test_send_reports(branch_codes=None)  # None = all branches

def test_specific_branches():
    """Test sending to specific branches"""
    print("\n🎯 Testing Send to Specific Branches...")
    return test_send_reports(["D01","D06"])  # Downtown, West Side, North

def main():
    """Run all tests"""
    print("🚀 Starting Email Endpoints Testing...")
    print(f"🎯 Target: {BASE_URL}")
    print(f"🏢 Tenant: {TENANT_ID}")
    print("="*60)
    
    if TENANT_ID == "YOUR_TENANT_ID_HERE":
        print("❌ Please update TENANT_ID in the script first!")
        return
    
    try:
        # Test sequence
        success = True
        
        # Basic functionality tests
        success &= test_email_config()
        #success &= test_branch_mappings()
        
        if success:
            print("\n" + "="*60)
            print("📧 EMAIL SENDING TESTS")
            print("="*60)
            

            # Test more scenarios (uncomment as needed)
            #job_id2 = test_all_branches()     # Combined reports: all branches  
            job_id3 = test_specific_branches() # Combined reports: D01, D03, D05
            
            print("\n" + "="*60)
            print("📜 HISTORY CHECK")
            print("="*60)
            test_email_history()
        
        if success:
            print("\n🎉 All tests completed successfully!")
            print("\n💡 Tips:")
            print("   - Check backend/logs/analytics-service.log for detailed logs")
            print("   - Check your email inbox: tasheer10@gmail.com")
            print("   - D04 (East Side Branch) is disabled, so no emails should be sent there")
            print("\n📊 Report System:")
            print("   - Personalized Combined Reports: Each recipient gets one email with all their branches")
            print("   - Smart Filtering: Recipients only see data for branches they handle")
            print("   - Efficient: Minimal emails while providing complete relevant information")
        else:
            print("\n⚠️  Some tests failed. Check the output above.")
            
    except Exception as e:
        print(f"❌ Test script error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
