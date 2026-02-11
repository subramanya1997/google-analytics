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
import { Plus, Send, Clock, RefreshCw, MapPin, type LucideIcon } from "lucide-react"

function emit(name: string) {
  window.dispatchEvent(new CustomEvent(name))
}

function HeaderButton({ icon: Icon, label, onClick, isMobile }: {
  icon: LucideIcon
  label: string
  onClick: () => void
  isMobile: boolean
}) {
  return (
    <Button onClick={onClick} size="sm" variant="outline" className={isMobile ? "w-10 px-0" : ""}>
      <Icon className={`h-4 w-4 ${!isMobile ? 'mr-2' : ''}`} />
      {!isMobile && label}
    </Button>
  )
}

export function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { selectedLocation, setSelectedLocation, dateRange, setDateRange, locations, loadingLocations, dataAvailability } = useDashboard()
  const isMobile = useIsMobile()

  const { subtitle } = getPageInfo(pathname)
  const isDataManagementPage = pathname === '/data-management'
  const isEmailManagementPage = pathname === '/email-management'

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
                <HeaderButton icon={RefreshCw} label="Refresh" onClick={() => emit('refreshDataManagement')} isMobile={isMobile} />
                <div className="h-4 w-px bg-border" />
                <HeaderButton icon={Clock} label="Schedule" onClick={() => emit('openDataIngestionScheduler')} isMobile={isMobile} />
              </>
            )}
            {isEmailManagementPage && (
              <>
                <HeaderButton icon={RefreshCw} label="Refresh" onClick={() => emit('refreshEmailManagement')} isMobile={isMobile} />
                <div className="h-4 w-px bg-border" />
                <HeaderButton icon={Clock} label="Schedule" onClick={() => emit('openEmailReportsScheduler')} isMobile={isMobile} />
                <HeaderButton icon={Send} label="Send" onClick={() => emit('openSendReportsDialog')} isMobile={isMobile} />
                <HeaderButton icon={Plus} label="Add Mapping" onClick={() => emit('openMappingDialog')} isMobile={isMobile} />
              </>
            )}
            {!isDataManagementPage && !isEmailManagementPage && (
              <>
                <Select
                  value={selectedLocation || "all"}
                  onValueChange={(value) => setSelectedLocation(value === "all" ? null : value)}
                  disabled={loadingLocations}
                >
                  <SelectTrigger className={isMobile ? 'w-10 h-10 p-0 [&>svg:last-child]:hidden flex items-center justify-center' : 'h-9 px-2 text-sm w-auto max-w-[250px]'}>
                    {isMobile ? (
                      <MapPin className="h-4 w-4 shrink-0 text-foreground" />
                    ) : (
                      <>
                        <MapPin className="h-4 w-4 text-foreground" />
                        <SelectValue placeholder="Select location" className="truncate" />
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
                  iconOnly={isMobile}
                  earliestDate={dataAvailability?.earliest_date}
                  latestDate={dataAvailability?.latest_date}
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
