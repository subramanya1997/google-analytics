# Windows Setup Guide for Data Ingestion Service

## 📋 Prerequisites

1. **Python 3.9+** installed
2. **Poetry** for dependency management
3. **Supabase account** (free tier is fine)
4. **BigQuery service account** credentials

## 🚀 Quick Setup Steps

### Step 1: Install Poetry (if not already installed)

Open PowerShell as Administrator and run:
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

Or use pip:
```bash
pip install poetry
```

### Step 2: Set up Supabase

1. Go to [https://supabase.com](https://supabase.com)
2. Create a new project
3. Wait for it to initialize (~2 minutes)
4. Go to **Settings** → **Database**
5. Copy the connection string that looks like:
   ```
   postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres
   ```

### Step 3: Set up the Service

1. **Navigate to the service directory:**
   ```bash
   cd backend/services/data_service
   ```

2. **Run the setup script:**
   ```bash
   setup_windows.bat
   ```
   This will:
   - Install Python dependencies
   - Create a `.env` file from the template
   - Guide you through configuration

3. **Configure your credentials** in the JSON files:

   **A. Edit `config/supabase.json`:**
   ```json
   {
     "project_url": "https://your-project-id.supabase.co",
     "project_id": "your-project-id",
     "database": {
       "host": "db.your-project-id.supabase.co",
       "port": 5432,
       "database": "postgres",
       "username": "postgres",
       "password": "your-database-password"
     },
     "connection_string": "postgresql+asyncpg://postgres:your-password@db.your-project-id.supabase.co:5432/postgres"
   }
   ```

   **B. Edit `config/bigquery.json`:**
   ```json
   {
     "project_id": "learned-maker-366218",
     "dataset_id": "analytics_349447920",
     "service_account": {
       "type": "service_account",
       "project_id": "learned-maker-366218",
       "private_key_id": "your-key-id",
       "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
       "client_email": "your-service-account@learned-maker-366218.iam.gserviceaccount.com",
       ...
     }
   }
   ```

### Step 4: Configure BigQuery Service Account

1. **Get your service account JSON:**
   - You should have a file like `learned-maker-366218-5927eef00c32.json`
   - Open it in a text editor
   - Copy the entire JSON content

2. **Paste it into `config/bigquery.json`:**
   - Replace the `service_account` section with your actual service account JSON
   - Keep the `project_id` and `dataset_id` fields as they are (unless you need different values)

### Step 5: Start the Service

1. **Run the service:**
   ```bash
   python run_windows.py
   ```

   This will:
   - Check database connection
   - Create database tables automatically
   - Start the FastAPI server

2. **Verify it's working:**
   - Open browser to: http://127.0.0.1:8001
   - Check API docs: http://127.0.0.1:8001/docs
   - Health check: http://127.0.0.1:8001/health

### Step 6: Test the Setup

In another terminal, run:
```bash
python test_setup.py
```

This will test all the endpoints and verify everything is working.

## 🔧 Configuration Details

### Configuration Files

| File | Description | Purpose |
|------|-------------|---------|
| `config/supabase.json` | Supabase project configuration | Database connection details |
| `config/bigquery.json` | BigQuery service account and settings | GA4 data access |
| `.env` | Environment variables | Service settings and defaults |

### Environment Variables (Optional Overrides)

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT_ID` | BigQuery project ID | `learned-maker-366218` |
| `BIGQUERY_DATASET_ID` | BigQuery dataset | `analytics_349447920` |
| `SFTP_HOST` | SFTP server hostname | From config files |
| `DEBUG` | Enable debug mode | `true` |

### Database Tables

The service will automatically create these tables on first run:
- `tenants` - Multi-tenant configuration
- `processing_jobs` - Track data ingestion jobs
- `users` - User data from SFTP (fresh load)
- `locations` - Location data from SFTP (fresh load)
- `events` - GA4 events from BigQuery (fresh load by date range)
- `task_tracking` - Task completion tracking

**Note:** No migrations needed! Tables are created automatically and data is loaded fresh from your sources.

## 📡 API Endpoints

### Data Ingestion
```http
POST /api/v1/data/ingest
Content-Type: application/json

{
  "tenant_id": "my-company",
  "start_date": "2024-01-15", 
  "end_date": "2024-01-20",
  "data_types": ["events", "users", "locations"],
  "force_refresh": false
}
```

### Job Status
```http
GET /api/v1/jobs/{job_id}
```

### List Jobs
```http
GET /api/v1/jobs?tenant_id=my-company&status=completed
```

## 🔄 Fresh Data Loading Strategy

This service is designed to load **fresh data** from your sources without any migrations:

### Events Data (BigQuery)
- **Replace Strategy**: For any date range, existing events are completely deleted and replaced
- **Source**: BigQuery GA4 tables (e.g., `events_20240115`)
- **Trigger**: API call with date range

### Users Data (SFTP)
- **Upsert Strategy**: Updates existing users, adds new ones
- **Source**: Latest `USER_LIST_FOR_AI*.xlsx` file from SFTP
- **Trigger**: API call or part of full data ingestion

### Locations Data (SFTP)
- **Upsert Strategy**: Updates existing locations, adds new ones
- **Source**: Latest `Locations_List*.xlsx` file from SFTP
- **Trigger**: API call or part of full data ingestion

### Complete Fresh Start
If you want to start completely fresh:
```bash
python reset_database.py
```
**WARNING**: This deletes ALL data!

## 🐛 Troubleshooting

### Database Connection Issues
- Verify your Supabase project is active
- Check the DATABASE_URL format
- Ensure your password doesn't contain special characters that need URL encoding

### BigQuery Issues
- Verify the service account JSON is valid
- Check that the service account has BigQuery permissions
- Ensure the project ID and dataset ID are correct

### SFTP Issues (optional)
- Test SFTP connection separately
- Check firewall settings
- Verify credentials and paths

### Poetry Issues
- Make sure Poetry is in your PATH
- Try: `poetry --version`
- Restart your terminal after installing Poetry

### Table Creation Issues
- The service creates tables automatically on first run
- If you see table-related errors, try: `python reset_database.py`
- Check that your database user has CREATE permissions

## 🎯 Next Steps

Once the service is running:

1. **Test data ingestion** with a small date range
2. **Check Supabase** to see the data being loaded
3. **Monitor logs** for any issues
4. **Set up the frontend** to connect to this service

## 📞 Getting Help

If you encounter issues:
1. Check the service logs in the terminal
2. Verify your `.env` configuration
3. Test each component separately (database, BigQuery, SFTP)
4. Use the test script to identify specific issues
