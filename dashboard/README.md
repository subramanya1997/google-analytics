# Impax Analytics Dashboard

A modern, modular e-commerce analytics dashboard built with Next.js 14, Shadcn UI, and Tailwind CSS. This dashboard visualizes Google Analytics data and provides actionable insights for sales teams.

## Features

- 🎨 **Modern UI** - Built with Shadcn UI components and Tailwind CSS
- 🌓 **Dark/Light Mode** - Full theme support with system preference detection
- 📊 **Interactive Charts** - Powered by Recharts for data visualization
- 📱 **Fully Responsive** - Works seamlessly on desktop, tablet, and mobile
- 🧩 **Modular Architecture** - Reusable components for easy customization
- 🚀 **Performance Optimized** - Built on Next.js 14 with App Router

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **UI Components**: Shadcn UI
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Icons**: Lucide React
- **Theme**: next-themes
- **Language**: TypeScript

## Project Structure

```
dashboard/
├── src/
│   ├── app/                    # Next.js app router pages
│   │   ├── page.tsx           # Dashboard overview
│   │   ├── purchases/         # Purchase follow-up tasks
│   │   ├── cart-abandonment/  # Cart abandonment analysis
│   │   └── ...               # Other task pages
│   ├── components/
│   │   ├── layout/           # Layout components
│   │   │   ├── sidebar.tsx   # Navigation sidebar
│   │   │   ├── header.tsx    # Top header with theme toggle
│   │   │   └── dashboard-layout.tsx
│   │   ├── charts/           # Chart components
│   │   │   ├── overview-chart.tsx
│   │   │   ├── metric-card.tsx
│   │   │   └── category-chart.tsx
│   │   ├── tasks/            # Task management components
│   │   │   └── task-card.tsx
│   │   └── ui/               # Shadcn UI components
│   └── lib/                  # Utilities
└── public/                   # Static assets
```

## Getting Started

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Run the development server**:
   ```bash
   npm run dev
   ```

3. **Open your browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## Key Components

### Layout Components

- **Sidebar**: Modular navigation with badge counts for active tasks
- **Header**: Contains theme toggle and user menu
- **DashboardLayout**: Wrapper component for consistent page structure

### Chart Components

- **MetricCard**: Displays KPIs with trend indicators
- **OverviewChart**: Line chart for time-series data
- **CategoryChart**: Bar chart for categorical analysis

### Task Components

- **TaskCard**: Expandable card for displaying actionable tasks with:
  - Customer information
  - Suggested actions
  - Contact buttons (Call/Email)
  - Mark complete functionality

## Pages

1. **Overview** (`/`): Main dashboard with stats and task overview
2. **Purchases** (`/purchases`): Purchase follow-up tasks
3. **Cart Abandonment** (`/cart-abandonment`): Abandoned cart recovery tasks
4. **Search Analysis** (`/search-analysis`): Search-related tasks
5. **Repeat Visits** (`/repeat-visits`): Repeat visitor engagement tasks
6. **Performance** (`/performance`): Performance and UX issue tasks

## Customization

### Adding New Pages

1. Create a new folder in `src/app/`
2. Add a `page.tsx` file
3. Import and use the `DashboardLayout` component
4. Update navigation in `src/components/layout/sidebar.tsx`

### Adding New Components

Components are organized by type:
- Charts go in `src/components/charts/`
- Task-related components in `src/components/tasks/`
- Layout components in `src/components/layout/`

### Theming

The dashboard uses CSS variables for theming. Colors can be customized in:
- `src/app/globals.css` - Theme color definitions
- Light/dark mode automatically handled by next-themes

## Data Integration

Currently using mock data. To integrate with real data:

1. Replace mock data in page components with API calls
2. Connect to your SQLite database or API endpoint
3. Update task data structures as needed

## Build for Production

```bash
npm run build
npm start
```

## Deployment

The dashboard is optimized for deployment on Vercel:

```bash
vercel
```

Or deploy to any platform that supports Next.js applications.

## License

MIT
