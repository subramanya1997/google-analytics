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
    const locationFilter = locationId ? `AND p.user_prop_default_branch_id = '${locationId}'` : ''
    
    // Build date filter
    let dateFilter = ''
    if (startDate && endDate) {
      // Convert ISO dates to YYYYMMDD format used in database
      const start = startDate.replace(/-/g, '')
      const end = endDate.replace(/-/g, '')
      dateFilter = `AND p.event_date BETWEEN '${start}' AND '${end}'`
    }
    
    // Get recent purchases
    const query = `
      SELECT DISTINCT
        p.param_transaction_id as transaction_id,
        p.param_ga_session_id as session_id,
        p.user_prop_webuserid as web_user_id,
        p.user_prop_default_branch_id as branch_id,
        p.ecommerce_purchase_revenue as revenue,
        p.ecommerce_total_item_quantity as item_quantity,
        p.event_timestamp,
        p.items_json,
        l.warehouse_name as location_name,
        l.city,
        l.state
      FROM purchase p
      LEFT JOIN locations l ON p.user_prop_default_branch_id = l.warehouse_code
      WHERE p.param_transaction_id IS NOT NULL
      ${locationFilter}
      ${dateFilter}
      ORDER BY p.event_timestamp DESC
      LIMIT 50
    `
    
    const purchases = await db.all(query)
    
    const tasks: Task[] = []
    
    for (const [index, purchase] of purchases.entries()) {
      const user = await correlateSessionToUser(purchase.session_id, db, index)
      const revenue = parseFloat(purchase.revenue) || 0
      
      // Parse items to get product details
      let productDetails: Array<{name: string, quantity: number, price: number, sku?: string}> = []
      
      try {
        const items = JSON.parse(purchase.items_json || '[]')
        productDetails = items.map((item: any) => ({
          name: item.item_name || item.item_id || 'Unknown Product',
          quantity: parseInt(item.quantity) || 1,
          price: parseFloat(item.price) || 0,
          sku: item.item_id || undefined
        }))
      } catch (e) {
        console.error('Error parsing items_json:', e)
      }
      
      // Format purchase date
      const purchaseDate = new Date(parseInt(purchase.event_timestamp) / 1000)
      const daysSincePurchase = Math.floor(
        (Date.now() - purchaseDate.getTime()) / (1000 * 60 * 60 * 24)
      )
      
      // Add location info to description if available
      const locationInfo = purchase.location_name ? ` from ${purchase.location_name} (${purchase.city}, ${purchase.state})` : ''
      
      tasks.push({
        id: `purchase-${purchase.transaction_id}-${index}`,
        type: 'purchase' as const,
        priority: revenue > 1000 ? 'high' : revenue > 500 ? 'medium' : 'low',
        title: revenue > 1000 ? 'High-value purchase follow-up' : 'Post-purchase engagement',
        description: revenue > 1000 
          ? `Thank customer for their $${revenue.toFixed(2)} purchase${locationInfo} - ${daysSincePurchase} days ago`
          : `Follow up on recent purchase of ${productDetails.length} item${productDetails.length !== 1 ? 's' : ''}${locationInfo}`,
        customer: {
          name: user?.name || 'Unknown Customer',
          email: user?.email || '',
          phone: user?.cell_phone || user?.office_phone || '',
          company: user?.customer_name || '',
          orderValue: revenue,
          lastOrder: purchaseDate.toLocaleDateString()
        },
        productDetails,
        metadata: {
          transactionId: purchase.transaction_id,
          purchaseDate: purchaseDate.toISOString(),
          daysSincePurchase,
          location: purchase.location_name ? `${purchase.location_name} - ${purchase.city}, ${purchase.state}` : undefined,
          branchId: purchase.branch_id
        },
        createdAt: new Date().toISOString(),
        status: 'pending' as const
      })
    }
    
    await db.close()
    
    return NextResponse.json({ 
      tasks,
      total: tasks.length 
    })
  } catch (error) {
    console.error('Error fetching purchase tasks:', error)
    return NextResponse.json({ error: 'Failed to fetch purchase tasks' }, { status: 500 })
  }
} 