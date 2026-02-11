"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { DateRangeSelector } from "@/components/ui/date-range-selector"
import { Download, Play, RefreshCw } from "lucide-react"
import { format } from "date-fns"
import { toast } from "sonner"
import { createIngestionJob } from "@/lib/api-utils"
import type { DateRange } from "react-day-picker"

const DATA_TYPES = ["events", "users", "locations"] as const

function getDefaultDateRange(): DateRange {
  const today = new Date()
  const sevenDaysAgo = new Date()
  sevenDaysAgo.setDate(today.getDate() - 7)
  return { from: sevenDaysAgo, to: today }
}

interface DataIngestionCardProps {
  onJobCreated: () => void
}

export function DataIngestionCard({ onJobCreated }: DataIngestionCardProps) {
  const [dateRange, setDateRange] = useState<DateRange | undefined>(getDefaultDateRange)
  const [selectedDataTypes, setSelectedDataTypes] = useState<string[]>([...DATA_TYPES])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleDataTypeChange = (dataType: string, checked: boolean) => {
    setSelectedDataTypes((prev) =>
      checked ? [...prev, dataType] : prev.filter((t) => t !== dataType)
    )
  }

  const handleSubmit = async () => {
    if (!dateRange?.from || !dateRange?.to) {
      toast.error("Please select a date range")
      return
    }

    if (selectedDataTypes.length === 0) {
      toast.error("Please select at least one data type")
      return
    }

    try {
      setIsSubmitting(true)

      const response = await createIngestionJob({
        start_date: format(dateRange.from, "yyyy-MM-dd"),
        end_date: format(dateRange.to, "yyyy-MM-dd"),
        data_types: selectedDataTypes,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Failed to create ingestion job")
      }

      const jobData = await response.json()
      toast.success(`Job ${jobData.job_id} has been started and is now in progress!`, {
        description: `Processing ${selectedDataTypes.join(", ")} data from ${format(dateRange.from, "MMM d")} to ${format(dateRange.to, "MMM d, yyyy")}`,
      })

      // Reset form and notify parent
      setDateRange(getDefaultDateRange())
      setSelectedDataTypes([...DATA_TYPES])
      onJobCreated()
    } catch (error) {
      console.error("Error creating ingestion job:", error)
      toast.error(
        `Failed to create ingestion job: ${error instanceof Error ? error.message : String(error)}`
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Download className="h-5 w-5" />
          Data Ingestion
        </CardTitle>
        <CardDescription>
          Ingest new data or update existing data for specific date ranges
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Date Range</Label>
          <DateRangeSelector dateRange={dateRange} onDateRangeChange={setDateRange} />
        </div>

        <div className="space-y-3">
          <Label>Data Types to Process</Label>
          <div className="flex flex-wrap gap-4">
            {DATA_TYPES.map((dataType) => (
              <div key={dataType} className="flex items-center space-x-2">
                <Checkbox
                  id={dataType}
                  checked={selectedDataTypes.includes(dataType)}
                  onCheckedChange={(checked) => handleDataTypeChange(dataType, !!checked)}
                />
                <Label htmlFor={dataType} className="capitalize">
                  {dataType}
                </Label>
              </div>
            ))}
          </div>
        </div>

        <Button
          onClick={handleSubmit}
          disabled={isSubmitting || !dateRange?.from || !dateRange?.to}
          className="w-full"
        >
          {isSubmitting ? (
            <>
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              Creating Job...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Start Ingestion
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
