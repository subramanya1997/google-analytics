# Google Analytics Intelligence Dashboard

A modern, responsive web dashboard for Google Analytics intelligence system. Built with Next.js 15, TypeScript, Tailwind CSS, and Shadcn/ui components for optimal user experience and developer productivity.

## 🎯 Overview

The dashboard provides a comprehensive interface for sales teams to analyze customer behavior, track performance metrics, and manage actionable tasks derived from Google Analytics data. It features real-time analytics, task management, email automation, and data ingestion controls.

## ✨ Key Features

### 🔐 Authentication & Security
- **OAuth 2.0 Integration**: Secure authentication flow with backend services
- **JWT Token Management**: Automatic token handling and refresh
- **Multi-tenant Support**: Isolated data access per organization
- **Auth Guard**: Protected routes with automatic redirects

### 📊 Analytics Dashboard
- **Real-time Metrics**: Revenue, purchases, cart abandonment, search analytics
- **Interactive Charts**: Time-series data visualization with Recharts
- **Location Filtering**: Branch/location-specific analytics
- **Date Range Selection**: Flexible date filtering with presets
- **Performance Monitoring**: Page bounce rates and user experience metrics

### 📋 Task Management
- **Purchase Follow-ups**: Customer contact management after purchases
- **Cart Recovery**: Abandoned cart recovery workflows
- **Search Analysis**: Failed search term optimization
- **Repeat Visitors**: High-engagement visitor conversion
- **Performance Issues**: UX problem identification and resolution

### 📧 Email Management
- **Branch Mappings**: Configure sales rep assignments to branches
- **Report Automation**: Automated daily/weekly report sending
- **Email History**: Track all sent emails with status monitoring
- **Template Customization**: HTML email template management

### 🔧 Data Management
- **Data Ingestion**: Google Analytics data import controls
- **Job Monitoring**: Track data processing status and progress
- **Data Availability**: View available data ranges and statistics
- **Error Handling**: Comprehensive error reporting and recovery

### 🎨 User Experience
- **Responsive Design**: Mobile-first design with desktop optimization
- **Dark/Light Mode**: System preference detection with manual toggle
- **Accessibility**: WCAG compliant with keyboard navigation
- **Performance**: Optimized loading with skeleton states and caching

## 🛠️ Technology Stack

### Core Framework
- **Next.js 15**: React framework with App Router and server components
- **React 19**: Latest React with concurrent features
- **TypeScript**: Full type safety throughout the application

### UI & Styling
- **Tailwind CSS 4**: Utility-first CSS framework
- **Shadcn/ui**: High-quality, accessible component library
- **Radix UI**: Primitive components for complex interactions
- **Lucide React**: Beautiful, customizable icon library
- **Recharts**: Powerful charting library for data visualization

### State Management & Data
- **React Context**: Global state for user and dashboard data
- **TanStack Query**: Server state management with caching
- **React Hook Form**: Form handling with validation
- **Zod**: Runtime type validation and schema definition

### Developer Experience
- **TypeScript**: Complete type safety
- **ESLint**: Code linting with Next.js rules
- **Hot Reload**: Instant development feedback

## 📋 Prerequisites

### Required Software

1. **Node.js 18 or higher**
   ```bash
   node --version  # Should be 18+
   npm --version   # Should be 9+
   ```

2. **Backend Services Running**
   - Analytics Service (Port 8001)
   - Data Service (Port 8002)  
   - Auth Service (Port 8003)

### Environment Setup

1. **Create Environment File**
   ```bash
   # Copy example environment file
   cp env.example .env.local
   
   # Edit with your backend service URLs
   nano .env.local
   ```

2. **Required Environment Variables**
   ```env
   # Backend API URLs (Required)
   NEXT_PUBLIC_ANALYTICS_API_URL=http://localhost:8001/api/v1
   NEXT_PUBLIC_DATA_API_URL=http://localhost:8002/api/v1
   NEXT_PUBLIC_AUTH_API_URL=http://localhost:8003/api/v1
   
   # Optional: OAuth Configuration
   NEXT_PUBLIC_OAUTH_LOGIN_URL=http://localhost:8003/auth/login
   
   # Optional: Default Tenant for Development
   NEXT_PUBLIC_TENANT_ID=your_default_tenant_id
   ```

## 🚀 Installation & Setup

### 1. Install Dependencies
```bash
# Navigate to dashboard directory
cd dashboard

# Install all dependencies
npm install

# Or using yarn/pnpm
yarn install
pnpm install
```

### 2. Start Development Server
```bash
# Start development server with hot reload
npm run dev

# Access dashboard at http://localhost:3000
```

### 3. Production Build
```bash
# Build for production
npm run build

# Start production server
npm start
```

## 📁 Project Structure

```
dashboard/
├── public/                          # Static assets
│   ├── favicon.ico                 # App icon
│   └── *.svg                       # Icon assets
├── src/
│   ├── app/                        # Next.js App Router
│   │   ├── (dashboard)/           # Dashboard route group
│   │   │   ├── page.tsx           # Overview dashboard
│   │   │   ├── purchases/         # Purchase follow-up tasks
│   │   │   ├── cart-abandonment/  # Cart recovery tasks
│   │   │   ├── search-analysis/   # Search optimization
│   │   │   ├── repeat-visits/     # Repeat visitor engagement
│   │   │   ├── performance/       # Performance analytics
│   │   │   ├── data-management/   # Data ingestion controls
│   │   │   ├── email-management/  # Email automation
│   │   │   └── layout.tsx         # Dashboard layout wrapper
│   │   ├── oauth/                 # Authentication pages
│   │   │   ├── login/             # Login page
│   │   │   └── callback/          # OAuth callback handler
│   │   ├── globals.css            # Global styles and CSS variables
│   │   ├── layout.tsx             # Root layout with providers
│   │   └── favicon.ico            # App favicon
│   ├── components/                # Reusable components
│   │   ├── charts/               # Data visualization components
│   │   ├── email-management/     # Email-related components
│   │   ├── tasks/                # Task management components
│   │   ├── ui/                   # Base UI components (Shadcn/ui)
│   │   ├── app-sidebar.tsx       # Main navigation sidebar
│   │   ├── auth-guard.tsx        # Authentication protection
│   │   ├── layout-wrapper.tsx    # Dashboard layout with header
│   │   ├── nav-user.tsx          # User menu and logout
│   │   └── theme-provider.tsx    # Dark/light mode provider
│   ├── contexts/                 # React Context providers
│   │   ├── dashboard-context.tsx # Global dashboard state
│   │   └── user-context.tsx      # User authentication state
│   ├── hooks/                    # Custom React hooks
│   │   └── use-mobile.ts         # Mobile device detection
│   ├── lib/                      # Utility functions
│   │   ├── api-utils.ts          # API communication helpers
│   │   ├── page-config.ts        # Page metadata configuration
│   │   └── utils.ts              # General utility functions
│   └── types/                    # TypeScript type definitions
│       ├── api.ts                # API response types
│       ├── tasks.ts              # Task and business logic types
│       └── index.ts              # Type re-exports
├── components.json               # Shadcn/ui configuration
├── next.config.ts               # Next.js configuration with API proxies
├── package.json                 # Dependencies and scripts
├── tsconfig.json               # TypeScript configuration
├── postcss.config.mjs          # PostCSS configuration for Tailwind
├── eslint.config.mjs           # ESLint configuration
└── README.md                   # This file
```

## 📱 Pages & Features

### Dashboard Overview (`/`)
- **Metrics Cards**: Revenue, purchases, abandonment, searches, visitors
- **Activity Timeline**: Interactive time-series charts with granularity controls
- **Location Performance**: Branch-wise performance comparison
- **Responsive Layout**: Optimized for mobile and desktop viewing

### Task Management Pages

#### Purchases (`/purchases`)
- Purchase follow-up tasks with customer details
- Order values, product information, and contact data
- Priority scoring based on value and recency
- Expandable task cards with customer history

#### Cart Abandonment (`/cart-abandonment`)
- Abandoned cart recovery workflows
- Cart values, items, and customer information
- Time-based priority scoring
- Direct contact integration

#### Search Analysis (`/search-analysis`)
- Failed search terms requiring attention
- Customer search behavior patterns
- Search result optimization opportunities
- User context for failed searches

#### Repeat Visits (`/repeat-visits`)
- High-engagement visitors without conversions
- Visit patterns and product interests
- Conversion opportunity identification
- Detailed browsing history

#### Performance (`/performance`)
- Page bounce rate analysis
- UX issues affecting user experience
- Performance optimization recommendations
- Customer impact assessment

### Configuration Pages

#### Data Management (`/data-management`)
- Data availability overview
- Google Analytics data ingestion controls
- Job monitoring with detailed progress
- Error handling and retry mechanisms

#### Email Management (`/email-management`)
- Branch to sales rep mapping configuration
- Manual report sending with branch selection
- Email job monitoring and history
- Complete email audit trail

## 🔧 Development

### Local Development Setup

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Start Development Server**
   ```bash
   npm run dev
   ```

3. **Environment Configuration**
   ```bash
   # Ensure backend services are running
   cd ../backend
   make services_start
   
   # Return to dashboard and start
   cd ../dashboard
   npm run dev
   ```

### Code Quality & Standards

```bash
# Linting
npm run lint

# Type checking (automatic in development)
npx tsc --noEmit

# Build verification
npm run build
```

## 🔍 API Integration

### Backend Service Communication

The dashboard communicates with three backend services:

1. **Analytics Service** (Port 8001)
2. **Data Service** (Port 8002)
3. **Auth Service** (Port 8003)

### API Proxy Configuration

```typescript
// next.config.ts
const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/analytics/:path*',
        destination: `${ANALYTICS_API}/:path*`,
      },
      {
        source: '/api/data/:path*',
        destination: `${DATA_API}/:path*`,
      }
    ];
  },
};
```

## 🎨 Styling & Theming

### Design System
- **Color Palette**: Stone-based neutrals with blue accents
- **Typography**: Inter font family with consistent scale
- **Spacing**: 4px base unit with systematic spacing
- **Border Radius**: Consistent rounding with CSS variables
- **Shadows**: Subtle depth with multiple levels

### Theme Support
- Dark/Light mode with system preference detection
- CSS variables for consistent theming
- Automatic theme persistence

### Responsive Design
- Mobile-first approach
- Breakpoint-specific optimizations
- Touch-friendly interactions

## 🐛 Troubleshooting

### Common Issues

1. **Backend Connection Failed**
   ```bash
   # Check backend services
   curl http://localhost:8001/health
   curl http://localhost:8002/health  
   curl http://localhost:8003/health
   ```

2. **Authentication Issues**
   ```bash
   # Clear browser storage
   localStorage.clear()
   sessionStorage.clear()
   ```

3. **Build Errors**
   ```bash
   # Clear Next.js cache
   rm -rf .next
   npm install
   ```

## 🚀 Deployment

### Production Build
```bash
# Build optimized production bundle
npm run build

# Start production server
npm start
```

### Deployment Platforms

**Vercel (Recommended)**
```bash
vercel
```

**Docker**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## 📞 Support

### Getting Help
- Check browser console for errors
- Verify backend service connectivity
- Review environment variable configuration
- Check authentication status

### Common Commands Summary
```bash
# Development
npm install         # Install dependencies
npm run dev        # Start development
npm run build      # Production build
npm start          # Production server

# Maintenance  
npm run lint       # Code linting
rm -rf .next       # Clear cache
npm update         # Update dependencies
```

This dashboard provides a modern, performant interface for Google Analytics intelligence with comprehensive features for sales team productivity and data-driven decision making.
