.PHONY: all load_data export_report generate_report clean run_dashboard

# Variables
PYTHON = python
DATA_DIR = data
USER_FILE = USER_LIST_FOR_AI1749843290493.xlsx
LOCATIONS_FILE = Locations_List1750281613134.xlsx
DB_FILE = db/branch_wise_location.db
EXPORT_DIR = branch_reports
DASHBOARD_DIR = dashboard

all: load_data export_report generate_report

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
	@echo "Cleaning up generated files..."
	rm -f $(DB_FILE)
	rm -f $(EXPORT_DIR)/*.html 