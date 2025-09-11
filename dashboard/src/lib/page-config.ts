export interface PageInfo {
  title: string
  subtitle: string
}

export const pageConfig: Record<string, PageInfo> = {
  "/": {
    title: "Analytics Dashboard",
    subtitle: "Real-time insights and performance metrics"
  },
  "/cart-abandonment": {
    title: "Cart Abandonment",
    subtitle: "Track and recover abandoned shopping sessions"
  },
  "/search-analysis": {
    title: "Search Analysis",
    subtitle: "Optimize search performance and user experience"
  },
  "/repeat-visits": {
    title: "Repeat Visits",
    subtitle: "Identify engaged visitors for targeted outreach"
  },
  "/performance": {
    title: "Performance Issues",
    subtitle: "Monitor and resolve user experience problems"
  },
  "/purchases": {
    title: "Recent Purchases",
    subtitle: "Track successful transactions and customer activity"
  },
  "/data-management": {
    title: "Data Management",
    subtitle: "Manage data ingestion and view system status"
  },
  "/email-management": {
    title: "Email Management",
    subtitle: "Manage email configurations and send reports"
  }
}

export const defaultPageInfo: PageInfo = {
  title: "Dashboard",
  subtitle: "Analytics and insights"
}

export function getPageInfo(pathname: string): PageInfo {
  return pageConfig[pathname] || defaultPageInfo
}
