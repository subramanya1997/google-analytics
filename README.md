# Impax Sales Intelligence Dashboard

A Next.js dashboard for analyzing e-commerce data and generating sales tasks from Google Analytics events.

## Project Structure

```
impax/
├── dashboard/          # Next.js dashboard application
├── data/              # Source data files (JSONL, Excel)
├── scripts/           # Data processing scripts
│   ├── load_data.py   # Load GA4 data into SQLite (captures ALL fields)
│   └── export_database.py  # Export database to various formats
├── impax_enhanced.db  # SQLite database with complete GA4 data
├── idea.md           # Task types and requirements
└── enhanced_data_summary.md  # Summary of all captured data fields
```

## Database

The project uses `impax_enhanced.db` which contains:
- **26,261 events** from Google Analytics
- **100-130 fields per table** including:
  - User tracking (user_pseudo_id)
  - Device and browser information
  - Geographic location data
  - Traffic source and campaign details
  - Complete e-commerce transaction details
  - User properties and session tracking
  - Full product catalog with items

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install and run the dashboard:
```bash
cd dashboard
npm install
npm run dev
```

The dashboard will be available at http://localhost:3000

## Data Loading

To reload data from source files:
```bash
python scripts/load_data.py --data-dir data --excel-file USER_LIST_FOR_AI1749843290493.xlsx --out impax_enhanced.db
```

## Features

- 6 types of sales tasks based on customer behavior
- Real customer data integration
- Dark/light mode
- Responsive design
- Real-time data from SQLite database 