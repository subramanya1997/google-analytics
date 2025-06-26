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
        u.customer_name LIKE '%' || ? || '%'
      )
    ` : ""
    
    // Build location filter
    const locationFilter = locationId ? `AND pv.user_prop_default_branch_id = ?` : ""
    
    const searchParams = query ? [query, query, query] : []
    const allParams = locationId ? [...searchParams, locationId] : searchParams

    // Get total count
    const countQuery = `
      SELECT COUNT(DISTINCT pv.param_ga_session_id) as total
      FROM page_view pv
      JOIN users u ON CAST(pv.user_prop_webuserid AS INTEGER) = u.user_id
      WHERE pv.user_prop_webuserid IS NOT NULL
      ${searchFilter}
      ${locationFilter}
      AND EXISTS (
        SELECT 1 FROM page_view pv2
        WHERE pv2.param_ga_session_id = pv.param_ga_session_id
        ${locationId ? 'AND pv2.user_prop_default_branch_id = pv.user_prop_default_branch_id' : ''}
        GROUP BY pv2.param_ga_session_id
        HAVING COUNT(DISTINCT pv2.param_page_location) >= 3
      )
    `

    const countResult = await db.get(countQuery, ...allParams) as { total: number }
    const totalCount = countResult.total || 0

    // Main query
    const tasksQuery = `
      WITH repeat_visitors AS (
        SELECT 
          pv.param_ga_session_id,
          pv.user_prop_default_branch_id as branch_id,
          u.user_id,
          u.name,
          u.email,
          u.office_phone,
          u.customer_name,
          COUNT(DISTINCT pv.param_page_location) as unique_pages_viewed,
          MAX(pv.event_timestamp) as last_visit,
          GROUP_CONCAT(DISTINCT 
            CASE 
              WHEN pv.param_page_title LIKE '%Product%' OR pv.param_page_location LIKE '%/product%' 
              THEN pv.param_page_title || '::URL::' || pv.param_page_location
              ELSE NULL 
            END
          ) as viewed_products,
          l.warehouse_name as location_name,
          l.city,
          l.state
        FROM page_view pv
        JOIN users u ON CAST(pv.user_prop_webuserid AS INTEGER) = u.user_id
        LEFT JOIN locations l ON pv.user_prop_default_branch_id = l.warehouse_code
        WHERE pv.user_prop_webuserid IS NOT NULL
        ${searchFilter}
        ${locationFilter}
        GROUP BY pv.param_ga_session_id, pv.user_prop_default_branch_id, u.user_id
        HAVING unique_pages_viewed >= 3
      )
      SELECT 
        'REPEAT_' || param_ga_session_id || '_' || user_id as id,
        'repeat_visit' as type,
        'Repeat visitor showing interest' as title,
        'Visited ' || unique_pages_viewed || ' pages without purchasing' || 
          CASE WHEN location_name IS NOT NULL THEN ' at ' || location_name ELSE '' END as description,
        CASE 
          WHEN unique_pages_viewed > 5 THEN 'high'
          WHEN unique_pages_viewed > 3 THEN 'medium'
          ELSE 'low'
        END as priority,
        user_id,
        name as customer_name,
        email as email_address,
        office_phone as phone_number,
        customer_name as company,
        param_ga_session_id,
        json_object(
          'visitCount', unique_pages_viewed,
          'lastVisit', last_visit,
          'products', CASE 
            WHEN viewed_products IS NOT NULL 
            THEN json_array(viewed_products)
            ELSE json_array()
          END,
          'location', CASE 
            WHEN location_name IS NOT NULL 
            THEN location_name || ' - ' || city || ', ' || state
            ELSE NULL
          END,
          'branchId', branch_id
        ) as metadata
      FROM repeat_visitors
      ORDER BY unique_pages_viewed DESC, last_visit DESC
      LIMIT ? OFFSET ?
    `

    const repeatVisitTasks = await db.all(tasksQuery, ...allParams, limit, offset) as any[]

    // Transform the results into Task objects
    const tasks: Task[] = repeatVisitTasks.map(row => {
      let metadata = JSON.parse(row.metadata)
      
      // Convert lastVisit timestamp from microseconds to ISO date string
      if (metadata.lastVisit) {
        const timestampMs = Math.floor(parseInt(metadata.lastVisit) / 1000)
        metadata.lastVisit = new Date(timestampMs).toISOString()
      }
      
      // Parse products if they exist
      if (metadata.products && metadata.products.length > 0 && metadata.products[0]) {
        const productsString = metadata.products[0]
        const productStrings = productsString.split(',').filter(Boolean)
        
        metadata.products = productStrings.map((productStr: string) => {
          const parts = productStr.split('::URL::')
          if (parts.length === 2) {
            return {
              title: parts[0].trim(),
              url: parts[1].trim()
            }
          } else {
            // Fallback for products without URL
            return { title: productStr.trim(), url: null }
          }
        })
      } else {
        metadata.products = []
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
    console.error('Error fetching repeat visit tasks:', error)
    return NextResponse.json({ error: 'Failed to fetch repeat visit tasks' }, { status: 500 })
  } finally {
    await db.close()
  }
} 