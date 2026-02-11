import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Label } from "@/components/ui/label"
import { Database } from "lucide-react"
import { format } from "date-fns"
import type { DataAvailability } from "@/types"

interface DataAvailabilityCardProps {
  loading: boolean
  data: DataAvailability | null
}

export function DataAvailabilityCard({ loading, data }: DataAvailabilityCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Data Availability
        </CardTitle>
        <CardDescription>
          View the range of data currently available in your analytics database
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-4 w-1/4" />
          </div>
        ) : data ? (
          <div className="grid gap-4">
            <div>
              <Label className="text-sm font-medium text-muted-foreground">Earliest Date</Label>
              <p className="text-lg font-semibold">
                {data.earliest_date
                  ? format(new Date(data.earliest_date), "MMM d, yyyy")
                  : "No data"}
              </p>
            </div>
            <div>
              <Label className="text-sm font-medium text-muted-foreground">Latest Date</Label>
              <p className="text-lg font-semibold">
                {data.latest_date
                  ? format(new Date(data.latest_date), "MMM d, yyyy")
                  : "No data"}
              </p>
            </div>
            <div>
              <Label className="text-sm font-medium text-muted-foreground">Total Events</Label>
              <p className="text-lg font-semibold">
                {data.total_events.toLocaleString()}
              </p>
            </div>
          </div>
        ) : (
          <p className="text-muted-foreground">Failed to load data availability</p>
        )}
      </CardContent>
    </Card>
  )
}
