"use client"

import { Sidebar } from "./sidebar"
import { Header } from "./header"
import { useDashboard } from "@/contexts/dashboard-context"

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { selectedLocation, setSelectedLocation, dateRange, setDateRange } = useDashboard()

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header 
          selectedLocation={selectedLocation}
          onLocationChange={setSelectedLocation}
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
        />
        <main className="flex-1 overflow-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  )
} 