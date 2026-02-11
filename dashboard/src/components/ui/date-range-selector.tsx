"use client"

import * as React from "react"
import { CalendarIcon } from "lucide-react"
import { DateRange } from "react-day-picker"
import { format, subDays, startOfDay, subMonths } from "date-fns"

import { cn } from "@/lib/utils"
import { getPresetRange, isPresetActive } from "@/lib/date-presets"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

interface DateRangeSelectorProps {
  dateRange: DateRange | undefined
  onDateRangeChange: (range: DateRange | undefined) => void
  className?: string
  iconOnly?: boolean
  /** Earliest available date (ISO string) to limit the calendar. Falls back to 365 days. */
  earliestDate?: string | null
  /** Latest available date (ISO string) shown in the availability footer. */
  latestDate?: string | null
}

const PRESETS = [
  { label: "Last 7 days", days: 7 },
  { label: "Last 15 days", days: 15 },
  { label: "Last 30 days", days: 30 },
  { label: "Last 60 days", days: 60 },
  { label: "Last 90 days", days: 90 },
] as const

export function DateRangeSelector({
  dateRange,
  onDateRangeChange,
  className,
  iconOnly = false,
  earliestDate,
  latestDate,
}: DateRangeSelectorProps) {
  const [open, setOpen] = React.useState(false)
  const [date, setDate] = React.useState<DateRange | undefined>(dateRange)
  const [numberOfMonths, setNumberOfMonths] = React.useState(2)

  React.useEffect(() => {
    const updateNumberOfMonths = () => {
      setNumberOfMonths(window.innerWidth >= 768 ? 2 : 1)
    }
    updateNumberOfMonths()
    window.addEventListener('resize', updateNumberOfMonths)
    return () => window.removeEventListener('resize', updateNumberOfMonths)
  }, [])

  React.useEffect(() => {
    setDate(dateRange)
  }, [dateRange])

  const handleDateChange = (newRange: DateRange | undefined) => {
    setDate(newRange)
    if (newRange?.from) {
      onDateRangeChange({
        from: startOfDay(newRange.from),
        to: startOfDay(newRange.to ?? newRange.from),
      })
    }
  }

  const formatDateRange = () => {
    if (!date?.from) return "Select date range"
    if (!date.to || date.from.getTime() === date.to.getTime()) {
      return `${format(date.from, "MMM d, yyyy")} - Select end date`
    }
    return `${format(date.from, "MMM d")} - ${format(date.to, "MMM d, yyyy")}`
  }

  const handlePresetClick = (days: number) => {
    const range = getPresetRange(days)
    setDate(range)
    onDateRangeChange(range)
  }

  const computedEarliestDate = React.useMemo(() => {
    if (earliestDate) return new Date(earliestDate)
    return subDays(new Date(), 365)
  }, [earliestDate])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id="date"
          variant="outline"
          size="sm"
          className={cn(
            "h-9 px-2 text-sm font-normal gap-1",
            iconOnly && "w-9 p-0 justify-center",
            !date && "text-muted-foreground",
            className
          )}
        >
          {iconOnly ? (
            <CalendarIcon className="h-4 w-4" />
          ) : (
            <>
              <CalendarIcon className="mr-2 h-4 w-4" />
              {formatDateRange()}
            </>
          )}
        </Button>
      </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="end">
          <div className="flex flex-col">
            {/* Preset buttons */}
            <div className="flex flex-wrap gap-2 p-3 border-b">
              {PRESETS.map((preset) => (
                <Button
                  key={preset.days}
                  size="sm"
                  variant={isPresetActive(date, preset.days) ? "default" : "outline"}
                  onClick={() => handlePresetClick(preset.days)}
                  className="text-xs"
                >
                  {preset.label}
                </Button>
              ))}
            </div>

            <Calendar
              initialFocus
              mode="range"
              defaultMonth={subMonths(date?.to || new Date(), 1)}
              selected={date}
              onSelect={handleDateChange}
              numberOfMonths={numberOfMonths}
              disabled={(d) => d > new Date() || d < computedEarliestDate}
              className="rounded-md"
            />

            {date?.from && (!date?.to || date.from.getTime() === date.to.getTime()) && (
              <div className="p-3 text-sm text-muted-foreground border-t bg-muted/50">
                <p className="font-medium">Click another date to complete the range</p>
                <p className="text-xs mt-1">Or use the preset buttons above</p>
              </div>
            )}

            {/* Data availability footer */}
            {earliestDate && (
              <div className="px-3 py-2 text-xs text-muted-foreground border-t">
                Data available from{" "}
                <span className="font-medium">{format(new Date(earliestDate), "MMM d, yyyy")}</span>
                {latestDate && (
                  <>
                    {" "}to{" "}
                    <span className="font-medium">{format(new Date(latestDate), "MMM d, yyyy")}</span>
                  </>
                )}
              </div>
            )}
          </div>
        </PopoverContent>
    </Popover>
  )
}
