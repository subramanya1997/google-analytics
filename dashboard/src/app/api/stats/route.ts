import { NextResponse } from 'next/server'
import { getDb } from '@/lib/db'

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const locationId = searchParams.get('locationId')
    
    const db = await getDb()
    
    // Build location filter
    const locationFilter = locationId ? `AND user_prop_default_branch_id = '${locationId}'` : ''
    
    // Get location-based statistics
    const locationStats = await db.all(`
      SELECT 
        l.warehouse_code as location_id,
        l.warehouse_name as location_name,
        l.city,
        l.state,
        (SELECT COUNT(*) FROM purchase p WHERE p.user_prop_default_branch_id = l.warehouse_code) as total_purchases,
        (SELECT COUNT(DISTINCT param_ga_session_id) FROM add_to_cart ac 
         WHERE ac.user_prop_default_branch_id = l.warehouse_code 
         AND param_ga_session_id NOT IN (
           SELECT DISTINCT param_ga_session_id FROM purchase p2 
           WHERE p2.user_prop_default_branch_id = l.warehouse_code
         )) as cart_abandonments,
        (SELECT COUNT(DISTINCT param_no_search_results_term) FROM no_search_results ns 
         WHERE ns.user_prop_default_branch_id = l.warehouse_code) as failed_searches,
        (SELECT COUNT(DISTINCT param_ga_session_id) FROM page_view pv 
         WHERE pv.user_prop_default_branch_id = l.warehouse_code) as total_visitors,
        (SELECT COALESCE(SUM(CAST(ecommerce_purchase_revenue AS REAL)), 0) FROM purchase p 
         WHERE p.user_prop_default_branch_id = l.warehouse_code 
         AND ecommerce_purchase_revenue IS NOT NULL) as total_revenue,
        (SELECT COUNT(DISTINCT pv.user_prop_webuserid) FROM page_view pv
         WHERE pv.user_prop_default_branch_id = l.warehouse_code
         AND pv.user_prop_webuserid IS NOT NULL
         AND pv.param_ga_session_id IN (
           SELECT param_ga_session_id FROM page_view pv2
           WHERE pv2.user_prop_default_branch_id = l.warehouse_code
           GROUP BY param_ga_session_id 
           HAVING COUNT(DISTINCT param_page_location) >= 3
         )) as repeat_visits
      FROM locations l
      WHERE EXISTS (
        SELECT 1 FROM page_view pv WHERE pv.user_prop_default_branch_id = l.warehouse_code
      )
      ${locationId ? `AND l.warehouse_code = '${locationId}'` : ''}
      ORDER BY total_revenue DESC
    `)
    
    // Get overall statistics (with optional location filter)
    const overallStats = await db.get(`
      SELECT 
        (SELECT COUNT(*) FROM purchase WHERE 1=1 ${locationFilter}) as total_purchases,
        (SELECT COUNT(DISTINCT param_ga_session_id) FROM add_to_cart 
         WHERE 1=1 ${locationFilter}
         AND param_ga_session_id NOT IN (
           SELECT DISTINCT param_ga_session_id FROM purchase WHERE 1=1 ${locationFilter}
         )) as cart_abandonments,
        (SELECT COUNT(DISTINCT param_no_search_results_term) FROM no_search_results WHERE 1=1 ${locationFilter}) as failed_searches,
        (SELECT COUNT(DISTINCT param_ga_session_id) FROM page_view WHERE 1=1 ${locationFilter}) as total_visitors,
        (SELECT SUM(CAST(ecommerce_purchase_revenue AS REAL)) FROM purchase 
         WHERE ecommerce_purchase_revenue IS NOT NULL ${locationFilter}) as total_revenue,
        (SELECT COUNT(DISTINCT pv.user_prop_webuserid) FROM page_view pv
         WHERE pv.user_prop_webuserid IS NOT NULL ${locationFilter}
         AND pv.param_ga_session_id IN (
           SELECT param_ga_session_id FROM page_view
           WHERE 1=1 ${locationFilter}
           GROUP BY param_ga_session_id 
           HAVING COUNT(DISTINCT param_page_location) >= 3
         )) as repeat_visits,
        (SELECT MAX(event_timestamp) FROM (
          SELECT MAX(event_timestamp) as event_timestamp FROM purchase WHERE 1=1 ${locationFilter}
          UNION ALL
          SELECT MAX(event_timestamp) as event_timestamp FROM add_to_cart WHERE 1=1 ${locationFilter}
          UNION ALL
          SELECT MAX(event_timestamp) as event_timestamp FROM page_view WHERE 1=1 ${locationFilter}
        )) as latest_event_timestamp
    `)
    
    // Get hourly activity for the single day (with location filter)
    const hourlyData = await db.all(`
      WITH hourly_events AS (
        SELECT 
          CAST(event_timestamp / 3600000000 AS INTEGER) as hour_bucket,
          event_name,
          COUNT(*) as event_count
        FROM (
          SELECT event_timestamp, 'purchase' as event_name FROM purchase WHERE 1=1 ${locationFilter}
          UNION ALL
          SELECT event_timestamp, 'add_to_cart' as event_name FROM add_to_cart WHERE 1=1 ${locationFilter}
          UNION ALL
          SELECT event_timestamp, 'search' as event_name FROM view_search_results WHERE 1=1 ${locationFilter}
          UNION ALL
          SELECT event_timestamp, 'search' as event_name FROM no_search_results WHERE 1=1 ${locationFilter}
        )
        GROUP BY hour_bucket, event_name
      )
      SELECT 
        hour_bucket,
        SUM(CASE WHEN event_name = 'purchase' THEN event_count ELSE 0 END) as purchases,
        SUM(CASE WHEN event_name = 'add_to_cart' THEN event_count ELSE 0 END) as carts,
        SUM(CASE WHEN event_name = 'search' THEN event_count ELSE 0 END) as searches
      FROM hourly_events
      GROUP BY hour_bucket
      ORDER BY hour_bucket
      LIMIT 24
    `)
    
    await db.close()
    
    // Format hour buckets to readable times
    const formatHour = (hourBucket: number) => {
      const hour = hourBucket % 24
      return hour === 0 ? '12 AM' : hour < 12 ? `${hour} AM` : hour === 12 ? '12 PM' : `${hour - 12} PM`
    }
    
    return NextResponse.json({
      metrics: {
        totalRevenue: `$${(overallStats.total_revenue || 0).toFixed(2)}`,
        purchases: overallStats.total_purchases || 0,
        abandonedCarts: overallStats.cart_abandonments || 0,
        failedSearches: overallStats.failed_searches || 0,
        totalVisitors: overallStats.total_visitors || 0,
        repeatVisits: overallStats.repeat_visits || 0
      },
      locationStats: locationStats.map(loc => ({
        locationId: loc.location_id,
        locationName: loc.location_name,
        city: loc.city,
        state: loc.state,
        totalRevenue: `$${(loc.total_revenue || 0).toFixed(2)}`,
        purchases: loc.total_purchases || 0,
        abandonedCarts: loc.cart_abandonments || 0,
        failedSearches: loc.failed_searches || 0,
        totalVisitors: loc.total_visitors || 0,
        repeatVisits: loc.repeat_visits || 0
      })),
      chartData: hourlyData.map(row => ({
        time: formatHour(row.hour_bucket),
        purchases: row.purchases || 0,
        carts: row.carts || 0,
        searches: row.searches || 0
      })),
      latestEventTimestamp: overallStats.latest_event_timestamp || null
    })
  } catch (error) {
    console.error('Error fetching stats:', error)
    return NextResponse.json({ error: 'Failed to fetch statistics' }, { status: 500 })
  }
} 