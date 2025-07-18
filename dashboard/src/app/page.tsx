"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { MetricCard } from "@/components/charts/metric-card"
import { OverviewChart } from "@/components/charts/overview-chart"
import { LocationStatsCard } from "@/components/charts/location-stats-card"
import { Skeleton } from "@/components/ui/skeleton"
import { TimeGranularitySelector, TimeGranularity } from "@/components/ui/time-granularity-selector"
import { useDashboard } from "@/contexts/dashboard-context"
import { format } from "date-fns"
import { 
  DollarSign, 
  ShoppingCart, 
  Search, 
  Users,
  TrendingUp,
  AlertCircle,
  MapPin,
  BarChart3
} from "lucide-react"

export default function DashboardPage() {
  const { selectedLocation, setSelectedLocation, dateRange } = useDashboard()
  const [metrics, setMetrics] = useState<any>(null)
  const [locationStats, setLocationStats] = useState<any[]>([])
  const [chartData, setChartData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [timeGranularity, setTimeGranularity] = useState<TimeGranularity>("daily")

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchDashboardData()
    }
  }, [selectedLocation, dateRange, timeGranularity])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      
      // Get timezone offset in minutes
      const timezoneOffset = new Date().getTimezoneOffset()
      
      // Build URL with location and date filters
      const params = new URLSearchParams()
      if (selectedLocation) {
        params.append('locationId', selectedLocation)
      }
      if (dateRange?.from) {
        params.append('startDate', format(dateRange.from, 'yyyy-MM-dd'))
      }
      if (dateRange?.to) {
        params.append('endDate', format(dateRange.to, 'yyyy-MM-dd'))
      }
      params.append('granularity', timeGranularity)
      params.append('timezoneOffset', (-timezoneOffset).toString()) // Negative because getTimezoneOffset returns opposite sign
      
      const url = `/api/stats${params.toString() ? `?${params.toString()}` : ''}`
        
      // Fetch stats
      const statsResponse = await fetch(url)
      const statsData = await statsResponse.json()
      setMetrics(statsData.metrics)
      setLocationStats(statsData.locationStats || [])
      setChartData(statsData.chartData)
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-4 sm:space-y-6">
        {/* Overall Metrics Grid */}
        {loading ? (
          <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-[125px]" />
            ))}
          </div>
        ) : metrics && (
          <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <MetricCard
              title="Total Revenue"
              value={metrics.totalRevenue}
              description={selectedLocation ? "Selected location" : "All locations"}
              icon={DollarSign}
            />
            <MetricCard
              title="Total Purchases"
              value={metrics.purchases}
              description="Completed orders"
              icon={TrendingUp}
            />
            <MetricCard
              title="Abandoned Carts"
              value={metrics.abandonedCarts}
              description="Need follow-up"
              icon={ShoppingCart}
            />
            <MetricCard
              title="Failed Searches"
              value={metrics.failedSearches}
              description="No results found"
              icon={Search}
            />
            <MetricCard
              title="Total Visitors"
              value={metrics.totalVisitors}
              description="Unique sessions"
              icon={Users}
            />
            <MetricCard
              title="Repeat Visits"
              value={metrics.repeatVisits}
              description="Multiple views"
              icon={AlertCircle}
            />
          </div>
        )}
        
        {/* Activity Timeline */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <h3 className="text-base sm:text-lg font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4 sm:h-5 sm:w-5" />
              Activity Timeline
            </h3>
            <TimeGranularitySelector 
              value={timeGranularity}
              onChange={setTimeGranularity}
              className="self-start sm:self-auto"
            />
          </div>
          {loading ? (
            <Skeleton className="h-[300px] sm:h-[400px]" />
          ) : (
            <OverviewChart 
              data={chartData} 
              dateRange={dateRange}
              timeGranularity={timeGranularity}
            />
          )}
        </div>

        {/* Location Breakdown - Only show when no location is selected */}
        {!selectedLocation && (
          <div className="space-y-4">
            <h3 className="text-base sm:text-lg font-semibold flex items-center gap-2">
              <MapPin className="h-4 w-4 sm:h-5 sm:w-5" />
              Performance by Location
            </h3>
            {loading ? (
              <div className="grid gap-3 sm:gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <Skeleton key={i} className="h-[200px]" />
                ))}
              </div>
            ) : (
              <div className="grid gap-3 sm:gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                {locationStats.map((location) => (
                  <LocationStatsCard
                    key={location.locationId}
                    stats={location}
                    onClick={() => setSelectedLocation(location.locationId)}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
