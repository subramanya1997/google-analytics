.PHONY: all load_data export_report generate_report clean clean-all run_dashboard sftp_sync install

# Variables
PYTHON = python
DATA_DIR = data
USER_FILE = USER_LIST_FOR_AI1749843290493.xlsx
LOCATIONS_FILE = Locations_List1750281613134.xlsx
DB_FILE = db/branch_wise_location.db
EXPORT_DIR = branch_reports
DASHBOARD_DIR = dashboard
CONFIG_FILE = configs/sftp_config.json

all: load_data export_report generate_report

install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

sftp_sync:
	@echo "Running SFTP sync and data loading..."
	$(PYTHON) scripts/sftp_sync_and_load.py --config $(CONFIG_FILE)

sftp_sync_yesterday:
	@echo "Running SFTP sync with yesterday's date..."
	$(PYTHON) scripts/sftp_sync_and_load.py --config $(CONFIG_FILE) --use-yesterday

sftp_download_only:
	@echo "Downloading files from SFTP only..."
	$(PYTHON) scripts/sftp_sync_and_load.py --config $(CONFIG_FILE) --download-only

load_data:
	@echo "Loading data into the database..."
	$(PYTHON) scripts/load_data.py \
		--data-dir $(DATA_DIR) \
		--excel-file $(USER_FILE) \
		--locations-file $(LOCATIONS_FILE) \
		--out $(DB_FILE)

export_report:
	@echo "Exporting database to CSV..."
	$(PYTHON) scripts/export_database.py --db-path $(DB_FILE) --format csv

generate_report:
	@echo "Generating branch-wise reports..."
	$(PYTHON) scripts/generate_branch_wise_report.py --db-path $(DB_FILE)

run_dashboard:
	@echo "Starting the dashboard development server..."
	cd $(DASHBOARD_DIR) && npm run dev

clean:
	@echo "Basic cleanup of generated files..."
	rm -f $(DB_FILE)
	rm -f $(EXPORT_DIR)/*.html
	rm -rf logs/

clean-all:
	@echo "Running comprehensive cleanup..."
	./scripts/cleanup_project.sh

# Combined operations
full_sync: sftp_sync export_report generate_report
	@echo "Full sync and report generation completed"

full_sync_with_email: 
	@echo "Running full sync with report generation and email..."
	$(PYTHON) scripts/sftp_sync_and_load.py --config $(CONFIG_FILE) --generate-reports --send-emails

send_reports:
	@echo "Sending branch reports via email..."
	$(PYTHON) scripts/send_branch_reports.py

send_reports_dry_run:
	@echo "Testing email configuration (dry run)..."
	$(PYTHON) scripts/send_branch_reports.py --dry-run 