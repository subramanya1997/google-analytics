"use client"

import { Card, CardContent } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { format } from "date-fns"

interface OverviewChartProps {
  data: Array<{
    time: string
    purchases: number
    carts: number
    searches: number
  }>
  timeGranularity?: string
}

export function OverviewChart({ data, timeGranularity = "daily" }: OverviewChartProps) {
  // Format time for display on X-axis
  const formatXAxisTime = (timeStr: string) => {
    try {
      const date = new Date(timeStr)
      if (isNaN(date.getTime())) return timeStr
      
      switch (timeGranularity) {
        case "hourly":
          return format(date, "MMM d, HH:mm")
        case "4hours":
        case "12hours":
          return format(date, "MMM d, HH:mm")
        case "daily":
        default:
          return format(date, "MMM d")
      }
    } catch {
      return timeStr
    }
  }

  return (
    <Card>
      <CardContent className="p-6">
        <div className="h-[250px] sm:h-[350px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey="time" 
                className="text-xs"
                tick={{ fill: 'currentColor' }}
                tickFormatter={formatXAxisTime}
                interval="preserveStartEnd"
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
                labelFormatter={(label) => `Time: ${formatXAxisTime(label)}`}
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
                name="Cart Additions"
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