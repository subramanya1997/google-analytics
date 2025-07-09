import { NextResponse } from 'next/server'
import { getDb } from '@/lib/db'

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const locationId = searchParams.get('locationId')
    const startDate = searchParams.get('startDate')
    const endDate = searchParams.get('endDate')
    const granularity = searchParams.get('granularity') || 'daily'
    const timezoneOffset = parseInt(searchParams.get('timezoneOffset') || '0') // in minutes
    
    const db = await getDb()
    
    // Build location filter
    const locationFilter = locationId ? `AND user_prop_default_branch_id = '${locationId}'` : ''
    
    // Build date filter
    let dateFilter = ''
    if (startDate && endDate) {
      // Convert ISO dates to YYYYMMDD format used in database
      const start = startDate.replace(/-/g, '')
      const end = endDate.replace(/-/g, '')
      dateFilter = `AND event_date BETWEEN '${start}' AND '${end}'`
    }
    
    // Get location-based statistics
    const locationStats = await db.all(`
      SELECT DISTINCT
        l.warehouse_code as location_id,
        l.warehouse_name as location_name,
        l.city,
        l.state,
        (SELECT COUNT(*) FROM purchase p WHERE p.user_prop_default_branch_id = l.warehouse_code ${dateFilter}) as total_purchases,
        (SELECT COUNT(DISTINCT param_ga_session_id) FROM add_to_cart ac 
         WHERE ac.user_prop_default_branch_id = l.warehouse_code ${dateFilter}
         AND param_ga_session_id NOT IN (
           SELECT DISTINCT param_ga_session_id FROM purchase p2 
           WHERE p2.user_prop_default_branch_id = l.warehouse_code ${dateFilter}
         )) as cart_abandonments,
        (SELECT COUNT(DISTINCT param_no_search_results_term) FROM no_search_results ns 
         WHERE ns.user_prop_default_branch_id = l.warehouse_code ${dateFilter}) as failed_searches,
        (SELECT COUNT(DISTINCT param_ga_session_id) FROM page_view pv 
         WHERE pv.user_prop_default_branch_id = l.warehouse_code ${dateFilter}) as total_visitors,
        (SELECT COALESCE(SUM(CAST(ecommerce_purchase_revenue AS REAL)), 0) FROM purchase p 
         WHERE p.user_prop_default_branch_id = l.warehouse_code 
         AND ecommerce_purchase_revenue IS NOT NULL ${dateFilter}) as total_revenue,
        (SELECT COUNT(DISTINCT pv.user_prop_webuserid) FROM page_view pv
         WHERE pv.user_prop_default_branch_id = l.warehouse_code
         AND pv.user_prop_webuserid IS NOT NULL ${dateFilter}
         AND pv.param_ga_session_id IN (
           SELECT param_ga_session_id FROM page_view pv2
           WHERE pv2.user_prop_default_branch_id = l.warehouse_code ${dateFilter}
           GROUP BY param_ga_session_id 
           HAVING COUNT(DISTINCT param_page_location) >= 3
         )) as repeat_visits
      FROM locations l
      WHERE EXISTS (
        SELECT 1 FROM page_view pv WHERE pv.user_prop_default_branch_id = l.warehouse_code ${dateFilter}
      )
      
      ORDER BY total_revenue DESC
    `)
    
    // Get overall statistics (with optional location filter)
    const overallStats = await db.get(`
      SELECT 
        (SELECT COUNT(*) FROM purchase WHERE 1=1 ${locationFilter} ${dateFilter}) as total_purchases,
        (SELECT COUNT(DISTINCT param_ga_session_id) FROM add_to_cart 
         WHERE 1=1 ${locationFilter} ${dateFilter}
         AND param_ga_session_id NOT IN (
           SELECT DISTINCT param_ga_session_id FROM purchase WHERE 1=1 ${locationFilter} ${dateFilter}
         )) as cart_abandonments,
        (SELECT COUNT(DISTINCT param_no_search_results_term) FROM no_search_results WHERE 1=1 ${locationFilter} ${dateFilter}) as failed_searches,
        (SELECT COUNT(DISTINCT param_ga_session_id) FROM page_view WHERE 1=1 ${locationFilter} ${dateFilter}) as total_visitors,
        (SELECT SUM(CAST(ecommerce_purchase_revenue AS REAL)) FROM purchase 
         WHERE ecommerce_purchase_revenue IS NOT NULL ${locationFilter} ${dateFilter}) as total_revenue,
        (SELECT COUNT(DISTINCT pv.user_prop_webuserid) FROM page_view pv
         WHERE pv.user_prop_webuserid IS NOT NULL ${locationFilter} ${dateFilter}
         AND pv.param_ga_session_id IN (
           SELECT param_ga_session_id FROM page_view
           WHERE 1=1 ${locationFilter} ${dateFilter}
           GROUP BY param_ga_session_id 
           HAVING COUNT(DISTINCT param_page_location) >= 3
         )) as repeat_visits,
        (SELECT MAX(event_timestamp) FROM (
          SELECT MAX(event_timestamp) as event_timestamp FROM purchase WHERE 1=1 ${locationFilter} ${dateFilter}
          UNION ALL
          SELECT MAX(event_timestamp) as event_timestamp FROM add_to_cart WHERE 1=1 ${locationFilter} ${dateFilter}
          UNION ALL
          SELECT MAX(event_timestamp) as event_timestamp FROM page_view WHERE 1=1 ${locationFilter} ${dateFilter}
        )) as latest_event_timestamp
    `)
    
    // Get activity data based on granularity
    let chartData: any[] = []
    
    // Calculate timezone offset in seconds
    const tzOffsetSeconds = timezoneOffset * 60
    
    if (granularity === 'hourly') {
      // For hourly data, we need to extract hour from timestamp with timezone adjustment
      chartData = await db.all(`
        WITH hourly_events AS (
          SELECT 
            event_date,
            CAST((event_timestamp / 1000000 + ${tzOffsetSeconds}) / 3600 AS INTEGER) % 24 as hour,
            event_name,
            COUNT(*) as event_count
          FROM (
            SELECT event_date, event_timestamp, 'purchase' as event_name FROM purchase WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, event_timestamp, 'add_to_cart' as event_name FROM add_to_cart WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, event_timestamp, 'search' as event_name FROM view_search_results WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, event_timestamp, 'search' as event_name FROM no_search_results WHERE 1=1 ${locationFilter} ${dateFilter}
          )
          GROUP BY event_date, hour, event_name
        )
        SELECT 
          event_date || ' ' || printf('%02d', hour) || ':00' as time_label,
          SUM(CASE WHEN event_name = 'purchase' THEN event_count ELSE 0 END) as purchases,
          SUM(CASE WHEN event_name = 'add_to_cart' THEN event_count ELSE 0 END) as carts,
          SUM(CASE WHEN event_name = 'search' THEN event_count ELSE 0 END) as searches
        FROM hourly_events
        GROUP BY event_date, hour
        ORDER BY event_date, hour
      `)
    } else if (granularity === '4hours') {
      // 4-hour intervals with timezone adjustment
      chartData = await db.all(`
        WITH interval_events AS (
          SELECT 
            event_date,
            CAST(CAST((event_timestamp / 1000000 + ${tzOffsetSeconds}) / 3600 AS INTEGER) / 4 AS INTEGER) * 4 as hour_group,
            event_name,
            COUNT(*) as event_count
          FROM (
            SELECT event_date, event_timestamp, 'purchase' as event_name FROM purchase WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, event_timestamp, 'add_to_cart' as event_name FROM add_to_cart WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, event_timestamp, 'search' as event_name FROM view_search_results WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, event_timestamp, 'search' as event_name FROM no_search_results WHERE 1=1 ${locationFilter} ${dateFilter}
          )
          GROUP BY event_date, hour_group, event_name
        )
        SELECT 
          event_date || ' ' || printf('%02d', hour_group % 24) || ':00' as time_label,
          SUM(CASE WHEN event_name = 'purchase' THEN event_count ELSE 0 END) as purchases,
          SUM(CASE WHEN event_name = 'add_to_cart' THEN event_count ELSE 0 END) as carts,
          SUM(CASE WHEN event_name = 'search' THEN event_count ELSE 0 END) as searches
        FROM interval_events
        GROUP BY event_date, hour_group
        ORDER BY event_date, hour_group
      `)
    } else if (granularity === '12hours') {
      // 12-hour intervals (AM/PM) with timezone adjustment
      chartData = await db.all(`
        WITH interval_events AS (
          SELECT 
            event_date,
            CASE 
              WHEN CAST((event_timestamp / 1000000 + ${tzOffsetSeconds}) / 3600 AS INTEGER) % 24 < 12 THEN 0
              ELSE 12
            END as hour_start,
            event_name,
            COUNT(*) as event_count
          FROM (
            SELECT event_date, event_timestamp, 'purchase' as event_name FROM purchase WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, event_timestamp, 'add_to_cart' as event_name FROM add_to_cart WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, event_timestamp, 'search' as event_name FROM view_search_results WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, event_timestamp, 'search' as event_name FROM no_search_results WHERE 1=1 ${locationFilter} ${dateFilter}
          )
          GROUP BY event_date, hour_start, event_name
        )
        SELECT 
          event_date || ' ' || printf('%02d', hour_start) || ':00' as time_label,
          SUM(CASE WHEN event_name = 'purchase' THEN event_count ELSE 0 END) as purchases,
          SUM(CASE WHEN event_name = 'add_to_cart' THEN event_count ELSE 0 END) as carts,
          SUM(CASE WHEN event_name = 'search' THEN event_count ELSE 0 END) as searches
        FROM interval_events
        GROUP BY event_date, hour_start
        ORDER BY event_date, hour_start
      `)
    } else {
      // Default to daily
      chartData = await db.all(`
        WITH daily_events AS (
          SELECT 
            event_date,
            event_name,
            COUNT(*) as event_count
          FROM (
            SELECT event_date, 'purchase' as event_name FROM purchase WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, 'add_to_cart' as event_name FROM add_to_cart WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, 'search' as event_name FROM view_search_results WHERE 1=1 ${locationFilter} ${dateFilter}
            UNION ALL
            SELECT event_date, 'search' as event_name FROM no_search_results WHERE 1=1 ${locationFilter} ${dateFilter}
          )
          GROUP BY event_date, event_name
        )
        SELECT 
          event_date,
          SUM(CASE WHEN event_name = 'purchase' THEN event_count ELSE 0 END) as purchases,
          SUM(CASE WHEN event_name = 'add_to_cart' THEN event_count ELSE 0 END) as carts,
          SUM(CASE WHEN event_name = 'search' THEN event_count ELSE 0 END) as searches
        FROM daily_events
        GROUP BY event_date
        ORDER BY event_date
      `)
    }
    
    await db.close()
    
    // Format dates for chart
    const formatDate = (dateStr: string) => {
      if (granularity !== 'daily' && dateStr.includes(' ')) {
        // For hourly/interval data, format differently
        const [date, time] = dateStr.split(' ')
        const year = date.substring(0, 4)
        const month = date.substring(4, 6)
        const day = date.substring(6, 8)
        const formattedDate = new Date(`${year}-${month}-${day}`).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        return `${formattedDate} ${time}`
      }
      
      // For daily data
      const year = dateStr.substring(0, 4)
      const month = dateStr.substring(4, 6)
      const day = dateStr.substring(6, 8)
      const date = new Date(`${year}-${month}-${day}`)
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
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
      chartData: chartData.map(row => ({
        time: granularity === 'daily' ? formatDate(row.event_date) : formatDate(row.time_label),
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