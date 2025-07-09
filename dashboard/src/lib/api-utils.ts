import { DateRange } from "react-day-picker"
import { format } from "date-fns"

export function buildApiQueryParams(
  selectedLocation: string | null,
  dateRange: DateRange | undefined,
  additionalParams?: Record<string, string>
): string {
  const params = new URLSearchParams()
  
  if (selectedLocation) {
    params.append('locationId', selectedLocation)
  }
  
  if (dateRange?.from) {
    params.append('startDate', format(dateRange.from, 'yyyy-MM-dd'))
  }
  
  if (dateRange?.to) {
    params.append('endDate', format(dateRange.to, 'yyyy-MM-dd'))
  }
  
  if (additionalParams) {
    Object.entries(additionalParams).forEach(([key, value]) => {
      params.append(key, value)
    })
  }
  
  return params.toString() ? `?${params.toString()}` : ''
} 