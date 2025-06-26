import { NextResponse } from 'next/server'
import { getDb } from '@/lib/db'
import { correlateSessionToUser } from '@/lib/user-matching'
import { Task } from '@/types/tasks'

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const locationId = searchParams.get('locationId')
    
    const db = await getDb()
    
    // Build location filter
    const locationFilter = locationId ? `AND ac.user_prop_default_branch_id = '${locationId}'` : ''
    const purchaseLocationFilter = locationId ? `AND user_prop_default_branch_id = '${locationId}'` : ''
    
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
          (SELECT items_json FROM add_to_cart WHERE param_ga_session_id = ac.param_ga_session_id ${locationFilter} ORDER BY event_timestamp DESC LIMIT 1) as items_json,
          l.warehouse_name as location_name,
          l.city,
          l.state
        FROM add_to_cart ac
        LEFT JOIN locations l ON ac.user_prop_default_branch_id = l.warehouse_code
        WHERE ac.param_ga_session_id NOT IN (
          SELECT DISTINCT param_ga_session_id 
          FROM purchase 
          WHERE param_ga_session_id IS NOT NULL ${purchaseLocationFilter}
        )
        ${locationFilter}
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
      const totalCartValue = parseFloat(cart.cart_value) || 0
      
      // Parse items_json to get product details
      let productDetails: Array<{name: string, quantity: number, price: number, sku?: string}> = []
      let totalValue = 0
      
      try {
        const items = JSON.parse(cart.items_json || '[]')
        productDetails = items.map((item: any) => ({
          name: item.item_name || item.item_id || 'Unknown Product',
          quantity: parseInt(item.quantity) || 1,
          price: parseFloat(item.price) || 0,
          sku: item.item_id || undefined
        }))
        
        // Calculate total cart value
        totalValue = productDetails.reduce((sum, item) => sum + (item.quantity * item.price), 0)
      } catch (e) {
        console.error('Error parsing items_json:', e)
        totalValue = totalCartValue
      }
      
      // If we couldn't calculate from items, use the calculated cart value
      if (totalValue === 0) {
        totalValue = totalCartValue
      }
      
      // Get cart products for backward compatibility
      const cartProducts = productDetails.map(p => p.name)
      
      // Calculate days since abandonment
      const daysSinceAbandonment = Math.floor(
        (Date.now() - parseInt(cart.last_activity) / 1000) / (1000 * 60 * 60 * 24)
      )
      
      // Determine priority and title based on cart value
      let priority: 'high' | 'medium' | 'low' = 'medium'
      let title = 'Abandoned cart recovery'
      let description = ''
      
      // Add location info to description if available
      const locationInfo = cart.location_name ? ` at ${cart.location_name} (${cart.city}, ${cart.state})` : ''
      
      if (totalValue > 500) {
        priority = 'high'
        title = 'High-value cart recovery opportunity'
        description = `High-value cart with ${productDetails.length} item${productDetails.length !== 1 ? 's' : ''} totaling $${totalValue.toFixed(2)} - abandoned ${daysSinceAbandonment} ${daysSinceAbandonment === 1 ? 'day' : 'days'} ago${locationInfo}`
      } else if (totalValue > 100) {
        priority = 'medium'
        title = 'Medium-value cart recovery'
        description = `${productDetails.length} item${productDetails.length !== 1 ? 's' : ''} worth $${totalValue.toFixed(2)} abandoned ${daysSinceAbandonment} ${daysSinceAbandonment === 1 ? 'day' : 'days'} ago${locationInfo}`
      } else {
        priority = 'low'
        description = `${productDetails.length} item${productDetails.length !== 1 ? 's' : ''} worth $${totalValue.toFixed(2)}${locationInfo}`
      }
      
      tasks.push({
        id: `cart-${cart.session_id}-${index}`,
        type: 'cart' as const,
        priority,
        title,
        description,
        customer: {
          name: user?.name || 'Unknown Customer',
          email: user?.email || '',
          phone: user?.cell_phone || user?.office_phone || '',
          company: user?.customer_name || '',
          orderValue: totalValue
        },
        productDetails,
        metadata: {
          products: cartProducts.length > 0 ? cartProducts : ['Multiple items'],
          cartValue: totalValue,
          visitCount: cart.abandonments || 1,
          location: cart.location_name ? `${cart.location_name} - ${cart.city}, ${cart.state}` : undefined,
          branchId: cart.branch_id
        },
        createdAt: new Date().toISOString(),
        status: 'pending' as const,
        userId: user?.user_id,
        sessionId: cart.session_id
      } as Task & { userId?: number | string; sessionId?: string })
    }
    
    await db.close()
    
    return NextResponse.json({ 
      tasks,
      total: tasks.length 
    })
  } catch (error) {
    console.error('Error fetching cart abandonment tasks:', error)
    return NextResponse.json({ error: 'Failed to fetch cart abandonment tasks' }, { status: 500 })
  }
} 