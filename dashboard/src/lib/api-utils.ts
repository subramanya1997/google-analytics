import { DateRange } from "react-day-picker"
import { format } from "date-fns"

export function buildApiQueryParams(
  selectedLocation: string | null,
  dateRange: DateRange | undefined,
  additionalParams?: Record<string, string | number>
): string {
  const params = new URLSearchParams()
  
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
      params.append(key, String(value))
    })
  }
  
  return params.toString() ? `?${params.toString()}` : ''
} 

export function getTenantId(): string {
  return process.env.NEXT_PUBLIC_TENANT_ID || 'e0f01854-6c2e-4b76-bf7b-67f3c28dbdac'
}

export function analyticsHeaders(extra?: HeadersInit): HeadersInit {
  const base: HeadersInit = {
    'Accept': 'application/json',
    'X-Tenant-Id': getTenantId(),
  }
  if (!extra) return base
  // Merge, with extra taking precedence
  return { ...(base as Record<string, string>), ...(extra as Record<string, string>) }
}

export async function fetchFromDataService(endpoint: string, options?: RequestInit): Promise<Response> {
  const proxyUrl = `/api/data${endpoint}`
  const directUrl = process.env.NEXT_PUBLIC_DATA_API_URL 
    ? `${process.env.NEXT_PUBLIC_DATA_API_URL}/api/v1${endpoint}` 
    : null

  // Try proxy first
  try {
    const response = await fetch(proxyUrl, {
      ...options,
      headers: {
        ...analyticsHeaders(),
        ...options?.headers
      }
    })
    return response
  } catch (error) {
    // Fallback to direct URL if proxy fails
    if (directUrl) {
      return await fetch(directUrl, {
        ...options,
        headers: {
          ...analyticsHeaders(),
          ...options?.headers
        }
      })
    }
    throw error
  }
}