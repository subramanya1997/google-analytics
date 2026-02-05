"use client"

import * as React from "react"
import { CalendarIcon } from "lucide-react"
import { DateRange } from "react-day-picker"
import { format, subDays, startOfDay, subMonths } from "date-fns"

import { cn } from "@/lib/utils"
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
}

export function DateRangeSelector({
  dateRange,
  onDateRangeChange,
  className,
  iconOnly = false,
}: DateRangeSelectorProps) {
  const [open, setOpen] = React.useState(false)
  const [date, setDate] = React.useState<DateRange | undefined>(dateRange)
  const [numberOfMonths, setNumberOfMonths] = React.useState(2)

  React.useEffect(() => {
    // Set number of months based on screen size
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
    // Update local state immediately for responsive UI
    setDate(newRange)
    
    // Always update parent when selection changes
    if (newRange?.from) {
      // If we have both dates, use them as-is
      if (newRange.to) {
        const normalizedRange: DateRange = {
          from: startOfDay(newRange.from),
          to: startOfDay(newRange.to)
        }
        onDateRangeChange(normalizedRange)
        // Keep popover open - user will close by clicking outside
      } else {
        // If only start date, use it as both start and end temporarily
        const tempRange: DateRange = {
          from: startOfDay(newRange.from),
          to: startOfDay(newRange.from)
        }
        onDateRangeChange(tempRange)
        // Keep popover open for end date selection
      }
    }
  }

  const formatDateRange = () => {
    if (!date?.from) return "Select date range"
    
    if (!date.to || date.from.getTime() === date.to.getTime()) {
      return `${format(date.from, "MMM d, yyyy")} - Select end date`
    }
    
    return `${format(date.from, "MMM d")} - ${format(date.to, "MMM d, yyyy")}`
  }

  // Reset to default range if needed
  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen)
    
    // If closing without a complete selection, keep the current state
    // Don't reset as user might be clicking outside temporarily
  }

  // Preset ranges for quick selection
  const handlePresetClick = (days: number) => {
    const end = startOfDay(subDays(new Date(), 1)) // yesterday
    const start = startOfDay(subDays(end, days - 1))
    const range: DateRange = { from: start, to: end }
    setDate(range)
    onDateRangeChange(range)
    // Keep popover open - user will close by clicking outside
  }

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
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
            <div className="flex gap-2 p-3 border-b">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handlePresetClick(7)}
                className="text-xs"
              >
                Last 7 days
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handlePresetClick(15)}
                className="text-xs"
              >
                Last 15 days
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handlePresetClick(30)}
                className="text-xs"
              >
                Last 30 days
              </Button>
            </div>
            
            <Calendar
              initialFocus
              mode="range"
              defaultMonth={subMonths(date?.to || new Date(), 1)}
              selected={date}
              onSelect={handleDateChange}
              numberOfMonths={numberOfMonths}
              disabled={(date) => date > new Date() || date < subDays(new Date(), 45)}
              className="rounded-md"
            />
            
            {date?.from && (!date?.to || date.from.getTime() === date.to.getTime()) && (
              <div className="p-3 text-sm text-muted-foreground border-t bg-muted/50">
                <p className="font-medium">👆 Click another date to complete the range</p>
                <p className="text-xs mt-1">Or use the preset buttons above</p>
              </div>
            )}
          </div>
        </PopoverContent>
    </Popover>
  )
} 