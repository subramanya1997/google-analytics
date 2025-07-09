"use client"

import { usePathname } from "next/navigation"
import { LocationSelector } from "../ui/location-selector"
import { DateRangeSelector } from "../ui/date-range-selector"
import { DateRange } from "react-day-picker"

interface HeaderProps {
  selectedLocation: string | null
  onLocationChange: (locationId: string | null) => void
  dateRange: DateRange | undefined
  onDateRangeChange: (dateRange: DateRange | undefined) => void
}

export function Header({ selectedLocation, onLocationChange, dateRange, onDateRangeChange }: HeaderProps) {
  const pathname = usePathname()
  
  const getPageInfo = () => {
    switch (pathname) {
      case "/":
        return {
          title: "Analytics Dashboard",
          subtitle: "Real-time insights and performance metrics"
        }
      case "/cart-abandonment":
        return {
          title: "Cart Abandonment",
          subtitle: "Track and recover abandoned shopping sessions"
        }
      case "/search-analysis":
        return {
          title: "Search Analysis",
          subtitle: "Optimize search performance and user experience"
        }
      case "/repeat-visits":
        return {
          title: "Repeat Visits",
          subtitle: "Identify engaged visitors for targeted outreach"
        }
      case "/performance":
        return {
          title: "Performance Issues",
          subtitle: "Monitor and resolve user experience problems"
        }
      case "/purchases":
        return {
          title: "Recent Purchases",
          subtitle: "Track successful transactions and customer activity"
        }
      default:
        return {
          title: "Dashboard",
          subtitle: "Analytics and insights"
        }
    }
  }
  
  const { title, subtitle } = getPageInfo()
  
  return (
    <header className="relative z-10 border-b bg-white ml-0 lg:ml-14">
      <div className="flex flex-col sm:flex-row sm:items-center px-4 sm:px-6 py-4 gap-4">
        <div className="flex-1 ml-12 lg:ml-0">
          <h1 className="text-xl sm:text-2xl font-semibold line-clamp-1">{title}</h1>
          <p className="text-sm text-muted-foreground line-clamp-1">{subtitle}</p>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-4">
          <DateRangeSelector 
            dateRange={dateRange}
            className="w-full sm:w-[200px] lg:w-[260px]"
            onDateRangeChange={onDateRangeChange}
          />
          <LocationSelector 
            selectedLocation={selectedLocation}
            onLocationChange={onLocationChange}
            className="w-full sm:w-auto"
          />
        </div>
      </div>
    </header>
  )
} 