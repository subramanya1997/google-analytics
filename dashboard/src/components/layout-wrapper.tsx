"use client"

import { usePathname } from "next/navigation"
import { useDashboard } from "@/contexts/dashboard-context"
import { AppSidebar } from "@/components/app-sidebar"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { DateRangeSelector } from "@/components/ui/date-range-selector"
import { getPageInfo } from "@/lib/page-config"
import { useIsMobile } from "@/hooks/use-mobile"
import { Plus, Send, Clock, RefreshCw, MapPin } from "lucide-react"

export function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { selectedLocation, setSelectedLocation, dateRange, setDateRange, locations, loadingLocations } = useDashboard()
  const isMobile = useIsMobile()

  const { subtitle } = getPageInfo(pathname)
  const isDataManagementPage = pathname === '/data-management'
  const isEmailManagementPage = pathname === '/email-management'

  const handleAddMapping = () => {
    // Dispatch a custom event that the email management page can listen to
    window.dispatchEvent(new CustomEvent('openMappingDialog'))
  }

  const handleSendReports = () => {
    // Dispatch a custom event that the email management page can listen to
    window.dispatchEvent(new CustomEvent('openSendReportsDialog'))
  }

  const handleScheduleDataIngestion = () => {
    // Dispatch a custom event that the data management page can listen to
    window.dispatchEvent(new CustomEvent('openDataIngestionScheduler'))
  }

  const handleScheduleEmailReports = () => {
    // Dispatch a custom event that the email management page can listen to
    window.dispatchEvent(new CustomEvent('openEmailReportsScheduler'))
  }

  const handleRefreshData = () => {
    // Dispatch a custom event that the data management page can listen to
    window.dispatchEvent(new CustomEvent('refreshDataManagement'))
  }

  const handleRefreshEmail = () => {
    // Dispatch a custom event that the email management page can listen to
    window.dispatchEvent(new CustomEvent('refreshEmailManagement'))
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
          <div className="flex items-center gap-2">
            <SidebarTrigger className="md:hidden" />
            <div className="flex items-center gap-2 md:hidden">
              <span className="text-lg font-semibold tracking-tight">Impaqx Analytics</span>
            </div>
            <Breadcrumb className="hidden md:block">
              <BreadcrumbItem>
                <BreadcrumbPage className="truncate">{subtitle}</BreadcrumbPage>
              </BreadcrumbItem>
            </Breadcrumb>
          </div>
          <div className="ml-auto flex items-center gap-1 sm:gap-2">
            {isDataManagementPage && (
              <>
                <Button onClick={handleRefreshData} size="sm" variant="outline" className={isMobile ? "w-10 px-0" : ""}>
                  <RefreshCw className={`h-4 w-4 ${!isMobile ? 'mr-2' : ''}`} />
                  {!isMobile && 'Refresh'}
                </Button>
                <div className="h-4 w-px bg-border" />
                <Button onClick={handleScheduleDataIngestion} size="sm" variant="outline" className={isMobile ? "w-10 px-0" : ""}>
                  <Clock className={`h-4 w-4 ${!isMobile ? 'mr-2' : ''}`} />
                  {!isMobile && 'Schedule'}
                </Button>
              </>
            )}
            {isEmailManagementPage && (
              <>
                <Button onClick={handleRefreshEmail} size="sm" variant="outline" className={isMobile ? "w-10 px-0" : ""}>
                  <RefreshCw className={`h-4 w-4 ${!isMobile ? 'mr-2' : ''}`} />
                  {!isMobile && 'Refresh'}
                </Button>
                <div className="h-4 w-px bg-border" />
                <Button onClick={handleScheduleEmailReports} size="sm" variant="outline" className={isMobile ? "w-10 px-0" : ""}>
                  <Clock className={`h-4 w-4 ${!isMobile ? 'mr-2' : ''}`} />
                  {!isMobile && 'Schedule'}
                </Button>
                <Button onClick={handleSendReports} size="sm" variant="outline" className={isMobile ? "w-10 px-0" : ""}>
                  <Send className={`h-4 w-4 ${!isMobile ? 'mr-2' : ''}`} />
                  {!isMobile && 'Send'}
                </Button>
                <Button onClick={handleAddMapping} size="sm" variant="outline" className={isMobile ? "w-10 px-0" : ""}>
                  <Plus className={`h-4 w-4 ${!isMobile ? 'mr-2' : ''}`} />
                  {!isMobile && 'Add Mapping'}
                </Button>
              </>
            )}
            {!isDataManagementPage && !isEmailManagementPage && (
              <>
                <Select
                  value={selectedLocation || "all"}
                  onValueChange={(value) => setSelectedLocation(value === "all" ? null : value)}
                  disabled={loadingLocations}
                >
                  <SelectTrigger className={isMobile ? 'w-10 h-10 p-0 [&>svg:last-child]:hidden flex items-center justify-center' : 'w-full sm:w-[250px]'}>
                    {isMobile ? (
                      <MapPin className="h-4 w-4 shrink-0 text-foreground" />
                    ) : (
                      <>
                        <MapPin className="h-4 w-4 shrink-0 text-foreground" />
                        <SelectValue placeholder="Select location" />
                      </>
                    )}
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Locations</SelectItem>
                    {locations.map((location) => (
                      <SelectItem key={location.locationId} value={location.locationId}>
                        {location.locationName} - {location.city}, {location.state}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <DateRangeSelector
                  dateRange={dateRange}
                  onDateRangeChange={setDateRange}
                  className={isMobile ? "w-10" : "w-[200px] lg:w-[260px]"}
                  iconOnly={isMobile}
                />
              </>
            )}
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 p-4">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
