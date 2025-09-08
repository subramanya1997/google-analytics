// ================================
// COMMON API TYPES
// ================================

export interface ApiResponse<T> {
  data: T
  total?: number
  page?: number
  limit?: number
  has_more?: boolean
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  total: number
  page: number
  limit: number
  has_more: boolean
}

// ================================
// API REQUEST TYPES
// ================================

export interface PaginationParams {
  page?: number
  limit?: number
}

export interface FilterParams {
  query?: string
  location_id?: string
  start_date?: string
  end_date?: string
}

export interface TaskFetchParams extends PaginationParams, FilterParams {
  selectedLocation?: string | null
  dateRange?: {
    from: Date
    to: Date
  }
  includeConverted?: boolean
}

// ================================
// DASHBOARD API TYPES
// ================================

export interface DashboardMetrics {
  totalRevenue: string
  purchases: number
  abandonedCarts: number
  failedSearches: number
  totalVisitors: number
  repeatVisits: number
}

export interface LocationStats {
  locationId: string
  locationName: string
  city: string
  state: string
  totalRevenue: string
  purchases: number
  abandonedCarts: number
  failedSearches: number
  totalVisitors: number
  repeatVisits: number
}

export interface ChartDataPoint {
  time: string
  purchases: number
  carts: number
  searches: number
}

export interface DashboardApiResponse {
  metrics: DashboardMetrics
  locationStats: LocationStats[]
  chartData: ChartDataPoint[]
}

// ================================
// LOCATION API TYPES
// ================================

export interface Location {
  locationId: string
  locationName: string
  city: string
  state: string
}

// ================================
// DATA MANAGEMENT API TYPES
// ================================

export interface DataAvailability {
  earliest_date: string | null
  latest_date: string | null
  total_events: number
}

export interface IngestionJob {
  job_id: string
  status: string
  start_date: string
  end_date: string
  data_types: string[]
  created_at: string
  started_at?: string
  completed_at?: string
  records_processed?: Record<string, number>
  progress?: Record<string, number>
  error_message?: string
}

export interface JobsResponse {
  jobs: IngestionJob[]
  total: number
  limit: number
  offset: number
}
