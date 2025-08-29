"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  ShoppingCart,
  Search,
  Users,
  TrendingUp,
  MapPin
} from "lucide-react"

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

interface LocationStatsCardProps {
  stats: LocationStats
  onClick?: () => void
}

export function LocationStatsCard({ stats, onClick }: LocationStatsCardProps) {
  return (
    <Card 
      className="hover:shadow-lg transition-shadow cursor-pointer" 
      onClick={onClick}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              {stats.locationName}
            </CardTitle>
            <CardDescription>
              {stats.city}, {stats.state} • {stats.locationId}
            </CardDescription>
          </div>
          <Badge variant="outline" className="text-lg font-semibold">
            {stats.totalRevenue}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <TrendingUp className="h-4 w-4" />
                <span>Purchases</span>
              </div>
              <span className="font-semibold">{stats.purchases}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <ShoppingCart className="h-4 w-4" />
                <span>Abandoned</span>
              </div>
              <span className="font-semibold">{stats.abandonedCarts}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Search className="h-4 w-4" />
                <span>Failed Searches</span>
              </div>
              <span className="font-semibold">{stats.failedSearches}</span>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Users className="h-4 w-4" />
                <span>Visitors</span>
              </div>
              <span className="font-semibold">{stats.totalVisitors}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Users className="h-4 w-4" />
                <span>Repeat Visits</span>
              </div>
              <span className="font-semibold">{stats.repeatVisits}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
} 