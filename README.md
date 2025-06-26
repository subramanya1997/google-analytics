# Impax Sales Intelligence System

A comprehensive sales intelligence and task management platform designed for multi-location retail operations. This system processes Google Analytics 4 (GA4) data to generate actionable insights and track sales-related tasks across different branch locations.

## 🚀 Key Features

- **Multi-Location Support**: Track and analyze performance across multiple branches/warehouses
- **Real-time Analytics Dashboard**: Next.js-based dashboard for monitoring key metrics
- **Task Management**: Track and manage sales tasks including:
  - Purchase follow-ups
  - Cart abandonment recovery
  - Failed search analysis
  - Repeat visitor conversion
- **Automated Reporting**: Generate branch-wise HTML reports with detailed task breakdowns
- **Data Pipeline**: ETL process for GA4 data with user and location enrichment
- **Export Capabilities**: Export data in multiple formats (CSV, JSON, SQL dumps)

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Contributing](#contributing)

## 🏗️ Architecture

The system consists of two main components:

1. **Data Processing Pipeline** (Python)
   - Loads GA4 data from JSONL files
   - Enriches with user and location data from Excel files
   - Stores in SQLite database with optimized indexes
   - Generates HTML reports for each branch

2. **Analytics Dashboard** (Next.js/TypeScript)
   - Real-time visualization of sales metrics
   - Task management interface
   - Location-based filtering
   - RESTful API for data access

## 📦 Prerequisites

- Python 3.8+
- Node.js 18+
- npm or yarn
- Git

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:subramanya1997/google-analytics.git
   cd google-analytics
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install dashboard dependencies**
   ```bash
   cd dashboard
   npm install
   cd ..
   ```

## ⚙️ Configuration

### Data Files Setup

Place the following files in the `data/` directory:

1. **GA4 Export**: `bq-results-*.jsonl` - Google Analytics 4 data export
2. **User Data**: `USER_LIST_FOR_AI*.xlsx` - User information mapping
3. **Location Data**: `Locations_List*.xlsx` - Branch/warehouse information

### Database Configuration

The system uses SQLite database stored at `db/branch_wise_location.db`. This is created automatically when you run the data pipeline.

## 🚀 Usage

### Quick Start

Run all data processing steps and start the dashboard:

```bash
# Process data and generate reports
make all

# Start the dashboard
make run_dashboard
```

### Individual Commands

```bash
# Load data into database
make load_data

# Export data to CSV/JSON
make export_report

# Generate HTML reports
make generate_report

# Clean generated files
make clean

# Start dashboard development server
make run_dashboard
```

### Manual Script Execution

```bash
# Load data with custom parameters
python scripts/load_data.py \
  --data-dir data \
  --excel-file USER_LIST_FOR_AI1749843290493.xlsx \
  --locations-file Locations_List1750281613134.xlsx \
  --out db/branch_wise_location.db

# Generate reports
python scripts/generate_branch_wise_report.py --db-path db/branch_wise_location.db

# Export database
python scripts/export_database.py --db-path db/branch_wise_location.db --format csv
```

## 📁 Project Structure

```
impax/
├── Makefile                 # Build automation
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── .gitignore             # Git ignore patterns
│
├── scripts/               # Data processing scripts
│   ├── load_data.py       # ETL pipeline for GA4 data
│   ├── export_database.py # Database export utilities
│   └── generate_branch_wise_report.py # HTML report generator
│
├── dashboard/             # Next.js web application
│   ├── src/
│   │   ├── app/          # Next.js app router pages
│   │   ├── components/   # React components
│   │   ├── lib/          # Utilities and database connection
│   │   └── types/        # TypeScript type definitions
│   ├── public/           # Static assets
│   └── package.json      # Node.js dependencies
│
├── data/                 # Data files (gitignored)
├── db/                   # Database files (gitignored)
├── branch_reports/       # Generated HTML reports (gitignored)
└── exports/              # Exported data files (gitignored)
```

## 📊 Database Schema

### Main Tables

- **users**: User information with contact details
- **locations**: Branch/warehouse information
- **purchase**: Purchase events from GA4
- **add_to_cart**: Cart addition events
- **page_view**: Page view tracking
- **no_search_results**: Failed search queries
- **task_tracking**: Task completion status

### Key Fields

- `user_prop_default_branch_id`: Links events to locations
- `param_transaction_id`: Unique purchase identifier
- `param_ga_session_id`: Session tracking
- `items_json`: Product details in JSON format

## 🔌 API Documentation

### Dashboard API Endpoints

- `GET /api/stats` - Overall statistics
- `GET /api/locations` - List all locations
- `GET /api/tasks/purchases` - Purchase follow-up tasks
- `GET /api/tasks/cart-abandonment` - Cart abandonment tasks
- `GET /api/tasks/search-analysis` - Search analysis tasks
- `GET /api/tasks/repeat-visits` - Repeat visit tasks
- `PUT /api/tasks/status` - Update task status

## 🛠️ Development

### Running in Development Mode

```bash
# Terminal 1: Start the dashboard
cd dashboard
npm run dev

# Terminal 2: Process new data
make all
```

### Adding New Event Types

1. Update `scripts/load_data.py` to handle new event types
2. Add corresponding API endpoint in `dashboard/src/app/api/`
3. Create UI components in `dashboard/src/components/`

### Testing

```bash
# Run data pipeline with sample data
python scripts/load_data.py --sample-lines 1000 ...

# Check database integrity
python scripts/export_database.py --db-path db/branch_wise_location.db --format json
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is proprietary software. All rights reserved.

## 🙏 Acknowledgments

- Built with [Next.js](https://nextjs.org/) and [Python](https://python.org/)
- UI components from [shadcn/ui](https://ui.shadcn.com/)
- Analytics powered by Google Analytics 4

---

For questions or support, please contact the development team. 