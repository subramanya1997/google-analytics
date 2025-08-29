import { DateRange } from "react-day-picker"
import { format } from "date-fns"

export function buildApiQueryParams(
  selectedLocation: string | null,
  dateRange: DateRange | undefined,
  additionalParams?: Record<string, string>
): string {
  const params = new URLSearchParams()
  
  // Example tenant_id
  params.append('tenant_id', '550e8400-e29b-41d4-a716-446655440000')
  
  if (selectedLocation) {
    params.append('location_id', selectedLocation)
  }
  
  if (dateRange?.from) {
    params.append('start_date', format(dateRange.from, 'yyyy-MM-dd'))
  }
  
  if (dateRange?.to) {
    params.append('end_date', format(dateRange.to, 'yyyy-MM-dd'))
  }
  
  if (additionalParams) {
    Object.entries(additionalParams).forEach(([key, value]) => {
      params.append(key, value)
    })
  }
  
  return params.toString() ? `?${params.toString()}` : ''
} 