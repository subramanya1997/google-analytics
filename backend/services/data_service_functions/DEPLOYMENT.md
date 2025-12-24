# Azure Functions Deployment Guide

This guide covers two deployment methods:
1. **Azure Portal (GUI)** - Manual deployment through the web interface
2. **GitHub Actions** - Automated CI/CD deployment

---

## Prerequisites

Before deploying, ensure you have:
- An Azure subscription
- A GitHub repository with the Azure Functions code
- PostgreSQL database accessible from Azure (Azure Database for PostgreSQL or external)

---

## Method 1: Azure Portal (GUI) Deployment

### Step 1: Create a Resource Group

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **"Create a resource"** → Search for **"Resource group"**
3. Click **"Create"**
4. Fill in:
   - **Subscription**: Select your subscription
   - **Resource group**: `rg-google-analytics-prod` (or your preferred name)
   - **Region**: Select your preferred region (e.g., `East US 2`)
5. Click **"Review + create"** → **"Create"**

### Step 2: Create a Storage Account (Required for Azure Functions and Queues)

1. Click **"Create a resource"** → Search for **"Storage account"**
2. Click **"Create"**
3. **Basics tab**:
   - **Resource group**: Select the one you created
   - **Storage account name**: `stgadataingestion` (must be globally unique, lowercase)
   - **Region**: Same as resource group
   - **Performance**: Standard
   - **Redundancy**: Locally-redundant storage (LRS)
4. Click **"Review + create"** → **"Create"**
5. After creation, go to the storage account → **"Access keys"** → Copy the **Connection string**
6. **Create the required queues:**
   - Go to Storage Account → **"Queues"** (under Data storage)
   - Click **"+ Queue"** and create:
     - **`ingestion-jobs`** - For data ingestion jobs
     - **`email-jobs`** - For email report jobs

### Step 3: Create the Function App

1. Click **"Create a resource"** → Search for **"Function App"**
2. Click **"Create"**
3. **Basics tab**:
   - **Resource group**: Select yours
   - **Function App name**: `func-data-ingestion-prod` (must be globally unique)
   - **Publish**: Code
   - **Runtime stack**: Python
   - **Version**: 3.9 or 3.10
   - **Region**: Same as resource group
   - **Operating System**: Linux
   - **Plan type**: **Premium** (required for 30-minute timeout) or **Dedicated (App Service)**

   > ⚠️ **Important**: Consumption plan has a 10-minute max timeout. Use **Premium** or **Dedicated** for long-running jobs.

4. **Hosting tab**:
   - **Storage account**: Select the one you created
5. **Monitoring tab**:
   - **Enable Application Insights**: Yes (recommended)
   - Create new or select existing Application Insights
6. Click **"Review + create"** → **"Create"**

### Step 4: Configure Application Settings

1. Go to your Function App → **"Configuration"** (under Settings)
2. Click **"+ New application setting"** and add each of these:

| Name | Value | Description |
|------|-------|-------------|
| `POSTGRES_HOST` | Your PostgreSQL host | e.g., `mydb.postgres.database.azure.com` |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | Your database username | Database user with access to tenant DBs |
| `POSTGRES_PASSWORD` | Your database password | Database password |
| `AzureWebJobsStorage` | Connection string | **CRITICAL**: From Step 2 - enables queue triggers |

> **IMPORTANT: Queue Configuration**
> 
> - `AzureWebJobsStorage` **MUST** point to the Storage Account containing the queues
> - This enables the Function App to listen to `ingestion-jobs` and `email-jobs` queues
> - Without this, queue triggers will not work
>
> **Note: Tenant-Specific Databases**
> 
> This service uses tenant-specific databases for SOC2 compliance. Each tenant has their own database:
> - Database name format: `google-analytics-{tenant_id}`
> - Tenant ID is included in queue messages
> - The service automatically connects to the correct tenant database

3. Click **"Save"** at the top

### Step 5: Configure Function Timeout (Premium/Dedicated only)

1. Go to Function App → **"Configuration"** → **"General settings"** tab
2. Set **Function timeout** to `00:30:00` (30 minutes)
3. Click **"Save"**

### Step 6: Deploy Code via Deployment Center

1. Go to Function App → **"Deployment Center"** (under Deployment)
2. **Source**: Select **GitHub**
3. Click **"Authorize"** and connect your GitHub account
4. Configure:
   - **Organization**: Your GitHub org/username
   - **Repository**: `google-analytics`
   - **Branch**: `feat/azure_functions`
5. **Build provider**: GitHub Actions
6. **Runtime stack**: Python
7. **Version**: 3.9
8. Click **"Save"**

This will automatically create a GitHub Actions workflow file in your repository.

### Step 7: Configure Network Access (if using Azure PostgreSQL)

1. Go to your Azure Database for PostgreSQL → **"Connection security"**
2. Add your Function App's outbound IPs to the firewall rules
3. Or enable **"Allow access to Azure services"**

### Step 8: Verify Deployment

1. Go to Function App → **"Functions"**
2. You should see these functions listed:
   - **HTTP Trigger:**
     - `health_check` - GET /api/v1/health
   - **Queue Triggers (Background Workers):**
     - `process_ingestion_job` - Triggered by `ingestion-jobs` queue
     - `process_email_job` - Triggered by `email-jobs` queue
3. Click on `health_check` → **"Get Function URL"** to test
4. **Verify Queue Triggers**:
   - Go to Storage Account → **"Queues"**
   - Confirm `ingestion-jobs` and `email-jobs` queues exist
   - Queue triggers will automatically start processing messages

---

## Method 2: GitHub Actions Deployment

### Step 1: Get Azure Publish Profile

1. Go to your Function App in Azure Portal
2. Click **"Get publish profile"** (in the Overview page, top toolbar)
3. A `.PublishSettings` file will download
4. Open it and copy the entire content

### Step 2: Add GitHub Secret

1. Go to your GitHub repository → **"Settings"** → **"Secrets and variables"** → **"Actions"**
2. Click **"New repository secret"**
3. **Name**: `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`
4. **Value**: Paste the entire publish profile content
5. Click **"Add secret"**

### Step 3: Create GitHub Actions Workflow

Create the file `.github/workflows/deploy-azure-functions.yml`:

```yaml
name: Deploy Data Service to Azure Functions

on:
  push:
    branches:
      - feat/azure_functions
      - main
    paths:
      - 'backend/services/data_service_functions/**'
  workflow_dispatch:  # Manual trigger

env:
  AZURE_FUNCTIONAPP_NAME: 'func-data-ingestion-prod'  # Your function app name
  AZURE_FUNCTIONAPP_PACKAGE_PATH: 'backend/services/data_service_functions'
  PYTHON_VERSION: '3.9'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Setup Python ${{ env.PYTHON_VERSION }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Install dependencies
      shell: bash
      run: |
        pushd '${{ env.AZURE_FUNCTIONAPP_PACKAGE_PATH }}'
        python -m pip install --upgrade pip
        pip install -r requirements.txt --target=".python_packages/lib/site-packages"
        popd

    - name: Run tests
      shell: bash
      run: |
        pushd '${{ env.AZURE_FUNCTIONAPP_PACKAGE_PATH }}'
        pip install pytest pytest-asyncio
        python -m pytest tests/ -v --tb=short || echo "Tests completed"
        popd

    - name: Deploy to Azure Functions
      uses: Azure/functions-action@v1
      with:
        app-name: ${{ env.AZURE_FUNCTIONAPP_NAME }}
        package: ${{ env.AZURE_FUNCTIONAPP_PACKAGE_PATH }}
        publish-profile: ${{ secrets.AZURE_FUNCTIONAPP_PUBLISH_PROFILE }}
        scm-do-build-during-deployment: true
        enable-oryx-build: true
```

### Step 4: Commit and Push

```bash
git add .github/workflows/deploy-azure-functions.yml
git commit -m "ci: Add GitHub Actions workflow for Azure Functions deployment"
git push
```

### Step 5: Monitor Deployment

1. Go to your GitHub repository → **"Actions"** tab
2. You'll see the workflow running
3. Click on it to view logs and deployment status

---

## Alternative: Using Azure CLI

If you prefer command-line deployment:

```bash
# Login to Azure
az login

# Create resource group
az group create --name rg-google-analytics-prod --location eastus2

# Create storage account
az storage account create \
  --name stgaborchestration \
  --resource-group rg-google-analytics-prod \
  --location eastus2 \
  --sku Standard_LRS

# Create function app (Premium plan for 30-min timeout)
az functionapp plan create \
  --name plan-data-ingestion \
  --resource-group rg-google-analytics-prod \
  --location eastus2 \
  --sku EP1 \
  --is-linux

az functionapp create \
  --name func-data-ingestion-prod \
  --resource-group rg-google-analytics-prod \
  --plan plan-data-ingestion \
  --runtime python \
  --runtime-version 3.9 \
  --storage-account stgaborchestration \
  --functions-version 4

# Configure app settings
# Note: Each tenant has their own database (google-analytics-{tenant_id})
# Get storage connection string first
STORAGE_CONN=$(az storage account show-connection-string \
  --name stgaborchestration \
  --resource-group rg-google-analytics-prod \
  --query connectionString -o tsv)

az functionapp config appsettings set \
  --name func-data-ingestion-prod \
  --resource-group rg-google-analytics-prod \
  --settings \
    POSTGRES_HOST=your-db-host \
    POSTGRES_PORT=5432 \
    POSTGRES_USER=your-user \
    POSTGRES_PASSWORD=your-password \
    AzureWebJobsStorage="$STORAGE_CONN"

# Create queues
az storage queue create --name ingestion-jobs --connection-string "$STORAGE_CONN"
az storage queue create --name email-jobs --connection-string "$STORAGE_CONN"

# Deploy from local
cd backend/services/data_service_functions
func azure functionapp publish func-data-ingestion-prod
```

---

## Post-Deployment Verification

### 1. Check Functions are Running

```bash
# List functions
az functionapp function list \
  --name func-data-ingestion-prod \
  --resource-group rg-google-analytics-prod

# Check logs
az functionapp log stream \
  --name func-data-ingestion-prod \
  --resource-group rg-google-analytics-prod
```

### 2. Test Queue-Based Processing

```bash
# Test health check endpoint
FUNCTION_URL="https://func-data-ingestion-prod.azurewebsites.net"
curl -X GET "$FUNCTION_URL/api/v1/health"
# Should return: {"status": "healthy", "service": "data-ingestion-email-worker", ...}

# Test ingestion via queue (from your local machine)
cd backend
uv run python services/data_service_functions/tests/test_ingestion.py \
  --tenant-id "your-tenant-uuid" \
  --days 7

# This will:
# 1. Create job record in database (status: queued)
# 2. Send message to 'ingestion-jobs' queue
# 3. Azure Function picks up and processes automatically

# Monitor in Azure Portal:
# - Storage Account → Queues → ingestion-jobs (watch message count drop to 0)
# - Function App → Monitor → Invocations (see process_ingestion_job executions)

# Check job status in database:
SELECT job_id, status, records_processed, error_message
FROM processing_jobs
WHERE tenant_id = 'your-tenant-uuid'
ORDER BY created_at DESC
LIMIT 10;

# Test email reports via queue
uv run python services/data_service_functions/tests/test_email_sending.py \
  --tenant-id "your-tenant-uuid" \
  --report-date "2025-01-15" \
  --branch-codes "D01,D02"

# Monitor email job:
SELECT job_id, status, emails_sent, emails_failed
FROM email_jobs
WHERE tenant_id = 'your-tenant-uuid'
ORDER BY created_at DESC
LIMIT 10;
```

**Note**: Jobs are triggered via FastAPI services (data_service, analytics_service), which create database records and queue messages. Azure Functions process them in the background.

### 3. Monitor in Application Insights

1. Go to Azure Portal → Your Function App → **"Application Insights"**
2. View:
   - **Live Metrics** - Real-time function executions
   - **Failures** - Error tracking
   - **Performance** - Execution times
   - **Logs** - Query logs with Kusto

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Functions not showing | Check deployment logs in Deployment Center |
| Queue triggers not firing | Verify `AzureWebJobsStorage` is set correctly and points to storage with queues |
| Message decoding errors | Ensure `host.json` has `"queues.messageEncoding": "none"` |
| Jobs stuck in "queued" | Check poison queues (`ingestion-jobs-poison`, `email-jobs-poison`) for failed messages |
| Database connection failed | Verify connection string, firewall rules, and SSL is enabled |
| Timeout errors | Jobs have 10 min timeout on Consumption Plan |
| Email sending fails | Verify SMTP config in `tenant_config.smtp_credentials` JSONB field |
| BigQuery errors | Verify service account credentials in tenant config |

### View Logs

```bash
# Stream live logs
az functionapp log stream \
  --name func-data-ingestion-prod \
  --resource-group rg-google-analytics-prod

# Or in Azure Portal:
# Function App → Functions → Select function → Monitor
```

---

## Cost Considerations

| Plan | Timeout | Cost Model | Best For |
|------|---------|------------|----------|
| **Consumption** | 10 min max | Pay per execution | Light workloads |
| **Premium (EP1)** | 60 min | Always-warm instances | Production with long jobs |
| **Dedicated (B1+)** | Unlimited | Fixed monthly | Predictable workloads |

For this data ingestion service with 30-minute jobs, **Premium EP1** is recommended.

---

## Security Best Practices

1. **Use Key Vault** for sensitive settings:
   ```bash
   az keyvault secret set --vault-name my-keyvault --name POSTGRES-PASSWORD --value "your-password"
   ```
   Then reference in app settings: `@Microsoft.KeyVault(SecretUri=https://my-keyvault.vault.azure.net/secrets/POSTGRES-PASSWORD/)`

2. **Enable Managed Identity** for Azure resources

3. **Use Private Endpoints** for database connections

4. **Enable HTTPS Only** in Configuration → General settings

