"use client"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export type TimeGranularity = "hourly" | "4hours" | "12hours" | "daily"

interface TimeGranularitySelectorProps {
  value: TimeGranularity
  onChange: (value: TimeGranularity) => void
  className?: string
}

export function TimeGranularitySelector({ value, onChange, className }: TimeGranularitySelectorProps) {
  const options: Array<{ value: TimeGranularity; label: string }> = [
    { value: "hourly", label: "Hourly" },
    { value: "4hours", label: "4 Hours" },
    { value: "12hours", label: "12 Hours" },
    { value: "daily", label: "Daily" },
  ]

  return (
    <div className={cn("flex gap-1 p-1 bg-muted rounded-lg", className)}>
      {options.map((option) => (
        <Button
          key={option.value}
          variant={value === option.value ? "secondary" : "ghost"}
          size="sm"
          onClick={() => onChange(option.value)}
          className={cn(
            "h-7 px-3 text-xs font-medium transition-colors",
            value === option.value && "shadow-sm"
          )}
        >
          {option.label}
        </Button>
      ))}
    </div>
  )
} 