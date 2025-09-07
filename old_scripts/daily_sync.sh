#!/bin/bash
# Daily data sync and loading script from GCS and SFTP

# Set working directory to project root
cd "$(dirname "$0")/.." || exit 1

# Load environment variables if .env file exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Configuration files
SFTP_CONFIG_FILE="${SFTP_CONFIG_FILE:-configs/sftp_config.json}"
GCS_CONFIG_FILE="${GCS_CONFIG_FILE:-configs/gcp-storage.json}"

# Log file with date
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/daily_sync_$(date +%Y%m%d_%H%M%S).log"

echo "Starting daily data sync at $(date)" | tee "$LOG_FILE"

# --- Step 1: Sync GA4 data from Google Cloud Storage ---
echo "--- Step 1: Syncing GA4 data from GCS ---" | tee -a "$LOG_FILE"
if [ ! -f "$GCS_CONFIG_FILE" ]; then
    echo "Error: GCS config file not found: $GCS_CONFIG_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

python scripts/sync_gcs_ga4.py --credentials "$GCS_CONFIG_FILE" 2>&1 | tee -a "$LOG_FILE"
GCS_EXIT_CODE=${PIPESTATUS[0]}

if [ $GCS_EXIT_CODE -ne 0 ]; then
    echo "GCS sync failed with exit code $GCS_EXIT_CODE at $(date)" | tee -a "$LOG_FILE"
    exit $GCS_EXIT_CODE
fi
echo "GCS sync completed successfully." | tee -a "$LOG_FILE"


# --- Step 2: Sync User Report from SFTP and process data ---
echo "--- Step 2: Syncing User Report from SFTP and loading data ---" | tee -a "$LOG_FILE"
if [ ! -f "$SFTP_CONFIG_FILE" ]; then
    echo "Error: SFTP config file not found: $SFTP_CONFIG_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

# Check if we should send emails (default to yes unless disabled)
SEND_EMAILS="${SEND_EMAILS:-true}"

# Run the SFTP sync and data loading script
if [ "$SEND_EMAILS" = "true" ]; then
    echo "Running SFTP sync with report generation and email sending..." | tee -a "$LOG_FILE"
    python scripts/sftp_sync_and_load.py --config "$SFTP_CONFIG_FILE" --generate-reports --send-emails 2>&1 | tee -a "$LOG_FILE"
else
    echo "Running SFTP sync with report generation only (email disabled)..." | tee -a "$LOG_FILE"
    python scripts/sftp_sync_and_load.py --config "$SFTP_CONFIG_FILE" --generate-reports 2>&1 | tee -a "$LOG_FILE"
fi

SFTP_EXIT_CODE=${PIPESTATUS[0]}

if [ $SFTP_EXIT_CODE -eq 0 ]; then
    echo "SFTP sync and data loading completed successfully at $(date)" | tee -a "$LOG_FILE"
else
    echo "SFTP sync and data loading failed with exit code $SFTP_EXIT_CODE at $(date)" | tee -a "$LOG_FILE"
    exit $SFTP_EXIT_CODE
fi

# Clean up old logs (keep last 30 days)
find "$LOG_DIR" -name "daily_sync_*.log" -type f -mtime +30 -delete

echo "Daily sync process finished successfully at $(date)" | tee -a "$LOG_FILE"
exit 0
