// Re-export all types from their respective files
export * from './tasks'
export * from './api'

// Export commonly used type combinations
export type { Task, Customer, ProductDetail, TaskType, TaskPriority, TaskStatus } from './tasks'
export type { 
  ApiResponse, 
  PaginatedResponse, 
  TaskFetchParams,
  EmailConfig,
  EmailConfigResponse,
  BranchEmailMapping,
  EmailJob,
  EmailJobsResponse,
  EmailHistory,
  EmailHistoryResponse,
  SendReportsRequest 
} from './api'
