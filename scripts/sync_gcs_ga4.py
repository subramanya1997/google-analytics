#!/usr/bin/env python3
"""
Connects to Google Cloud Storage and downloads GA4 files from a specified bucket.
Files are renamed to include their creation date.
"""
import os
import argparse
import logging
from datetime import datetime
from google.cloud import storage
from google.oauth2 import service_account
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def download_ga4_files_from_gcs(bucket_name: str, credentials_path: str, data_dir: str):
    """Downloads GA4 .json and .jsonl files from a GCS bucket."""
    try:
        # Load credentials from the service account file
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        storage_client = storage.Client(credentials=credentials)
        
        bucket = storage_client.bucket(bucket_name)
        
        logger.info(f"Checking for GA4 files in bucket: {bucket_name}")
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        blobs = bucket.list_blobs()
        
        downloaded_count = 0
        for blob in blobs:
            if blob.name.endswith('.json') or blob.name.endswith('.jsonl'):
                # Get the creation date and format it
                creation_date = blob.time_created.strftime('%Y-%m-%d')
                
                # Create the new filename
                original_path = Path(blob.name)
                new_filename = f"{original_path.stem}-{creation_date}{original_path.suffix}"
                local_filepath = os.path.join(data_dir, new_filename)
                
                logger.info(f"Downloading {blob.name} to {local_filepath}...")
                
                try:
                    blob.download_to_filename(local_filepath)
                    downloaded_count += 1
                except Exception as e:
                    logger.error(f"Failed to download {blob.name}: {e}")
        
        logger.info(f"Successfully downloaded {downloaded_count} GA4 files.")
        
    except Exception as e:
        logger.error(f"Failed to connect to GCS and download files: {e}")
        return False
        
    return True

def main():
    parser = argparse.ArgumentParser(description="Download GA4 files from GCS.")
    parser.add_argument("--bucket", default="herculesai", help="GCS bucket name.")
    parser.add_argument("--credentials", default="configs/gcp-storage.json", help="Path to GCS credentials file.")
    parser.add_argument("--data-dir", default="data", help="Local directory to save files.")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.credentials):
        logger.error(f"Credentials file not found: {args.credentials}")
        return 1
        
    if not download_ga4_files_from_gcs(args.bucket, args.credentials, args.data_dir):
        return 1
        
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
