# SFTP Sync and Data Loading Guide

This guide explains how to use the SFTP synchronization script to automatically fetch `.jsonl` files and load them into the database.

## Overview

The SFTP sync script (`scripts/sftp_sync_and_load.py`) performs the following tasks:

1. Connects to an SFTP server
2. Downloads all `.jsonl` files
3. Optionally adds date suffixes to downloaded files
4. Cleans up old data in the data folder
5. Runs the data loading process
6. Creates database backups before cleaning
7. Generates branch-wise reports (optional)
8. Sends reports to sales representatives via email (optional)

## Installation

1. Install required Python packages:
   ```bash
   make install
   # or
   pip install -r requirements.txt
   ```

2. Create your configuration files:
   ```bash
   cp configs/sftp_config.json.example configs/sftp_config.json
   cp configs/smtp_config.json.example configs/smtp_config.json
   cp configs/branch_email_mapping.json.example configs/branch_email_mapping.json
   ```

3. Edit the SFTP configuration file with your credentials:
   ```json
   {
       "host": "your-sftp-server.com",
       "port": 22,
       "username": "your-username",
       "password": "your-password",
       "remote_path": "/path/to/jsonl/files",
       "data_dir": "data",
       "user_file": "USER_LIST_FOR_AI1749843290493.xlsx",
       "locations_file": "Locations_List1750281613134.xlsx",
               "db_path": "db/branch_wise_location.db",
        "use_yesterday": false,
        "no_date_suffix": false,
        "no_db_backup": false,
        "generate_reports": true,
        "send_emails": false
    }
    ```

4. Configure SMTP settings for email:
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

5. Configure branch-to-email mapping:
   ```json
   {
       "D01": {
           "branch_name": "Downtown Branch",
           "email": "john.doe@company.com",
           "name": "John Doe",
           "cc": "manager@company.com",
           "enabled": true
       }
   }
   ```

## Usage

### Using Make Commands

```bash
# Full sync (download + load data)
make sftp_sync

# Sync with yesterday's date suffix
make sftp_sync_yesterday

# Download files only (no data loading)
make sftp_download_only

# Full sync with report generation
make full_sync

# Full sync with report generation and email
make full_sync_with_email

# Send reports only (using existing reports)
make send_reports

# Test email configuration (dry run)
make send_reports_dry_run
```

### Using the Script Directly

```bash
# Basic usage with config file
python scripts/sftp_sync_and_load.py --config configs/sftp_config.json

# Command line options (override config)
python scripts/sftp_sync_and_load.py \
    --host sftp.example.com \
    --username myuser \
    --password mypass \
    --remote-path /data/exports

# Use SSH key instead of password
python scripts/sftp_sync_and_load.py \
    --host sftp.example.com \
    --username myuser \
    --key-path ~/.ssh/id_rsa

# Download with yesterday's date
python scripts/sftp_sync_and_load.py \
    --config configs/sftp_config.json \
    --use-yesterday

# Dry run (see what would happen)
python scripts/sftp_sync_and_load.py \
    --config configs/sftp_config.json \
    --dry-run
```

### Using the Daily Sync Script

```bash
# Run the daily sync wrapper
./scripts/daily_sync.sh

# Set custom config file via environment
SFTP_CONFIG_FILE=configs/my_config.json ./scripts/daily_sync.sh
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--host` | SFTP server hostname | Required |
| `--port` | SFTP server port | 22 |
| `--username` | SFTP username | Required |
| `--password` | SFTP password | None |
| `--key-path` | Path to SSH private key | None |
| `--remote-path` | Remote directory path | . |
| `--data-dir` | Local data directory | data |
| `--use-yesterday` | Use yesterday's date for suffix | False |
| `--no-date-suffix` | Don't add date suffix | False |
| `--user-file` | User Excel file name | USER_LIST_FOR_AI1749843290493.xlsx |
| `--locations-file` | Locations Excel file name | Locations_List1750281613134.xlsx |
| `--db-path` | Database output path | db/branch_wise_location.db |
| `--no-db-backup` | Don't backup database | False |
| `--config` | JSON configuration file | None |
| `--download-only` | Only download, don't load | False |
| `--load-only` | Only load, don't download | False |
| `--dry-run` | Show what would be done | False |
| `--generate-reports` | Generate branch reports after loading | False |
| `--send-emails` | Send reports via email | False |
| `--smtp-config` | SMTP configuration file | configs/smtp_config.json |
| `--branch-mapping` | Branch email mapping file | configs/branch_email_mapping.json |

## File Naming Convention

When downloaded, files can be renamed with date suffixes:

- Original: `bq-results-20250618-200504-1750277132291.jsonl`
- With today's date: `bq-results-20250618-200504-1750277132291_20250122.jsonl`
- With yesterday's date: `bq-results-20250618-200504-1750277132291_20250121.jsonl`

## Scheduling with Cron

To run the sync automatically, add to your crontab:

```bash
# Edit crontab
crontab -e

# Add daily sync at 2 AM
0 2 * * * cd /path/to/impax && ./scripts/daily_sync.sh
```

See `configs/crontab.example` for more scheduling examples.

## Security Considerations

1. **Configuration Files**: Keep your config files secure and never commit them to version control
   ```bash
   echo "configs/sftp_config.json" >> .gitignore
   ```

2. **SSH Keys**: Use SSH key authentication instead of passwords when possible
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/sftp_key
   ```

3. **Environment Variables**: For sensitive data, use environment variables
   ```bash
   export SFTP_PASSWORD="your-password"
   ```

## Troubleshooting

### Connection Issues

1. Check SFTP connectivity:
   ```bash
   sftp -P 22 username@host
   ```

2. Verify firewall settings allow port 22 (or custom port)

3. Check SSH key permissions:
   ```bash
   chmod 600 ~/.ssh/sftp_key
   ```

### File Download Issues

1. Check remote path exists:
   ```bash
   python scripts/sftp_sync_and_load.py --dry-run
   ```

2. Verify disk space:
   ```bash
   df -h data/
   ```

3. Check file permissions in data directory

### Data Loading Issues

1. Verify Excel files exist:
   ```bash
   ls -la data/*.xlsx
   ```

2. Check database permissions:
   ```bash
   ls -la db/
   ```

3. Review logs:
   ```bash
   tail -f logs/sftp_sync_*.log
   ```

## Logs

Logs are stored in the `logs/` directory with timestamps:
- `logs/sftp_sync_20250122_140532.log`

Old logs are automatically cleaned up after 30 days.

## Examples

### Example 1: Production Setup
```json
{
    "host": "sftp.analytics.company.com",
    "username": "ga4_exporter",
    "key_path": "/home/ubuntu/.ssh/ga4_sftp_key",
    "remote_path": "/exports/ga4/daily",
    "use_yesterday": true,
    "no_db_backup": false
}
```

### Example 2: Development Setup
```json
{
    "host": "localhost",
    "port": 2222,
    "username": "dev",
    "password": "dev123",
    "remote_path": "/test_data",
    "no_date_suffix": true
}
```

## Email Reporting

The system can automatically send branch-wise reports to sales representatives after data sync.

### Email Features

1. **Individual Branch Reports**: Each branch gets their own customized HTML report
2. **Rich HTML Emails**: The generated HTML reports are sent as the email body (not attachments)
3. **Professional Formatting**: Reports include inline CSS for proper rendering in all email clients
4. **Customizable Recipients**: Configure email, CC, and enable/disable per branch
5. **Batch Sending**: All emails are sent in a single SMTP session for efficiency

### Testing Email Configuration

```bash
# Test without sending
python scripts/send_branch_reports.py --dry-run

# Send report for specific branch
python scripts/send_branch_reports.py --branch D01

# Send all reports
python scripts/send_branch_reports.py
```

### Email Troubleshooting

1. **Gmail App Passwords**: For Gmail, use an app-specific password, not your regular password
2. **SMTP Ports**: Common ports are 587 (TLS) or 465 (SSL)
3. **Firewall**: Ensure outbound SMTP connections are allowed
4. **Rate Limits**: Some providers limit emails per minute/hour

### Disabling Emails

To disable emails temporarily:
```bash
# Via environment variable
SEND_EMAILS=false ./scripts/daily_sync.sh

# Or in the config file
"send_emails": false
```

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Run with `--dry-run` to test configuration
3. Use verbose logging by modifying the script's logging level
4. Test email configuration separately from sync process 