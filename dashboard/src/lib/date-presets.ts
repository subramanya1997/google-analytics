import { subDays, startOfDay, isSameDay } from "date-fns"
import { DateRange } from "react-day-picker"

/** Compute a preset date range ending at yesterday. */
export function getPresetRange(days: number): DateRange {
  const end = startOfDay(subDays(new Date(), 1))
  const start = startOfDay(subDays(end, days - 1))
  return { from: start, to: end }
}

/** Check whether a date range matches a given preset (by day count). */
export function isPresetActive(dateRange: DateRange | undefined, days: number): boolean {
  if (!dateRange?.from || !dateRange?.to) return false
  const { from, to } = getPresetRange(days)
  return isSameDay(dateRange.from, from!) && isSameDay(dateRange.to, to!)
}
