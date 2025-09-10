import { DateRange } from "react-day-picker"
import { format } from "date-fns"

// =============== Core Utilities ===============

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

// =============== Base Fetch Functions ===============

export async function fetchFromAnalyticsService(endpoint: string, options?: RequestInit): Promise<Response> {
  const baseUrl = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
  const url = `${baseUrl}/${endpoint}`
  
  return await fetch(url, {
    ...options,
    headers: {
      ...analyticsHeaders(),
      ...options?.headers
    }
  })
}

export async function fetchFromDataService(endpoint: string, options?: RequestInit): Promise<Response> {
  const directUrl = `${process.env.NEXT_PUBLIC_DATA_API_URL}/${endpoint}`

  // Try proxy first
  try {
    const response = await fetch(directUrl, {
      ...options,
      headers: {
        ...analyticsHeaders(),
        ...options?.headers
      }
    })
    return response
  } catch (error) {
    console.error(error)
    throw error
  }
}

export async function fetchFromAuthService(endpoint: string, options?: RequestInit): Promise<Response> {
  const authBase = process.env.NEXT_PUBLIC_AUTH_API_URL || ""
  const url = `${authBase}/${endpoint}`
  
  return await fetch(url, {
    credentials: "include",
    ...options,
  })
}

// =============== Analytics Service APIs ===============

export async function fetchDashboardStats(params: {
  selectedLocation?: string | null
  dateRange?: DateRange
  granularity?: string
  timezoneOffset?: number
}) {
  const queryParams = new URLSearchParams()
  
  if (params.selectedLocation) {
    queryParams.append('location_id', params.selectedLocation)
  }
  if (params.dateRange?.from) {
    queryParams.append('start_date', format(params.dateRange.from, 'yyyy-MM-dd'))
  }
  if (params.dateRange?.to) {
    queryParams.append('end_date', format(params.dateRange.to, 'yyyy-MM-dd'))
  }
  if (params.granularity) {
    queryParams.append('granularity', params.granularity)
  }
  if (params.timezoneOffset !== undefined) {
    queryParams.append('timezone_offset', params.timezoneOffset.toString())
  }
  
  // Try proxy first, then fallback to direct URL
  const proxyUrl = `/api/analytics/stats?${queryParams.toString()}`
  const directBase = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
  const directUrl = directBase ? `${directBase}/stats?${queryParams.toString()}` : ''
  
  try {
    return await fetch(proxyUrl, { headers: analyticsHeaders() })
  } catch (error) {
    if (directUrl) {
      return await fetch(directUrl, { headers: analyticsHeaders() })
    }
    throw error
  }
}

export async function fetchLocations(signal?: AbortSignal) {
  // Try proxy first
  const proxyUrl = '/api/analytics/locations'
  const directBase = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
  const directUrl = directBase ? `${directBase}/locations` : ''
  
  try {
    return await fetch(proxyUrl, {
      signal,
      headers: analyticsHeaders()
    })
  } catch (error) {
    if (directUrl && !signal?.aborted) {
      return await fetch(directUrl, {
        signal,
        headers: analyticsHeaders()
      })
    }
    throw error
  }
}

export async function fetchUserHistory(userId?: string | number, sessionId?: string) {
  if (userId) {
    return fetchFromAnalyticsService(`history/user?user_id=${userId}`)
  } else if (sessionId) {
    return fetchFromAnalyticsService(`history/session?session_id=${sessionId}`)
  }
  throw new Error('Either userId or sessionId is required')
}

// Task APIs
export async function fetchCartAbandonmentTasks(params: {
  selectedLocation?: string | null
  dateRange?: DateRange
  page?: number
  limit?: number
}) {
  const queryParams = buildApiQueryParams(params.selectedLocation || null, params.dateRange, {
    page: params.page || 1,
    limit: params.limit || 50
  })
  return fetchFromAnalyticsService(`tasks/cart-abandonment${queryParams}`)
}

export async function fetchPurchaseTasks(params: {
  selectedLocation?: string | null
  dateRange?: DateRange
  page?: number
  limit?: number
}) {
  const queryParams = buildApiQueryParams(params.selectedLocation || null, params.dateRange, {
    page: params.page || 1,
    limit: params.limit || 50
  })
  return fetchFromAnalyticsService(`tasks/purchases${queryParams}`)
}

export async function fetchPerformanceTasks(params: {
  selectedLocation?: string | null
  dateRange?: DateRange
  page?: number
  limit?: number
  query?: string
}) {
  const additionalParams: Record<string, string | number> = {
    page: (params.page || 1).toString(),
    limit: (params.limit || 50).toString(),
  }
  if (params.query) {
    additionalParams.query = params.query
  }
  
  const queryParams = buildApiQueryParams(params.selectedLocation || null, params.dateRange, additionalParams)
  return fetchFromAnalyticsService(`tasks/performance${queryParams}`)
}

export async function fetchRepeatVisitTasks(params: {
  selectedLocation?: string | null
  dateRange?: DateRange
  page?: number
  limit?: number
  query?: string
}) {
  const additionalParams: Record<string, string | number> = {
    page: (params.page || 1).toString(),
    limit: (params.limit || 50).toString(),
  }
  if (params.query) {
    additionalParams.query = params.query
  }
  
  const queryParams = buildApiQueryParams(params.selectedLocation || null, params.dateRange, additionalParams)
  return fetchFromAnalyticsService(`tasks/repeat-visits${queryParams}`)
}

export async function fetchSearchAnalysisTasks(params: {
  selectedLocation?: string | null
  dateRange?: DateRange
  page?: number
  limit?: number
  includeConverted?: boolean
  query?: string
}) {
  const additionalParams: Record<string, string | number> = {
    page: (params.page || 1).toString(),
    limit: (params.limit || 50).toString(),
    include_converted: (params.includeConverted || true).toString(),
  }
  if (params.query) {
    additionalParams.query = params.query
  }
  
  const queryParams = buildApiQueryParams(params.selectedLocation || null, params.dateRange, additionalParams)
  return fetchFromAnalyticsService(`tasks/search-analysis${queryParams}`)
}

// =============== Data Service APIs ===============

export async function fetchDataAvailability() {
  return fetchFromDataService('data-availability')
}

export async function fetchJobs(params: {
  limit?: number
  offset?: number
}) {
  const queryParams = new URLSearchParams()
  if (params.limit) queryParams.append('limit', params.limit.toString())
  if (params.offset) queryParams.append('offset', params.offset.toString())
  
  const query = queryParams.toString() ? `?${queryParams.toString()}` : ''
  return fetchFromDataService(`jobs${query}`)
}

export async function createIngestionJob(data: {
  start_date: string
  end_date: string
  data_types: string[]
}) {
  return fetchFromDataService('ingest', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })
}

// =============== Auth Service APIs ===============

export async function authenticateWithCode(code: string) {
  return fetchFromAuthService('/authenticate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ code }),
  })
}

export async function getSyncStatus(tenantId: string) {
  return fetchFromAuthService(`/tenant/sync/status?tenant_id=${encodeURIComponent(tenantId)}`)
}

export async function startSync(tenantId: string) {
  return fetchFromAuthService('/tenant/sync/start', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ tenant_id: tenantId }),
  })
}

// =============== Email Management APIs ===============

export async function fetchEmailConfig() {
  return fetchFromAnalyticsService('email/config')
}

export async function fetchBranchEmailMappings() {
  return fetchFromAnalyticsService('email/mappings')
}

export async function updateBranchEmailMappings(mappings: any[]) {
  return fetchFromAnalyticsService('email/mappings', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(mappings),
  })
}

export async function sendEmailReports(data: {
  report_date: string
  branch_codes?: string[]
}) {
  return fetchFromAnalyticsService('email/send-reports', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })
}

export async function fetchEmailJobs(params: {
  page?: number
  limit?: number
  status?: string
}) {
  const queryParams = new URLSearchParams()
  if (params.page) queryParams.append('page', params.page.toString())
  if (params.limit) queryParams.append('limit', params.limit.toString())
  if (params.status) queryParams.append('status', params.status)
  
  const query = queryParams.toString() ? `?${queryParams.toString()}` : ''
  return fetchFromAnalyticsService(`email/jobs${query}`)
}

export async function fetchEmailJobStatus(jobId: string) {
  return fetchFromAnalyticsService(`email/jobs/${jobId}`)
}

export async function fetchEmailHistory(params: {
  page?: number
  limit?: number
  status?: string
  branch_code?: string
}) {
  const queryParams = new URLSearchParams()
  if (params.page) queryParams.append('page', params.page.toString())
  if (params.limit) queryParams.append('limit', params.limit.toString())
  if (params.status) queryParams.append('status', params.status)
  if (params.branch_code) queryParams.append('branch_code', params.branch_code)
  
  const query = queryParams.toString() ? `?${queryParams.toString()}` : ''
  return fetchFromAnalyticsService(`email/history${query}`)
}