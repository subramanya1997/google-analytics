"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardAction } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { DateRange } from "react-day-picker"
import { format } from "date-fns"
import { BarChart3 } from "lucide-react"

export type TimeGranularity = "hourly" | "4hours" | "12hours" | "daily"

interface OverviewChartProps {
  data: Array<{
    time: string
    purchases: number
    carts: number
    searches: number
  }>
  dateRange?: DateRange
  timeGranularity?: TimeGranularity
  onTimeGranularityChange?: (value: TimeGranularity) => void
}

export function OverviewChart({ 
  data, 
  dateRange, 
  timeGranularity = "daily",
  onTimeGranularityChange 
}: OverviewChartProps) {
  const formatDateRange = () => {
    if (!dateRange?.from || !dateRange?.to) return "Select date range"
    
    const fromDate = format(dateRange.from, "MMM d, yyyy")
    const toDate = format(dateRange.to, "MMM d, yyyy")
    
    if (fromDate === toDate) {
      return fromDate
    }
    
    return `${format(dateRange.from, "MMM d")} - ${format(dateRange.to, "MMM d, yyyy")}`
  }
  
  const getGranularityText = () => {
    switch (timeGranularity) {
      case "hourly": return "Hourly"
      case "4hours": return "4-hour"
      case "12hours": return "12-hour"
      case "daily": return "Daily"
      default: return "Daily"
    }
  }

  const formatXAxisLabel = (tickItem: string) => {
    try {
      const date = new Date(tickItem)
      
      // Check if we're on a smaller screen (simplified responsive check)
      const isSmallScreen = typeof window !== 'undefined' && window.innerWidth < 768
      
      const granularity = timeGranularity as string
      switch (granularity) {
        case "hourly":
          return isSmallScreen ? format(date, "HH:mm") : format(date, "MMM d, HH:mm")
        case "4hours":
        case "12hours":
          return isSmallScreen ? format(date, "MMM d\nHH:mm") : format(date, "MMM d, HH:mm")
        case "daily":
        default:
          return isSmallScreen ? format(date, "M/d") : format(date, "MMM d")
      }
    } catch {
      // Fallback for invalid dates
      return tickItem
    }
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base sm:text-lg font-semibold flex items-center gap-2">
          <BarChart3 className="h-4 w-4 sm:h-5 sm:w-5" />
          Activity Overview - {formatDateRange()}
        </CardTitle>
        <CardDescription className="text-xs sm:text-sm">
          {getGranularityText()} activity breakdown for purchases, cart additions, and searches
        </CardDescription>
        {onTimeGranularityChange && (
          <CardAction>
            <Tabs 
              value={timeGranularity} 
              onValueChange={(value) => onTimeGranularityChange(value as TimeGranularity)}
            >
              <TabsList className="h-8">
                <TabsTrigger value="hourly" className="text-xs px-3">Hourly</TabsTrigger>
                <TabsTrigger value="4hours" className="text-xs px-3">4 Hours</TabsTrigger>
                <TabsTrigger value="12hours" className="text-xs px-3">12 Hours</TabsTrigger>
                <TabsTrigger value="daily" className="text-xs px-3">Daily</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardAction>
        )}
      </CardHeader>
      <CardContent>
        <div className="h-[250px] sm:h-[350px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey="time" 
                className="text-xs"
                tick={{ fill: 'currentColor' }}
                interval="preserveStartEnd"
                tickFormatter={formatXAxisLabel}
              />
              <YAxis 
                className="text-xs"
                tick={{ fill: 'currentColor' }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                  fontSize: '12px'
                }}
                labelFormatter={(value) => formatXAxisLabel(value as string)}
              />
              <Legend 
                wrapperStyle={{ fontSize: '12px' }}
                iconSize={12}
              />
              <Line 
                type="monotone" 
                dataKey="purchases" 
                stroke="#10b981" 
                strokeWidth={2}
                dot={{ fill: '#10b981', strokeWidth: 2, r: 3 }}
                activeDot={{ r: 5 }}
                name="Purchases"
              />
              <Line 
                type="monotone" 
                dataKey="carts" 
                stroke="#f59e0b" 
                strokeWidth={2}
                dot={{ fill: '#f59e0b', strokeWidth: 2, r: 3 }}
                activeDot={{ r: 5 }}
                name="Abandoned Carts"
              />
              <Line 
                type="monotone" 
                dataKey="searches" 
                stroke="#3b82f6" 
                strokeWidth={2}
                dot={{ fill: '#3b82f6', strokeWidth: 2, r: 3 }}
                activeDot={{ r: 5 }}
                name="Searches"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
} 