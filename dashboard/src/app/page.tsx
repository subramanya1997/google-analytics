"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { MetricCard } from "@/components/charts/metric-card"
import { OverviewChart } from "@/components/charts/overview-chart"
import { LocationStatsCard } from "@/components/charts/location-stats-card"
import { LocationSelector } from "@/components/ui/location-selector"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
  const [metrics, setMetrics] = useState<any>(null)
  const [locationStats, setLocationStats] = useState<any[]>([])
  const [chartData, setChartData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [dashboardDate, setDashboardDate] = useState<string>("")
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null)

  useEffect(() => {
    fetchDashboardData()
  }, [selectedLocation])

  const fetchDashboardData = async () => {
    try {
      // Build URL with location filter
      const url = selectedLocation 
        ? `/api/stats?locationId=${selectedLocation}`
        : '/api/stats'
        
      // Fetch stats
      const statsResponse = await fetch(url)
      const statsData = await statsResponse.json()
      setMetrics(statsData.metrics)
      setLocationStats(statsData.locationStats || [])
      setChartData(statsData.chartData)
      
      // Format the date from the latest event timestamp
      if (statsData.latestEventTimestamp) {
        const date = new Date(parseInt(statsData.latestEventTimestamp) / 1000)
        const formattedDate = date.toLocaleDateString('en-US', { 
          month: 'long', 
          day: 'numeric', 
          year: 'numeric' 
        })
        setDashboardDate(formattedDate)
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const subtitle = dashboardDate 
    ? `E-commerce analytics for ${dashboardDate}${selectedLocation ? ' (Filtered)' : ''}`
    : "E-commerce analytics"

  return (
    <DashboardLayout 
      title="Dashboard Overview"
      subtitle={subtitle}
    >
      <div className="space-y-6">
        {/* Location Selector */}
        <div className="flex justify-between items-center">
          <LocationSelector
            selectedLocation={selectedLocation}
            onLocationChange={setSelectedLocation}
          />
        </div>

        {/* Overall Metrics Grid */}
        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-[125px]" />
            ))}
          </div>
        ) : metrics && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
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

        {/* Tabs for different views */}
        <Tabs defaultValue="locations" className="space-y-4">
          <TabsList>
            <TabsTrigger value="locations" className="flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              Location Breakdown
            </TabsTrigger>
            <TabsTrigger value="activity" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Activity Timeline
            </TabsTrigger>
          </TabsList>

          <TabsContent value="locations" className="space-y-4">
            {/* Location Stats Grid */}
            {!selectedLocation && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Performance by Location</h3>
                {loading ? (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                      <Skeleton key={i} className="h-[200px]" />
                    ))}
                  </div>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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
          </TabsContent>

          <TabsContent value="activity" className="space-y-4">
            {/* Activity Chart */}
            <div className="lg:col-span-2">
              {loading ? (
                <Skeleton className="h-[400px]" />
              ) : (
                <OverviewChart data={chartData} />
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  )
}
