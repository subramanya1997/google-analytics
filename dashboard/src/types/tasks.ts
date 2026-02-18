// ================================
// CORE TYPES
// ================================

export type TaskType = 'performance' | 'search' | 'repeat_visit' | 'purchase' | 'cart'
export type TaskPriority = 'high' | 'medium' | 'low'
export type TaskStatus = 'pending' | 'in_progress' | 'completed'

// ================================
// CUSTOMER TYPES
// ================================

export interface Customer {
  id?: string
  name: string
  email?: string
  phone?: string
  office_phone?: string
  company?: string
  orderValue?: number
  lastOrder?: string
}

// ================================
// PRODUCT TYPES
// ================================

export interface ProductDetail {
  name: string
  quantity: number
  price: number
  sku?: string
}

export interface ProductReference {
  title: string
  url?: string | null
}

// ================================
// TASK METADATA TYPES
// ================================

export interface TaskMetadata {
  pageUrl?: string
  pageTitle?: string
  issueType?: string
  frequency?: number
  searchTerms?: string[]
  visitCount?: number
  productsViewed?: number
  products?: string[] | ProductReference[]
  hasPurchase?: boolean
  cartValue?: number
  lastSeen?: string
  lastBounce?: string
  bounceCount?: number
  lastVisit?: string
  location?: string
  branchId?: string
  transactionId?: string
  purchaseDate?: string
  daysSincePurchase?: number
}

// ================================
// MAIN TASK INTERFACE
// ================================

export interface Task {
  id: string
  type: TaskType
  priority: TaskPriority
  title: string
  description: string
  customer: Customer
  productDetails?: ProductDetail[]
  metadata?: TaskMetadata
  createdAt: string
  status?: TaskStatus
  userId?: string | number
  sessionId?: string
}

// ================================
// SPECIALIZED TASK TYPES
// ================================

export interface PurchaseCartTask extends Omit<Task, 'type'> {
  type: 'purchase' | 'cart'
  customer: Customer & {
    orderValue?: number
  }
  metadata?: TaskMetadata & {
    cartValue?: number
    products?: string[]
    visitCount?: number
    location?: string
    branchId?: string
  }
}

// ================================
// API RESPONSE TYPES
// ================================

export interface PurchaseApiProduct {
  item_name: string
  quantity: number
  price: number
  item_id: string
}

export interface PurchaseApiTask {
  transaction_id: string
  user_id: string
  customer_name?: string
  email?: string
  phone?: string
  office_phone?: string
  order_value: number
  products: PurchaseApiProduct[]
  event_date: string
  session_id: string
}

export interface PurchaseApiResponse {
  data: PurchaseApiTask[]
  total: number
  page: number
  limit: number
  has_more: boolean
}

export interface CartApiProduct {
  item_name: string
  quantity: number
  price: number
  item_id: string
}

export interface CartApiTask {
  session_id: string
  user_id: string
  customer_name?: string
  email?: string
  phone?: string
  office_phone?: string
  total_value: number
  items_count: number
  products: CartApiProduct[]
  event_date: string
}

export interface CartApiResponse {
  data: CartApiTask[]
  total: number
  page: number
  limit: number
  has_more: boolean
}

export interface SearchAnalysisApiTask {
  session_id: string
  user_id: string
  customer_name?: string
  email?: string
  phone?: string
  office_phone?: string
  search_term: string | null
  search_count: number
  search_type: string
  event_date: string
  location_id?: string
}

export interface SearchAnalysisApiResponse {
  data: SearchAnalysisApiTask[]
  facets?: {
    search_types?: FacetItem[]
  }
  total?: number
}

export interface RepeatVisitApiTask {
  session_id: string
  user_id: string
  customer_name?: string
  email?: string
  phone?: string
  office_phone?: string
  page_views_count: number
  products_viewed?: number
  event_date: string
  products_details?: ProductReference[]
}

export interface RepeatVisitApiResponse {
  data: RepeatVisitApiTask[]
  total?: number
}

export interface PerformanceApiTask {
  session_id: string
  user_id: string
  customer_name?: string
  email?: string
  phone?: string
  office_phone?: string
  entry_page: string
  location_id?: string
  event_date: string
}

export interface FrequentlyBouncedPage {
  entry_page: string
  bounce_count: number
}

export interface FacetItem {
  value: string
  label: string
  count: number
}

export interface PerformanceApiResponse {
  data: {
    bounced_sessions: PerformanceApiTask[]
    frequently_bounced_pages: FrequentlyBouncedPage[]
  }
  facets?: {
    issue_types?: FacetItem[]
  }
  total?: number
}

// ================================
// USER HISTORY TYPES
// ================================

export interface PurchaseHistoryItem {
  transaction_id: string
  event_date: string
  event_timestamp: string
  order_value: string
  items: ProductDetail[]
}

export interface SearchHistoryItem {
  term: string
  date: string
  results: number
}

export interface CartHistoryItem {
  session_id: string
  event_date: string
  event_timestamp: string
  cart_value: number
  items: ProductDetail[]
}

export interface ViewedProduct {
  sku: string
  name: string
  category: string
  price: number
  view_count: number
  last_viewed_date: string
  last_viewed_timestamp: string
}

export interface UserHistory {
  user: unknown
  purchaseHistory: PurchaseHistoryItem[]
  searchHistory: SearchHistoryItem[]
  cartHistory: CartHistoryItem[]
  viewedProductsHistory: ViewedProduct[]
}

// ================================
// COMPONENT PROP TYPES
// ================================

export interface TaskCardProps {
  task: PurchaseCartTask
}

export interface TaskDetailSheetProps {
  task: Task
  children: React.ReactNode
}

// ================================
// SORT AND FILTER TYPES
// ================================

export type SortField = 'metric' | 'lastVisit' | 'visitCount' | 'searchTerms' | 'attempts'
export type SortOrder = 'asc' | 'desc'