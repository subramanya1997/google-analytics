"use client"

import { usePathname } from "next/navigation"
import { useDashboard } from "@/contexts/dashboard-context"
import { AppSidebar } from "@/components/app-sidebar"
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { LocationSelector } from "@/components/ui/location-selector"
import { DateRangeSelector } from "@/components/ui/date-range-selector"
import { getPageInfo } from "@/lib/page-config"

export function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { selectedLocation, setSelectedLocation, dateRange, setDateRange } = useDashboard()

  const { subtitle } = getPageInfo(pathname)
  const isDataManagementPage = pathname === '/data-management'

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
          <Breadcrumb>
            <BreadcrumbItem>
              <BreadcrumbPage>{subtitle}</BreadcrumbPage>
            </BreadcrumbItem>
          </Breadcrumb>
          {!isDataManagementPage && (
            <div className="ml-auto flex items-center gap-2">
              <LocationSelector
                selectedLocation={selectedLocation}
                onLocationChange={setSelectedLocation}
                className="w-auto"
              />
              <DateRangeSelector
                dateRange={dateRange}
                onDateRangeChange={setDateRange}
                className="w-[200px] lg:w-[260px]"
              />
            </div>
          )}
        </header>
        <div className="flex flex-1 flex-col gap-4 p-4">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
