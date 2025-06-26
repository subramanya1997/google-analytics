"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"

interface OverviewChartProps {
  data: Array<{
    time: string
    purchases: number
    carts: number
    searches: number
  }>
}

export function OverviewChart({ data }: OverviewChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity Overview - June 12, 2025</CardTitle>
        <CardDescription>Hourly activity breakdown for purchases, cart additions, and searches</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="time" 
              className="text-xs"
              tick={{ fill: 'currentColor' }}
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
                borderRadius: '6px'
              }}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="purchases" 
              stroke="#10b981" 
              strokeWidth={3}
              dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6 }}
              name="Purchases"
            />
            <Line 
              type="monotone" 
              dataKey="carts" 
              stroke="#f59e0b" 
              strokeWidth={3}
              dot={{ fill: '#f59e0b', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6 }}
              name="Cart Additions"
            />
            <Line 
              type="monotone" 
              dataKey="searches" 
              stroke="#3b82f6" 
              strokeWidth={3}
              dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6 }}
              name="Searches"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
} 