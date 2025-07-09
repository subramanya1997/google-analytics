import { NextResponse } from 'next/server'
import { getDb } from '@/lib/db'
import { correlateSessionToUser } from '@/lib/user-matching'
import { Task } from '@/types/tasks'

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const locationId = searchParams.get('locationId')
    const startDate = searchParams.get('startDate')
    const endDate = searchParams.get('endDate')
    
    const db = await getDb()
    
    // Build location filter
    const locationFilter = locationId ? `AND ac.user_prop_default_branch_id = '${locationId}'` : ''
    const purchaseLocationFilter = locationId ? `AND user_prop_default_branch_id = '${locationId}'` : ''
    
    // Build date filter
    let dateFilter = ''
    if (startDate && endDate) {
      // Convert ISO dates to YYYYMMDD format used in database
      const start = startDate.replace(/-/g, '')
      const end = endDate.replace(/-/g, '')
      dateFilter = `AND ac.event_date BETWEEN '${start}' AND '${end}'`
    }
    
    // Get abandoned cart sessions
    const query = `
      WITH abandoned_carts AS (
        SELECT DISTINCT
          ac.param_ga_session_id as session_id,
          ac.user_prop_webuserid as web_user_id,
          ac.user_prop_default_branch_id as branch_id,
          COUNT(DISTINCT ac.first_item_item_id) as unique_items,
          COUNT(*) as abandonments,
          SUM(CAST(ac.first_item_price AS REAL) * CAST(ac.first_item_quantity AS INTEGER)) as cart_value,
          MAX(ac.event_timestamp) as last_activity,
          MIN(ac.event_timestamp) as first_activity,
          (SELECT items_json FROM add_to_cart WHERE param_ga_session_id = ac.param_ga_session_id ${locationFilter} ${dateFilter} ORDER BY event_timestamp DESC LIMIT 1) as items_json,
          l.warehouse_name as location_name,
          l.city,
          l.state
        FROM add_to_cart ac
        LEFT JOIN locations l ON ac.user_prop_default_branch_id = l.warehouse_code
        WHERE ac.param_ga_session_id NOT IN (
          SELECT DISTINCT param_ga_session_id 
          FROM purchase 
          WHERE param_ga_session_id IS NOT NULL ${purchaseLocationFilter} ${dateFilter.replace(/ac\./g, '')}
        )
        ${locationFilter}
        ${dateFilter}
        GROUP BY ac.param_ga_session_id, ac.user_prop_webuserid, ac.user_prop_default_branch_id
      )
      SELECT * FROM abandoned_carts
      ORDER BY last_activity DESC
      LIMIT 50
    `
    
    const abandonedCarts = await db.all(query)
    
    const tasks: Task[] = []
    
    for (const [index, cart] of abandonedCarts.entries()) {
      const user = await correlateSessionToUser(cart.session_id, db, index)
      const cartValue = parseFloat(cart.cart_value) || 0
      
      // Parse items to get product details
      let productDetails: Array<{name: string, quantity: number, price: number}> = []
      
      try {
        const items = JSON.parse(cart.items_json || '[]')
        productDetails = items.map((item: any) => ({
          name: item.item_name || item.item_id || 'Unknown Product',
          quantity: parseInt(item.quantity) || 1,
          price: parseFloat(item.price) || 0
        }))
      } catch (e) {
        console.error('Error parsing items_json:', e)
      }
      
      // Skip carts with 0 value
      if (cartValue === 0) continue
      
      // Calculate hours since abandonment
      const hoursSinceAbandonment = Math.floor(
        (Date.now() - parseInt(cart.last_activity) / 1000) / (1000 * 60 * 60)
      )
      
      // Calculate session duration in minutes
      const sessionDuration = Math.floor(
        (parseInt(cart.last_activity) - parseInt(cart.first_activity)) / (1000 * 60 * 1000)
      )
      
      // Determine priority based on cart value and time
      let priority: Task['priority'] = 'medium'
      if (cartValue > 500 || (cartValue > 200 && hoursSinceAbandonment < 24)) {
        priority = 'high'
      } else if (cartValue < 50 || hoursSinceAbandonment > 72) {
        priority = 'low'
      }
      
      // Add location info to description if available
      const locationInfo = cart.location_name ? ` from ${cart.location_name} (${cart.city}, ${cart.state})` : ''
      
      tasks.push({
        id: `CART_${cart.session_id}`,
        type: 'cart',
        title: `Abandoned cart worth $${cartValue.toFixed(2)}`,
        description: user 
          ? `${user.name} left ${cart.unique_items} item${cart.unique_items > 1 ? 's' : ''} in cart${locationInfo}`
          : `Customer left ${cart.unique_items} item${cart.unique_items > 1 ? 's' : ''} in cart${locationInfo}`,
        priority,
        customer: {
          name: user?.name || 'Unknown Customer',
          email: user?.email || '',
          phone: user?.office_phone || user?.cell_phone || '',
          company: user?.customer_name || '',
          orderValue: cartValue
        },
        productDetails: productDetails.map(p => ({
          name: p.name,
          quantity: p.quantity,
          price: p.price
        })),
        metadata: {
          cartValue,
          visitCount: cart.unique_items,
          products: productDetails.map(p => p.name),
          location: cart.location_name ? `${cart.location_name} - ${cart.city}, ${cart.state}` : undefined,
          branchId: cart.branch_id
        },
        createdAt: new Date(parseInt(cart.last_activity) / 1000).toISOString(),
        userId: cart.web_user_id || undefined,
        sessionId: cart.session_id
      })
    }
    
    await db.close()
    
    return NextResponse.json({ tasks })
  } catch (error) {
    console.error('Error fetching cart abandonment tasks:', error)
    return NextResponse.json({ error: 'Failed to fetch tasks' }, { status: 500 })
  }
} 