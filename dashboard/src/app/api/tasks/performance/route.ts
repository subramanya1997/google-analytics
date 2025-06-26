import { NextResponse } from 'next/server'
import { getDb } from '@/lib/db'
import { Task } from '@/types/tasks'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const page = parseInt(searchParams.get('page') || '1')
  const limit = parseInt(searchParams.get('limit') || '50') 
  const query = searchParams.get('q') || ''
  const locationId = searchParams.get('locationId')
  const offset = (page - 1) * limit

  const db = await getDb()
  
  try {
    // Build search filter
    const searchFilter = query ? `
      AND (
        u.name LIKE '%' || ? || '%' OR
        u.email LIKE '%' || ? || '%' OR
        u.customer_name LIKE '%' || ? || '%' OR
        pv.param_page_title LIKE '%' || ? || '%' OR
        pv.param_page_location LIKE '%' || ? || '%'
      )
    ` : ""
    
    // Build location filter - we'll apply it with proper table alias in each context
    const locationFilter = locationId ? true : false
    
    const searchParams = query ? Array(5).fill(query) : []
    const allParams = locationId ? [...searchParams, locationId] : searchParams

    // Get total count of bounce sessions
    const countQuery = `
      SELECT 
        (SELECT COUNT(*) FROM (
          SELECT COUNT(DISTINCT pv.param_ga_session_id) as total
          FROM page_view pv
          JOIN users u ON CAST(pv.user_prop_webuserid AS INTEGER) = u.user_id
          WHERE pv.user_prop_webuserid IS NOT NULL
          ${searchFilter}
          ${locationFilter ? 'AND pv.user_prop_default_branch_id = ?' : ''}
          GROUP BY pv.param_ga_session_id
          HAVING COUNT(*) = 1
        )) +
        (SELECT COUNT(*) FROM (
          SELECT param_page_location, COUNT(DISTINCT param_ga_session_id) as bounce_count
          FROM page_view
          WHERE param_ga_session_id IN (
            SELECT param_ga_session_id 
            FROM page_view 
            WHERE 1=1 ${locationFilter ? 'AND user_prop_default_branch_id = ?' : ''}
            GROUP BY param_ga_session_id 
            HAVING COUNT(*) = 1
          )
          ${locationFilter ? 'AND user_prop_default_branch_id = ?' : ''}
          GROUP BY param_page_location
          HAVING bounce_count > 2
        )) as total
    `

    const countResult = await db.get(countQuery, ...allParams, ...(locationId ? [locationId, locationId, locationId] : [])) as { total: number }
    const totalCount = countResult?.total || 0

    // Main query to get performance tasks
    const tasksQuery = `
      WITH bounce_sessions AS (
        SELECT 
          pv.param_ga_session_id,
          pv.param_page_title,
          pv.param_page_location,
          pv.user_prop_default_branch_id as branch_id,
          u.user_id,
          u.name,
          u.email,
          u.office_phone,
          u.customer_name,
          MAX(pv.event_timestamp) as last_seen,
          COUNT(*) as page_views,
          l.warehouse_name as location_name,
          l.city,
          l.state
        FROM page_view pv
        JOIN users u ON CAST(pv.user_prop_webuserid AS INTEGER) = u.user_id
        LEFT JOIN locations l ON pv.user_prop_default_branch_id = l.warehouse_code
        WHERE pv.user_prop_webuserid IS NOT NULL
        ${searchFilter}
        ${locationFilter ? 'AND pv.user_prop_default_branch_id = ?' : ''}
        GROUP BY pv.param_ga_session_id, pv.user_prop_default_branch_id, u.user_id, u.name, u.email, u.office_phone, u.customer_name, l.warehouse_name, l.city, l.state, pv.param_page_title, pv.param_page_location
        HAVING COUNT(*) = 1
      ),
      frequently_bounced_pages AS (
        SELECT 
          pv.param_page_location,
          pv.param_page_title,
          COUNT(DISTINCT pv.param_ga_session_id) as bounce_count,
          MAX(pv.event_timestamp) as last_bounce,
          ${locationId ? `
            l.warehouse_name as location_name,
            l.city,
            l.state
          ` : `
            NULL as location_name,
            NULL as city,
            NULL as state
          `}
        FROM page_view pv
        ${locationId ? 'LEFT JOIN locations l ON pv.user_prop_default_branch_id = l.warehouse_code' : ''}
        WHERE pv.param_ga_session_id IN (
          SELECT param_ga_session_id 
          FROM page_view 
          WHERE 1=1 ${locationFilter ? 'AND user_prop_default_branch_id = ?' : ''}
          GROUP BY param_ga_session_id 
          HAVING COUNT(*) = 1
        )
        ${locationFilter ? 'AND pv.user_prop_default_branch_id = ?' : ''}
        GROUP BY pv.param_page_location, pv.param_page_title${locationId ? ', l.warehouse_name, l.city, l.state' : ''}
        HAVING bounce_count > 2
      )
      
      SELECT * FROM (
        -- Individual bounce sessions
        SELECT 
          'PERF_BOUNCE_' || param_ga_session_id || '_' || CAST(user_id AS TEXT) || '_' || CAST(last_seen AS TEXT) as id,
          'performance' as type,
          'High bounce rate: ' || param_page_title as title,
          'User left after viewing only this page' || 
            CASE WHEN location_name IS NOT NULL THEN ' at ' || location_name ELSE '' END as description,
          'medium' as priority,
          user_id,
          name as customer_name,
          email as email_address,
          office_phone as phone_number,
          customer_name as company,
          param_ga_session_id,
          json_object(
            'issueType', 'high_bounce',
            'pageTitle', param_page_title,
            'pageUrl', param_page_location,
            'lastSeen', last_seen,
            'location', CASE 
              WHEN location_name IS NOT NULL 
              THEN location_name || ' - ' || city || ', ' || state
              ELSE NULL
            END,
            'branchId', branch_id
          ) as metadata
        FROM bounce_sessions
        
        UNION ALL
        
        -- Pages with frequent bounces (aggregate view)
        SELECT DISTINCT
          'PERF_PAGE_' || REPLACE(REPLACE(fbp.param_page_location, '/', '_'), '.', '_') || '_' || CAST(fbp.bounce_count AS TEXT) || '_' || CAST(fbp.last_bounce AS TEXT) ${locationId ? " || '_' || '" + locationId + "'" : ""} as id,
          'performance' as type,
          'Page issue: ' || fbp.param_page_title as title,
          fbp.bounce_count || ' users bounced from this page' ||
            CASE WHEN fbp.location_name IS NOT NULL THEN ' at ' || fbp.location_name ELSE '' END as description,
          CASE 
            WHEN fbp.bounce_count > 10 THEN 'high'
            WHEN fbp.bounce_count > 5 THEN 'medium'
            ELSE 'low'
          END as priority,
          NULL as user_id,
          'System Alert' as customer_name,
          '' as email_address,
          '' as phone_number,
          'Internal' as company,
          '' as param_ga_session_id,
          json_object(
            'issueType', 'page_bounce_issue',
            'pageTitle', fbp.param_page_title,
            'pageUrl', fbp.param_page_location,
            'bounceCount', fbp.bounce_count,
            'lastBounce', fbp.last_bounce,
            'location', CASE 
              WHEN fbp.location_name IS NOT NULL 
              THEN fbp.location_name || ' - ' || fbp.city || ', ' || fbp.state
              ELSE NULL
            END
          ) as metadata
        FROM frequently_bounced_pages fbp
        ${query ? 'WHERE EXISTS (SELECT 1 FROM bounce_sessions bs)' : ''}
      )
      ORDER BY 
        CASE priority 
          WHEN 'high' THEN 1 
          WHEN 'medium' THEN 2 
          WHEN 'low' THEN 3 
        END,
        id DESC
      LIMIT ? OFFSET ?
    `

    const queryParams = [...allParams, ...(locationId ? [locationId, locationId, locationId] : []), limit, offset]
      
    const performanceTasks = await db.all(tasksQuery, ...queryParams) as any[]
    
    // Transform tasks to proper format
    const tasks: Task[] = performanceTasks.map(row => {
      const metadata = JSON.parse(row.metadata)
      
      // Convert timestamps from microseconds to ISO date strings
      if (metadata.lastSeen) {
        const timestampMs = Math.floor(parseInt(metadata.lastSeen) / 1000)
        metadata.lastSeen = new Date(timestampMs).toISOString()
      }
      
      if (metadata.lastBounce) {
        const timestampMs = Math.floor(parseInt(metadata.lastBounce) / 1000)
        metadata.lastBounce = new Date(timestampMs).toISOString()
      }
      
      return {
        id: row.id,
        type: row.type,
        title: row.title,
        description: row.description,
        priority: row.priority,
        customer: {
          name: row.customer_name || 'Unknown',
          email: row.email_address || '',
          phone: row.phone_number || '',
          company: row.company || ''
        },
        metadata,
        createdAt: new Date().toISOString(),
        userId: row.user_id || undefined,
        sessionId: row.param_ga_session_id || undefined
      }
    })
    
    return NextResponse.json({ 
      tasks,
      total: totalCount,
      page,
      limit,
      totalPages: Math.ceil(totalCount / limit)
    })
  } catch (error) {
    console.error('Error fetching performance tasks:', error)
    return NextResponse.json({ error: 'Failed to fetch performance tasks' }, { status: 500 })
  } finally {
    await db.close()
  }
} 