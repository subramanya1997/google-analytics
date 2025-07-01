# Automated Workflow: SFTP Sync → Report Generation → Email Distribution

## Overview

This document describes the complete automated workflow for:
1. Fetching data files from SFTP
2. Loading data into the database
3. Generating branch-wise reports
4. Sending reports to sales representatives via email

## Workflow Diagram

```
SFTP Server → Download .jsonl → Load to DB → Generate Reports → Send Emails
     ↓              ↓                ↓              ↓                ↓
 (hercules/)   (data folder)   (SQLite DB)   (HTML reports)   (SMTP Server)
```

## Quick Start

### 1. One-Time Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure all config files
cp configs/sftp_config.json.example configs/sftp_config.json
cp configs/smtp_config.json.example configs/smtp_config.json
cp configs/branch_email_mapping.json.example configs/branch_email_mapping.json

# Edit the config files with your credentials
# - SFTP credentials in sftp_config.json
# - SMTP server details in smtp_config.json
# - Branch emails in branch_email_mapping.json
```

### 2. Manual Execution

```bash
# Full automated workflow (download → load → report → email)
make full_sync_with_email

# Or run step by step:
make sftp_sync          # Download and load data
make generate_report    # Generate HTML reports
make send_reports       # Send emails
```

### 3. Automated Scheduling

Add to crontab for daily execution:
```bash
# Run daily at 2:00 AM
0 2 * * * cd /path/to/impax && ./scripts/daily_sync.sh

# Run Monday-Friday at 8:00 AM
0 8 * * 1-5 cd /path/to/impax && ./scripts/daily_sync.sh
```

## Configuration Files

### 1. SFTP Configuration (`configs/sftp_config.json`)
```json
{
    "host": "extremeb2bsftp.blob.core.windows.net",
    "username": "extremeb2bsftp.herculessftpuser",
    "password": "your-password",
    "remote_path": "hercules",
    "generate_reports": true,
    "send_emails": true
}
```

### 2. SMTP Configuration (`configs/smtp_config.json`)
```json
{
    "server": "smtp.gmail.com",
    "port": 587,
    "use_tls": true,
    "username": "your-email@gmail.com",
    "password": "your-app-password",
    "from_address": "Sales Analytics <analytics@company.com>"
}
```

### 3. Branch Email Mapping (`configs/branch_email_mapping.json`)
```json
{
    "D01": {
        "branch_name": "Downtown Branch",
        "email": "sales.rep@company.com",
        "name": "John Doe",
        "cc": "manager@company.com",
        "enabled": true
    }
}
```

## Testing and Troubleshooting

### Test Individual Components

```bash
# Test SFTP connection
python scripts/test_sftp_connection.py

# Test report generation (with existing data)
python scripts/generate_branch_wise_report.py --db-path db/branch_wise_location.db

# Test email sending (dry run)
python scripts/send_branch_reports.py --dry-run

# Test email for specific branch
python scripts/send_branch_reports.py --branch D01 --dry-run
```

### Common Issues and Solutions

1. **SFTP Connection Failed**
   - Check credentials in `configs/sftp_config.json`
   - Verify network connectivity
   - Ensure the remote path exists

2. **No Reports Generated**
   - Check if data was loaded successfully
   - Verify database path is correct
   - Look for errors in logs

3. **Emails Not Sending**
   - For Gmail: Use app-specific password, not regular password
   - Check SMTP server and port settings
   - Verify sender email has permission to send
   - Check firewall for outbound SMTP connections

4. **Missing Branch Reports**
   - Verify branch has data in the database
   - Check if branch is in email mapping
   - Ensure branch is enabled in mapping

## Monitoring and Logs

### Log Files
- SFTP sync logs: `logs/sftp_sync_YYYYMMDD_HHMMSS.log`
- Contains details of downloads, data loading, report generation, and email sending

### Database Backups
- Automatic backups created before each sync
- Located at: `db/branch_wise_location.db.backup_YYYYMMDD_HHMMSS`

### Report Archives
- Reports stored in: `branch_reports/`
- Format: `D##_report_YYYYMMDD.html`

## Customization Options

### Disable Emails Temporarily
```bash
# Via environment variable
SEND_EMAILS=false ./scripts/daily_sync.sh

# Or in sftp_config.json
"send_emails": false
```

### Use Yesterday's Date
```bash
# For files with yesterday's date
make sftp_sync_yesterday
```

### Skip Specific Branches
In `branch_email_mapping.json`, set:
```json
"enabled": false
```

## Security Best Practices

1. **Never commit config files with credentials**
   - All `*.json` config files are gitignored
   - Only `*.json.example` files are tracked

2. **Use SSH keys for SFTP when possible**
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/sftp_key
   ```

3. **Use app-specific passwords for email**
   - Gmail: Generate app password in account settings
   - Office 365: Use app passwords or OAuth2

4. **Restrict file permissions**
   ```bash
   chmod 600 configs/*.json
   ```

## Integration with Existing Systems

The workflow can be integrated with:
- **Monitoring systems**: Check exit codes and parse logs
- **Notification systems**: Send alerts on failures
- **Data pipelines**: Chain with other ETL processes
- **Dashboard updates**: Trigger dashboard refresh after sync

## Support and Maintenance

- Check logs in `logs/` directory for detailed execution history
- Run components individually to isolate issues
- Use `--dry-run` flags to test without making changes
- Keep configuration examples updated with new features 