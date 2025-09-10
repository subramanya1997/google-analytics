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

// ================================
// EMAIL MANAGEMENT API TYPES
// ================================

export interface EmailConfig {
  server: string
  port: number | string
  from_address: string
  username?: string
  password?: string
  use_tls?: boolean
  use_ssl?: boolean
}

export interface EmailConfigResponse {
  tenant_id: string
  config: EmailConfig | null
  configured: boolean
}

export interface BranchEmailMapping {
  id?: string
  branch_code: string
  branch_name?: string
  sales_rep_email: string
  sales_rep_name?: string
  is_enabled: boolean
  created_at?: string
  updated_at?: string
}

export interface BranchEmailMappingUpdateResponse {
  success: boolean
  message: string
  created: number
  updated: number
  total: number
}

export interface EmailJob {
  job_id: string
  status: string
  tenant_id: string
  report_date: string
  target_branches: string[]
  total_emails: number
  emails_sent: number
  emails_failed: number
  error_message?: string
  created_at: string
  started_at?: string
  completed_at?: string
  message?: string
}

export interface EmailJobsResponse {
  data: EmailJob[]
  total: number
  page: number
  limit: number
}

export interface EmailHistory {
  id: string
  job_id?: string
  branch_code: string
  sales_rep_email: string
  sales_rep_name?: string
  subject: string
  report_date: string
  status: string
  smtp_response?: string
  error_message?: string
  sent_at: string
}

export interface EmailHistoryResponse {
  data: EmailHistory[]
  total: number
  page: number
  limit: number
}

export interface SendReportsRequest {
  report_date: string
  branch_codes?: string[]
}