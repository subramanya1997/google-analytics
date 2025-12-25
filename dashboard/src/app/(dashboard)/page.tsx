"use client"

import { useEffect, useState, useRef } from "react"
import { MetricCard } from "@/components/charts/metric-card"
import { OverviewChart, TimeGranularity } from "@/components/charts/overview-chart"
import { LocationStatsCard } from "@/components/charts/location-stats-card"
import { Skeleton } from "@/components/ui/skeleton"
import { useDashboard } from "@/contexts/dashboard-context"
import { fetchOverviewStats, fetchChartStats, fetchLocationStats } from "@/lib/api-utils"
import { DashboardMetrics, LocationStats, ChartDataPoint } from "@/types"
import { format } from "date-fns"
import {
  DollarSign,
  ShoppingCart,
  Search,
  Users,
  TrendingUp,
  AlertCircle,
  MapPin
} from "lucide-react"

export default function DashboardPage() {
  const { selectedLocation, setSelectedLocation, dateRange } = useDashboard()
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [locationStats, setLocationStats] = useState<LocationStats[]>([])
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  
  // Separate loading states for progressive loading
  const [loadingMetrics, setLoadingMetrics] = useState(true)
  const [loadingChart, setLoadingChart] = useState(true)
  const [loadingLocations, setLoadingLocations] = useState(true)
  
  const [timeGranularity, setTimeGranularity] = useState<TimeGranularity>("daily")

  // Track last fetched params to prevent duplicate requests
  const lastMetricsParams = useRef<string>("")
  const lastChartParams = useRef<string>("")
  const lastLocationsParams = useRef<string>("")

  // Fetch metrics when dateRange or selectedLocation changes
  useEffect(() => {
    if (!dateRange?.from || !dateRange?.to) return
    
    const params = `${format(dateRange.from, 'yyyy-MM-dd')}-${format(dateRange.to, 'yyyy-MM-dd')}-${selectedLocation || ''}`
    if (params === lastMetricsParams.current) return
    lastMetricsParams.current = params

    const fetchData = async () => {
      try {
        setLoadingMetrics(true)
        const response = await fetchOverviewStats({ selectedLocation, dateRange })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = await response.json()
        setMetrics(data)
      } catch (error) {
        console.error('Error fetching metrics:', error)
      } finally {
        setLoadingMetrics(false)
      }
    }
    fetchData()
  }, [dateRange, selectedLocation])

  // Fetch chart when dateRange, selectedLocation, or timeGranularity changes
  useEffect(() => {
    if (!dateRange?.from || !dateRange?.to) return
    
    const params = `${format(dateRange.from, 'yyyy-MM-dd')}-${format(dateRange.to, 'yyyy-MM-dd')}-${selectedLocation || ''}-${timeGranularity}`
    if (params === lastChartParams.current) return
    lastChartParams.current = params

    const fetchData = async () => {
      try {
        setLoadingChart(true)
        const response = await fetchChartStats({ selectedLocation, dateRange, granularity: timeGranularity })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = await response.json()
        setChartData(data || [])
      } catch (error) {
        console.error('Error fetching chart data:', error)
      } finally {
        setLoadingChart(false)
      }
    }
    fetchData()
  }, [dateRange, selectedLocation, timeGranularity])

  // Fetch location stats only when dateRange changes
  useEffect(() => {
    if (!dateRange?.from || !dateRange?.to) return
    
    const params = `${format(dateRange.from, 'yyyy-MM-dd')}-${format(dateRange.to, 'yyyy-MM-dd')}`
    if (params === lastLocationsParams.current) return
    lastLocationsParams.current = params

    const fetchData = async () => {
      try {
        setLoadingLocations(true)
        const response = await fetchLocationStats({ dateRange })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = await response.json()
        setLocationStats(data || [])
      } catch (error) {
        console.error('Error fetching location stats:', error)
      } finally {
        setLoadingLocations(false)
      }
    }
    fetchData()
  }, [dateRange])

  return (
    <div className="space-y-4 sm:space-y-6">
        {/* Metrics Cards - loads independently */}
        {loadingMetrics ? (
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

        {/* Chart - loads independently */}
        {loadingChart ? (
          <Skeleton className="h-[300px] sm:h-[400px]" />
        ) : (
          <OverviewChart 
            data={chartData} 
            dateRange={dateRange}
            timeGranularity={timeGranularity}
            onTimeGranularityChange={setTimeGranularity}
          />
        )}

        {/* Location Stats - loads independently */}
        <div className="space-y-4">
          <h3 className="text-base sm:text-lg font-semibold flex items-center gap-2">
            <MapPin className="h-4 w-4 sm:h-5 sm:w-5" />
            Performance by Location
          </h3>
          {loadingLocations ? (
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


