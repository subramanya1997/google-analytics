# Azure Functions Deployment Guide

> **Last Updated**: December 2024  
> **Status**: Production Ready  
> **Owner**: DevOps / Backend Team

## Table of Contents

- [Overview](#overview)
- [Architecture Context](#architecture-context)
- [Prerequisites](#prerequisites)
- [Deployment Methods](#deployment-methods)
  - [Method 1: Azure Portal (GUI)](#method-1-azure-portal-gui-deployment)
  - [Method 2: GitHub Actions](#method-2-github-actions-deployment)
  - [Method 3: Azure CLI](#method-3-azure-cli-deployment)
- [Post-Deployment Verification](#post-deployment-verification)
- [Troubleshooting](#troubleshooting)
- [Cost Considerations](#cost-considerations)
- [Security Best Practices](#security-best-practices)

---

## Overview

### Purpose

The Azure Functions service (`backend/services/functions/`) is a **serverless background worker** that handles long-running, resource-intensive operations asynchronously. It processes jobs that are queued by the FastAPI services, enabling the main API services to remain responsive.

### What This Service Does

| Function | Trigger | Description |
|----------|---------|-------------|
| `health_check` | HTTP GET | Health endpoint for monitoring and load balancers |
| `process_ingestion_job` | Queue | Extracts GA4 events from BigQuery, downloads user/location data from SFTP |
| `process_email_job` | Queue | Generates HTML branch reports and sends via SMTP |

### Why Azure Functions?

- **Long-running jobs**: Data ingestion can take 10-30 minutes for large date ranges
- **Cost efficiency**: Pay only when jobs are running (serverless)
- **Auto-scaling**: Handles multiple concurrent tenant jobs
- **Isolation**: Keeps heavy processing separate from API latency

---

## Architecture Context

### How It Fits in the System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GOOGLE ANALYTICS SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│   │ Auth Service │    │ Data Service │    │  Analytics   │   FastAPI       │
│   │    :8003     │    │    :8002     │    │   Service    │   Services      │
│   └──────────────┘    └──────┬───────┘    │    :8001     │                 │
│                              │            └──────┬───────┘                 │
│                              │                   │                         │
│                              │ Queue Messages    │                         │
│                              ▼                   ▼                         │
│                    ┌─────────────────────────────────────┐                 │
│                    │       Azure Storage Queues          │                 │
│                    │  • ingestion-jobs                   │                 │
│                    │  • email-jobs                       │                 │
│                    └─────────────────┬───────────────────┘                 │
│                                      │                                     │
│                                      ▼                                     │
│                    ┌─────────────────────────────────────┐                 │
│                    │       Azure Functions               │   Serverless    │
│                    │  • process_ingestion_job            │   Workers       │
│                    │  • process_email_job                │                 │
│                    └─────────────────┬───────────────────┘                 │
│                                      │                                     │
│            ┌─────────────────────────┼─────────────────────────┐           │
│            ▼                         ▼                         ▼           │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐       │
│   │    BigQuery     │    │   PostgreSQL    │    │   SMTP Server   │       │
│   │  (GA4 Events)   │    │ (Tenant DBs)    │    │  (Email Send)   │       │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Job Flow

1. **User triggers ingestion** via Data Service API (`POST /api/v1/ingestion/jobs`)
2. **Data Service** creates job record in database (status: `queued`)
3. **Data Service** sends message to `ingestion-jobs` Azure Queue
4. **Azure Function** (`process_ingestion_job`) picks up message automatically
5. **Function** updates job status to `processing`, executes work, updates to `completed`/`failed`
6. **User** can poll job status via API or receive webhook notification

### Multi-Tenant Architecture

Each tenant has their own isolated database for SOC2 compliance:
- Database naming: `google-analytics-{tenant_id}`
- Tenant ID is included in every queue message
- Azure Functions connect to the correct tenant database automatically

For more details, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Prerequisites

Before deploying, ensure you have:

| Requirement | Description |
|-------------|-------------|
| Azure Subscription | Active subscription with permissions to create resources |
| GitHub Repository | Repository containing the `backend/services/functions/` code |
| PostgreSQL Database | Accessible from Azure (Azure Database for PostgreSQL or external) |
| BigQuery Access | Service account credentials for GA4 data (stored per-tenant) |
| SMTP Server | For email reports (configured per-tenant) |

---

## Deployment Methods

### Method 1: Azure Portal (GUI) Deployment

#### Step 1: Create a Resource Group

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **"Create a resource"** → Search for **"Resource group"**
3. Configure:
   - **Subscription**: Select your subscription
   - **Resource group**: `rg-google-analytics-prod`
   - **Region**: Select your preferred region (e.g., `East US 2`)
4. Click **"Review + create"** → **"Create"**

#### Step 2: Create a Storage Account (Required for Queues)

1. Click **"Create a resource"** → Search for **"Storage account"**
2. **Basics tab**:
   - **Resource group**: Select the one you created
   - **Storage account name**: `stgadataingestion` (globally unique, lowercase)
   - **Region**: Same as resource group
   - **Performance**: Standard
   - **Redundancy**: Locally-redundant storage (LRS)
3. Click **"Review + create"** → **"Create"**
4. After creation:
   - Go to Storage Account → **"Access keys"** → Copy the **Connection string**
   - Go to **"Queues"** → Create two queues:
     - `ingestion-jobs`
     - `email-jobs`

#### Step 3: Create the Function App

1. Click **"Create a resource"** → Search for **"Function App"**
2. **Basics tab**:
   - **Resource group**: Select yours
   - **Function App name**: `func-ga-data-ingestion-prod` (globally unique)
   - **Publish**: Code
   - **Runtime stack**: Python
   - **Version**: 3.11
   - **Region**: Same as resource group
   - **Operating System**: Linux
   - **Plan type**: **Premium (EP1)** or **Dedicated (App Service)**

> ⚠️ **Important**: Consumption plan has a **10-minute max timeout**. Use **Premium** or **Dedicated** for jobs that may run up to 30 minutes.

3. **Hosting tab**: Select the storage account you created
4. **Monitoring tab**: Enable Application Insights (recommended)
5. Click **"Review + create"** → **"Create"**

#### Step 4: Configure Application Settings

Go to Function App → **"Configuration"** → Add these settings:

| Name | Value | Description |
|------|-------|-------------|
| `POSTGRES_HOST` | `your-db.postgres.database.azure.com` | Database server hostname |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `your-username` | Database username |
| `POSTGRES_PASSWORD` | `your-password` | Database password |
| `AzureWebJobsStorage` | Connection string from Step 2 | **Required** for queue triggers |

> **Critical**: `AzureWebJobsStorage` must point to the Storage Account containing the queues. Without this, queue triggers will not work.

Click **"Save"**.

#### Step 5: Configure Function Timeout

1. Go to Function App → **"Configuration"** → **"General settings"**
2. Set **Function timeout** to `00:30:00` (30 minutes)
3. Click **"Save"**

#### Step 6: Deploy via Deployment Center

1. Go to Function App → **"Deployment Center"**
2. **Source**: GitHub
3. Authorize and select:
   - **Repository**: `google-analytics`
   - **Branch**: `main` (or your deployment branch)
4. **Build provider**: GitHub Actions
5. Click **"Save"**

This creates a GitHub Actions workflow automatically.

---

### Method 2: GitHub Actions Deployment

#### Step 1: Get Azure Publish Profile

1. Go to Function App in Azure Portal
2. Click **"Get publish profile"** (top toolbar)
3. Open the downloaded file and copy the entire content

#### Step 2: Add GitHub Secret

1. Go to GitHub Repository → **"Settings"** → **"Secrets and variables"** → **"Actions"**
2. Create secret:
   - **Name**: `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`
   - **Value**: Paste the publish profile content

#### Step 3: Create Workflow File

Create `.github/workflows/master_gadataingestion.yml`:



#### Step 4: Commit and Push

```bash
git add .github/workflows/master_gadataingestion.yml
git commit -m "ci: Add Azure Functions deployment workflow"
git push
```

Monitor deployment in GitHub → **"Actions"** tab.

---

### Method 3: Azure CLI Deployment

```bash
# Login to Azure
az login

# Create resource group
az group create --name rg-google-analytics-prod --location eastus2

# Create storage account
az storage account create \
  --name stgadataingestion \
  --resource-group rg-google-analytics-prod \
  --location eastus2 \
  --sku Standard_LRS

# Get storage connection string
STORAGE_CONN=$(az storage account show-connection-string \
  --name stgadataingestion \
  --resource-group rg-google-analytics-prod \
  --query connectionString -o tsv)

# Create queues
az storage queue create --name ingestion-jobs --connection-string "$STORAGE_CONN"
az storage queue create --name email-jobs --connection-string "$STORAGE_CONN"

# Create Premium function app plan (for 30-min timeout)
az functionapp plan create \
  --name plan-ga-data-ingestion \
  --resource-group rg-google-analytics-prod \
  --location eastus2 \
  --sku EP1 \
  --is-linux

# Create function app
az functionapp create \
  --name func-ga-data-ingestion-prod \
  --resource-group rg-google-analytics-prod \
  --plan plan-ga-data-ingestion \
  --runtime python \
  --runtime-version 3.11 \
  --storage-account stgadataingestion \
  --functions-version 4

# Configure app settings
az functionapp config appsettings set \
  --name func-ga-data-ingestion-prod \
  --resource-group rg-google-analytics-prod \
  --settings \
    POSTGRES_HOST=your-db-host \
    POSTGRES_PORT=5432 \
    POSTGRES_USER=your-user \
    POSTGRES_PASSWORD=your-password \
    AzureWebJobsStorage="$STORAGE_CONN"

# Deploy from local
cd backend/services/functions
func azure functionapp publish func-ga-data-ingestion-prod
```

---

## Post-Deployment Verification

### 1. Verify Functions are Registered

Go to Function App → **"Functions"**. You should see:
- `health_check` (HTTP Trigger)
- `process_ingestion_job` (Queue Trigger)
- `process_email_job` (Queue Trigger)

### 2. Test Health Endpoint

```bash
curl https://func-ga-data-ingestion-prod.azurewebsites.net/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-12-30T10:30:00.123456",
  "version": "1.0.0",
  "service": "data-ingestion-email-worker",
  "mode": "queue-based background processing"
}
```

### 3. Monitor in Azure Portal

- **Storage Account** → **Queues**: Watch message counts
- **Function App** → **Monitor**: View invocation logs
- **Application Insights** → **Live Metrics**: Real-time monitoring

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Functions not showing | Deployment failed | Check Deployment Center logs |
| Queue triggers not firing | Missing `AzureWebJobsStorage` | Verify app setting points to correct storage |
| Message decoding errors | Encoding mismatch | Ensure `host.json` has `"queues.messageEncoding": "none"` |
| Jobs stuck in "queued" | Function crashed | Check poison queues (`*-poison`) for failed messages |
| Database connection failed | Firewall/credentials | Verify connection string and Azure firewall rules |
| Timeout errors | Job too long | Use Premium plan (30-min timeout) or optimize job |
| BigQuery errors | Invalid credentials | Check `tenant_config.bigquery_credentials` |
| Email sending fails | SMTP misconfigured | Verify `tenant_config.email_config` |

### View Logs

```bash
# Stream live logs
az functionapp log stream \
  --name func-ga-data-ingestion-prod \
  --resource-group rg-google-analytics-prod
```

Or in Azure Portal: Function App → Functions → Select function → **Monitor**

---

## Cost Considerations

| Plan | Max Timeout | Cost Model | Best For |
|------|-------------|------------|----------|
| **Consumption** | 10 min | Pay per execution | Light workloads, testing |
| **Premium (EP1)** | 60 min | Always-warm instances | Production with long jobs |
| **Dedicated (B1+)** | Unlimited | Fixed monthly | Predictable high volume |

**Recommendation**: Use **Premium EP1** for production. Data ingestion jobs can run 10-30 minutes depending on date range and data volume.

---

## Security Best Practices

### 1. Use Azure Key Vault for Secrets

```bash
# Create Key Vault
az keyvault create --name kv-ga-secrets --resource-group rg-google-analytics-prod

# Store secrets
az keyvault secret set --vault-name kv-ga-secrets --name POSTGRES-PASSWORD --value "your-password"

# Reference in app settings
POSTGRES_PASSWORD=@Microsoft.KeyVault(SecretUri=https://kv-ga-secrets.vault.azure.net/secrets/POSTGRES-PASSWORD/)
```

### 2. Enable Managed Identity

```bash
az functionapp identity assign \
  --name func-ga-data-ingestion-prod \
  --resource-group rg-google-analytics-prod
```

### 3. Network Security

- Enable **Private Endpoints** for database connections
- Configure **VNet Integration** for the Function App
- Enable **HTTPS Only** in Configuration → General settings

### 4. Access Control

- Use **Azure RBAC** for deployment permissions
- Restrict Function App access with **IP restrictions** if needed
- Enable **Application Insights** for audit logging

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
- [DATABASE.md](./DATABASE.md) - Database schema and tenant isolation
- [RUNBOOK.md](./RUNBOOK.md) - Operational procedures and incident response
- [API.md](./API.md) - Data Service API for triggering jobs
- [Functions README](../services/functions/README.md) - Service-specific documentation

