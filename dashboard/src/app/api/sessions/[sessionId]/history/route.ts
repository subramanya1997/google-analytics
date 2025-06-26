import { NextResponse } from 'next/server'
import { getDb } from '@/lib/db'
import { correlateSessionToUser } from '@/lib/user-matching'

export async function GET(
  request: Request,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const db = await getDb()
    const { sessionId } = await params
    
    // Try to find the user associated with this session
    const user = await correlateSessionToUser(sessionId, db)
    
    // Get page views for this session
    const pageViews = await db.all(`
      SELECT 
        param_page_title as title,
        param_page_location as url,
        event_timestamp,
        event_date
      FROM page_view
      WHERE param_ga_session_id = ?
      ORDER BY event_timestamp ASC
    `, sessionId)
    
    // Get purchases for this session
    const purchases = await db.all(`
      SELECT 
        param_transaction_id as transaction_id,
        event_date,
        event_timestamp,
        ecommerce_purchase_revenue as order_value,
        items_json
      FROM purchase
      WHERE param_ga_session_id = ?
    `, sessionId)
    
    // Get cart activity for this session
    const cartActivity = await db.all(`
      SELECT 
        event_timestamp,
        event_date,
        first_item_item_name as item_name,
        first_item_price as item_price,
        first_item_quantity as item_quantity,
        items_json
      FROM add_to_cart
      WHERE param_ga_session_id = ?
      ORDER BY event_timestamp ASC
    `, sessionId)
    
    // Get searches for this session
    const searches = await db.all(`
      SELECT 
        event_date,
        event_timestamp,
        param_search_term as term,
        'with_results' as type
      FROM view_search_results
      WHERE param_ga_session_id = ?
      UNION ALL
      SELECT 
        event_date,
        event_timestamp,
        param_no_search_results_term as term,
        'no_results' as type
      FROM no_search_results  
      WHERE param_ga_session_id = ?
      ORDER BY event_timestamp ASC
    `, sessionId, sessionId)
    
    await db.close()
    
    // Format the response
    return NextResponse.json({
      sessionId,
      user: user ? {
        id: user.user_id,
        name: user.name,
        email: user.email,
        phone: user.cell_phone || user.office_phone,
        company: user.customer_name
      } : null,
      pageViews: pageViews.map(pv => ({
        title: pv.title,
        url: pv.url,
        timestamp: pv.event_timestamp,
        date: pv.event_date
      })),
      purchases: purchases.map(p => {
        let items = []
        try {
          items = JSON.parse(p.items_json || '[]')
        } catch (e) {
          console.error('Error parsing purchase items:', e)
        }
        return {
          transactionId: p.transaction_id,
          date: p.event_date,
          timestamp: p.event_timestamp,
          orderValue: p.order_value,
          items
        }
      }),
      cartActivity: cartActivity.map(ca => {
        let items = []
        try {
          items = JSON.parse(ca.items_json || '[]')
        } catch (e) {
          // Fallback to single item info
          if (ca.item_name) {
            items = [{
              item_name: ca.item_name,
              price: ca.item_price,
              quantity: ca.item_quantity
            }]
          }
        }
        return {
          timestamp: ca.event_timestamp,
          date: ca.event_date,
          items
        }
      }),
      searches: searches.map(s => ({
        date: s.date,
        timestamp: s.event_timestamp,
        term: s.term,
        type: s.type
      }))
    })
  } catch (error) {
    console.error('Error fetching session history:', error)
    return NextResponse.json({ error: 'Failed to fetch session history' }, { status: 500 })
  }
} 