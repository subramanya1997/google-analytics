"use client"

import { useEffect, useState, useCallback } from "react"
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

interface DashboardMetrics {
  totalRevenue: string
  purchases: number
  abandonedCarts: number
  failedSearches: number
  totalVisitors: number
  repeatVisits: number
}

interface LocationStats {
  locationId: string
  locationName: string
  city: string
  state: string
  totalRevenue: string
  purchases: number
  abandonedCarts: number
  failedSearches: number
  totalVisitors: number
  repeatVisits: number
}

interface ChartDataPoint {
  time: string
  purchases: number
  carts: number
  searches: number
}

interface DashboardApiResponse {
  metrics: DashboardMetrics
  locationStats: LocationStats[]
  chartData: ChartDataPoint[]
}

export default function DashboardPage() {
  const { selectedLocation, setSelectedLocation, dateRange } = useDashboard()
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [locationStats, setLocationStats] = useState<LocationStats[]>([])
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [timeGranularity, setTimeGranularity] = useState<TimeGranularity>("daily")

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true)
      
      // Get timezone offset in minutes
      const timezoneOffset = new Date().getTimezoneOffset()
      
      // Build URL with location and date filters
      const params = new URLSearchParams()
      // Add tenant_id
      params.append('tenant_id', '550e8400-e29b-41d4-a716-446655440000') // Example tenant_id
      if (selectedLocation) {
        params.append('location_id', selectedLocation)
      }
      if (dateRange?.from) {
        params.append('start_date', format(dateRange.from, 'yyyy-MM-dd'))
      }
      if (dateRange?.to) {
        params.append('end_date', format(dateRange.to, 'yyyy-MM-dd'))
      }
      params.append('granularity', timeGranularity)
      params.append('timezone_offset', (-timezoneOffset).toString()) // Negative because getTimezoneOffset returns opposite sign
      
      const baseUrl = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
      const url = `${baseUrl}/stats/dashboard?${params.toString()}`
        
      // Fetch stats
      const statsResponse = await fetch(url)
      const statsData: DashboardApiResponse = await statsResponse.json()
      setMetrics(statsData.metrics)
      setLocationStats(statsData.locationStats || [])
      setChartData(statsData.chartData)
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }, [selectedLocation, dateRange, timeGranularity])

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchDashboardData()
    }
  }, [dateRange, fetchDashboardData])

  return (
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

        {/* Location Breakdown - Always show */}
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
                {locationStats
                  .filter(location => !selectedLocation || location.locationId === selectedLocation)
                  .map((location) => (
                    <LocationStatsCard
                      key={location.locationId}
                      stats={location}
                      onClick={() => setSelectedLocation(location.locationId)}
                    />
                  ))}
              </div>
            )}
          </div>
      </div>
  )
}
