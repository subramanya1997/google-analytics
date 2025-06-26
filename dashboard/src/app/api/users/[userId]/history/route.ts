import { NextResponse } from 'next/server'
import { getDb } from '@/lib/db'

export async function GET(
  request: Request,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const db = await getDb()
    const { userId } = await params
    
    // Get user details
    const user = await db.get('SELECT * FROM users WHERE user_id = ?', userId)
    
    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 })
    }
    
    // Get purchase history
    const purchaseHistory = await db.all(`
      SELECT DISTINCT
        p.param_transaction_id as transaction_id,
        p.event_date,
        p.event_timestamp,
        p.ecommerce_purchase_revenue as order_value,
        p.items_json
      FROM purchase p
      WHERE p.user_prop_webuserid = ?
      ORDER BY p.event_timestamp DESC
      LIMIT 10
    `, [userId])
    
    // Parse items for each purchase
    const purchasesWithItems = purchaseHistory.map(purchase => {
      let items = []
      try {
        const parsedItems = JSON.parse(purchase.items_json || '[]')
        items = parsedItems.map((item: any) => ({
          name: item.item_name || item.item_id || 'Unknown Product',
          sku: item.item_id || '',
          quantity: parseInt(item.quantity) || 1,
          price: parseFloat(item.price) || 0
        }))
      } catch (e) {
        console.error('Error parsing items_json:', e)
      }
      
      return {
        ...purchase,
        items
      }
    })
    
    // Get search history
    // Join with page_view to get user_id since view_search_results doesn't have user_prop_webuserid
    const searchesWithResults = await db.all(`
      SELECT 
        vsr.event_date as date,
        vsr.param_search_term as term,
        'with_results' as type,
        COUNT(*) as count
      FROM view_search_results vsr
      WHERE vsr.param_ga_session_id IN (
        SELECT DISTINCT param_ga_session_id 
        FROM page_view 
        WHERE user_prop_webuserid = ?
      )
      GROUP BY vsr.event_date, vsr.param_search_term
      ORDER BY vsr.event_date DESC
      LIMIT 10
    `, userId)
    
    const searchesNoResults = await db.all(`
      SELECT 
        event_date as date,
        param_no_search_results_term as term,
        'no_results' as type,
        COUNT(*) as count
      FROM no_search_results
      WHERE user_prop_webuserid = ?
      GROUP BY event_date, param_no_search_results_term
      ORDER BY event_date DESC
      LIMIT 10
    `, userId)
    
    // Combine and sort the search results
    const searches = [...searchesWithResults, ...searchesNoResults]
      .sort((a, b) => b.date.localeCompare(a.date))
      .slice(0, 20)
    
    // Get cart activity with detailed items
    const cartHistory = await db.all(`
      SELECT DISTINCT
        ac.param_ga_session_id as session_id,
        ac.event_date,
        MAX(ac.event_timestamp) as event_timestamp,
        (SELECT items_json FROM add_to_cart WHERE param_ga_session_id = ac.param_ga_session_id ORDER BY event_timestamp DESC LIMIT 1) as items_json,
        SUM(CAST(ac.first_item_price AS REAL) * CAST(ac.first_item_quantity AS INTEGER)) as cart_value
      FROM add_to_cart ac
      WHERE ac.user_prop_webuserid = ?
        AND ac.param_ga_session_id NOT IN (
          SELECT DISTINCT param_ga_session_id 
          FROM purchase 
          WHERE param_ga_session_id IS NOT NULL
        )
      GROUP BY ac.param_ga_session_id, ac.event_date
      ORDER BY MAX(ac.event_timestamp) DESC
      LIMIT 10
    `, userId)
    
    // Parse items for each cart session
    const cartsWithItems = cartHistory.map(cart => {
      let items = []
      let totalValue = 0
      try {
        const parsedItems = JSON.parse(cart.items_json || '[]')
        items = parsedItems.map((item: any) => ({
          name: item.item_name || item.item_id || 'Unknown Product',
          sku: item.item_id || '',
          quantity: parseInt(item.quantity) || 1,
          price: parseFloat(item.price) || 0
        }))
        // Calculate total from items
        totalValue = items.reduce((sum: number, item: any) => sum + (item.quantity * item.price), 0)
      } catch (e) {
        console.error('Error parsing cart items_json:', e)
        totalValue = parseFloat(cart.cart_value) || 0
      }
      
      // Use calculated total or fallback to aggregated value
      if (totalValue === 0) {
        totalValue = parseFloat(cart.cart_value) || 0
      }
      
      return {
        session_id: cart.session_id,
        event_date: cart.event_date,
        event_timestamp: cart.event_timestamp,
        cart_value: totalValue,
        items
      }
    })
    
    // Get viewed products history - unique products with view counts
    const viewedProductsWithCounts = await db.all(`
      SELECT 
        vi.first_item_item_id as sku,
        vi.first_item_item_name as name,
        vi.first_item_item_category as category,
        MAX(vi.first_item_price) as price,
        COUNT(*) as view_count,
        MAX(vi.event_date) as last_viewed_date,
        MAX(vi.event_timestamp) as last_viewed_timestamp
      FROM view_item vi
      WHERE vi.user_prop_webuserid = ?
      GROUP BY vi.first_item_item_id
      ORDER BY view_count DESC, last_viewed_timestamp DESC
      LIMIT 50
    `, userId)
    
    // Format the viewed products
    const viewedProductsWithDetails = viewedProductsWithCounts.map(product => ({
      sku: product.sku || '',
      name: product.name || product.sku || 'Unknown Product',
      category: product.category || '',
      price: parseFloat(product.price) || 0,
      view_count: product.view_count,
      last_viewed_date: product.last_viewed_date,
      last_viewed_timestamp: product.last_viewed_timestamp
    }))
    
    await db.close()
    
    // Format the response
    return NextResponse.json({
      user: {
        id: user.user_id,
        name: user.name,
        email: user.email,
        phone: user.cell_phone || user.office_phone,
        company: user.customer_name,
        erpId: user.customer_erp_id,
        userType: user.user_type
      },
      purchaseHistory: purchasesWithItems,
      searchHistory: searches.map(s => ({
        date: s.date,
        term: s.term,
        type: s.type,
        results: s.type === 'with_results' ? s.count : 0
      })),
      cartHistory: cartsWithItems,
      viewedProductsHistory: viewedProductsWithDetails
    })
  } catch (error) {
    console.error('Error fetching user history:', error)
    return NextResponse.json({ error: 'Failed to fetch user history' }, { status: 500 })
  }
} 