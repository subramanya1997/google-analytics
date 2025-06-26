// Utility functions for matching sessions to users
// Enhanced with better correlation and grouping capabilities

export interface User {
  user_id: number
  name: string
  email: string
  cell_phone?: string
  office_phone?: string
  customer_name?: string
  customer_erp_id?: string
  user_type?: string
}

export interface SessionUser {
  ga_session_id: string
  user_id: number
  identified_at: string
}

export interface UserGroup {
  company: string
  users: User[]
  totalPurchases: number
  totalValue: number
  lastActivity: string
}

// Cache for session-to-user mappings
const sessionUserCache = new Map<string, User>()

export async function getSessionUserMappings(db: any): Promise<SessionUser[]> {
  try {
    // Get unique session-user mappings from the page_view table
    const mappings = await db.all(`
      SELECT DISTINCT 
        param_ga_session_id as ga_session_id,
        CAST(user_prop_webuserid AS INTEGER) as user_id,
        MIN(event_timestamp) as identified_at
      FROM page_view
      WHERE user_prop_webuserid IS NOT NULL
      GROUP BY param_ga_session_id, user_prop_webuserid
    `)
    return mappings
  } catch (error) {
    console.error('Error fetching session-user mappings:', error)
    return []
  }
}

export async function correlateSessionToUser(
  sessionId: string,
  db: any,
  fallbackIndex?: number
): Promise<User | null> {
  // Check cache first
  if (sessionUserCache.has(sessionId)) {
    return sessionUserCache.get(sessionId)!
  }

  try {
    // Skip the session_users table check since it doesn't exist
    // Go directly to checking GA4 event data

    // Try to match by user properties in GA4 data
    // First try purchase table which has all user properties
    let sessionData = await db.get(`
      SELECT DISTINCT
        user_prop_webuserid,
        user_prop_webcustomerid,
        user_prop_bill_to_id,
        user_prop_ship_to_id
      FROM purchase 
      WHERE param_ga_session_id = ?
        AND user_prop_webuserid IS NOT NULL
      LIMIT 1
    `, sessionId)
    
    // If not found in purchase, try page_view
    if (!sessionData) {
      sessionData = await db.get(`
        SELECT DISTINCT
          user_prop_webuserid,
          user_prop_webcustomerid,
          user_prop_bill_to_id,
          user_prop_ship_to_id
        FROM page_view 
        WHERE param_ga_session_id = ?
          AND user_prop_webuserid IS NOT NULL
        LIMIT 1
      `, sessionId)
    }
    
    // If not found in page_view, try session_start
    if (!sessionData) {
      sessionData = await db.get(`
        SELECT DISTINCT
          user_prop_webuserid,
          user_prop_webcustomerid,
          user_prop_bill_to_id,
          user_prop_ship_to_id
        FROM session_start 
        WHERE param_ga_session_id = ?
          AND user_prop_webuserid IS NOT NULL
        LIMIT 1
      `, sessionId)
    }
    
    // Also check add_to_cart and no_search_results tables
    if (!sessionData) {
      sessionData = await db.get(`
        SELECT DISTINCT
          user_prop_webuserid,
          user_prop_webcustomerid,
          user_prop_bill_to_id,
          user_prop_ship_to_id
        FROM add_to_cart 
        WHERE param_ga_session_id = ?
          AND user_prop_webuserid IS NOT NULL
        LIMIT 1
      `, sessionId)
    }

    if (sessionData?.user_prop_webuserid) {
      const user = await db.get(
        'SELECT * FROM users WHERE user_id = ?',
        sessionData.user_prop_webuserid
      )
      if (user) {
        // Cache the mapping for future use (no database insert needed)
        sessionUserCache.set(sessionId, user)
        return user
      }
    }

    // Fallback to deterministic mapping if provided
    if (fallbackIndex !== undefined) {
      const users = await db.all('SELECT * FROM users WHERE user_type = "ECOMM" LIMIT 100')
      return users[fallbackIndex % users.length] || null
    }

    return null
  } catch (error) {
    console.error('Error correlating session to user:', error)
    return null
  }
}

export function matchUserToSession(
  sessionId: string, 
  users: User[], 
  index: number
): User {
  // Legacy function for backward compatibility
  const sessionHash = sessionId.split('').reduce((acc, char) => {
    return acc + char.charCodeAt(0)
  }, 0)
  
  const userIndex = sessionHash % users.length
  return users[userIndex] || users[index % users.length] || createDefaultUser(index)
}

export function createDefaultUser(index: number): User {
  return {
    user_id: 90000 + index,
    name: `Guest User`,
    email: '',
    customer_name: '',
    user_type: 'GUEST'
  }
}

export function groupUsersByCompany(users: User[]): Map<string, User[]> {
  const groups = new Map<string, User[]>()
  
  users.forEach(user => {
    const company = user.customer_name || 'Individual'
    if (!groups.has(company)) {
      groups.set(company, [])
    }
    groups.get(company)!.push(user)
  })
  
  return groups
}

export function prioritizeUsersByType(users: User[], preferredType: string = 'ECOMM'): User[] {
  const preferred = users.filter(u => u.user_type === preferredType)
  const others = users.filter(u => u.user_type !== preferredType)
  return [...preferred, ...others]
}

export function getUsersWithContactInfo(users: User[]): User[] {
  return users.filter(u => 
    u.email && u.email !== '' && 
    (u.cell_phone || u.office_phone)
  )
}

export function getUsersByPurchaseValue(users: User[], minValue: number): User[] {
  // This would need to be implemented with actual purchase data
  return users.filter(u => u.customer_erp_id) // Placeholder: assume ERP ID indicates business customer
}

export function getHighValueUsers(users: User[]): User[] {
  // Identify VIP customers based on various criteria
  return users.filter(u => {
    // Business customers with ERP integration
    if (u.customer_erp_id && u.customer_erp_id !== '90000') return true
    // Users with complete contact information
    if (u.email && u.cell_phone && u.customer_name) return true
    return false
  })
} 