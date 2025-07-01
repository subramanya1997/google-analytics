#!/bin/bash
# Daily SFTP sync and data loading script

# Set working directory to project root
cd "$(dirname "$0")/.." || exit 1

# Load environment variables if .env file exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default configuration file
CONFIG_FILE="${SFTP_CONFIG_FILE:-configs/sftp_config.json}"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found: $CONFIG_FILE"
    echo "Please create a config file based on configs/sftp_config.json.example"
    exit 1
fi

# Log file with date
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/sftp_sync_$(date +%Y%m%d_%H%M%S).log"

echo "Starting SFTP sync and data loading at $(date)" | tee "$LOG_FILE"
echo "Using configuration: $CONFIG_FILE" | tee -a "$LOG_FILE"

# Check if we should send emails (default to yes unless disabled)
SEND_EMAILS="${SEND_EMAILS:-true}"

# Run the sync script with report generation
if [ "$SEND_EMAILS" = "true" ]; then
    echo "Running sync with report generation and email sending..." | tee -a "$LOG_FILE"
    python scripts/sftp_sync_and_load.py --config "$CONFIG_FILE" --generate-reports --send-emails 2>&1 | tee -a "$LOG_FILE"
else
    echo "Running sync with report generation only (email disabled)..." | tee -a "$LOG_FILE"
    python scripts/sftp_sync_and_load.py --config "$CONFIG_FILE" --generate-reports 2>&1 | tee -a "$LOG_FILE"
fi

# Check exit code
EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
    echo "Sync completed successfully at $(date)" | tee -a "$LOG_FILE"
    
else
    echo "Sync failed with exit code $EXIT_CODE at $(date)" | tee -a "$LOG_FILE"
    
    # Optional: Send alert email or notification
    # echo "SFTP sync failed. Check log: $LOG_FILE" | mail -s "SFTP Sync Failed" admin@example.com
fi

# Clean up old logs (keep last 30 days)
find "$LOG_DIR" -name "sftp_sync_*.log" -type f -mtime +30 -delete

exit $EXIT_CODE 