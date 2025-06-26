export interface Customer {
  name: string
  email: string
  phone?: string
  company?: string
}

export interface ProductDetail {
  name: string
  quantity: number
  price: number
}

export interface Task {
  id: string
  type: 'performance' | 'search' | 'repeat_visit' | 'purchase' | 'cart'
  priority: 'high' | 'medium' | 'low'
  title: string
  description: string
  customer: {
    name: string
    email: string
    phone?: string
    company?: string
    orderValue?: number
    lastOrder?: string
  }
  productDetails?: Array<{
    name: string
    quantity: number
    price: number
    sku?: string
  }>
  metadata?: {
    pageUrl?: string
    issueType?: string
    frequency?: number
    searchTerms?: string[]
    visitCount?: number
    products?: string[] | Array<{ title: string; url: string | null }>
    hasPurchase?: boolean
    cartValue?: number
    pageTitle?: string
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
  createdAt: string
  status?: 'pending' | 'in_progress' | 'completed'
  userId?: string | number
  sessionId?: string
} 