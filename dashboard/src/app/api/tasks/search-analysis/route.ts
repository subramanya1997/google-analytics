import { NextResponse } from 'next/server'
import { getDb } from '@/lib/db'
import { correlateSessionToUser } from '@/lib/user-matching'
import { Task } from '@/types/tasks'

export async function GET(request: Request) {
  const db = await getDb()
  
  try {
    const { searchParams } = new URL(request.url)
    const page = parseInt(searchParams.get('page') || '1')
    const limit = parseInt(searchParams.get('limit') || '50')
    const includeConverted = searchParams.get('includeConverted') === 'true'
    const query = (searchParams.get('q') || '').toLowerCase()
    const locationId = searchParams.get('locationId')
    const startDate = searchParams.get('startDate')
    const endDate = searchParams.get('endDate')
    const offset = (page - 1) * limit
    
    // Build location filter
    const locationFilter = locationId ? " AND user_prop_default_branch_id = ? " : ""
    const locationParams = locationId ? [locationId] : []
    
    // Build date filter
    let dateFilter = ''
    let dateParams: string[] = []
    if (startDate && endDate) {
      // Convert ISO dates to YYYYMMDD format used in database
      const start = startDate.replace(/-/g, '')
      const end = endDate.replace(/-/g, '')
      dateFilter = " AND event_date BETWEEN ? AND ? "
      dateParams = [start, end]
    }
    
    // Build search filter for failed searches
    const failedSearchFilter = query ? 
      " AND LOWER(param_no_search_results_term) LIKE ? " : ""
    const failedSearchParams = query ? [`%${query}%`] : []
    const failedSearchAllParams = [...failedSearchParams, ...locationParams, ...dateParams]
    
    // Count failed searches
    const failedSearchCountQuery = `
      SELECT COUNT(*) as count
      FROM (
        SELECT DISTINCT param_ga_session_id, param_no_search_results_term
        FROM no_search_results
        WHERE param_no_search_results_term IS NOT NULL
        ${failedSearchFilter}
        ${locationFilter}
        ${dateFilter}
      ) AS tmp
    `
    
    // Get failed searches
    const failedSearchesQuery = `
      SELECT 
        nsr.param_ga_session_id as session_id,
        nsr.param_no_search_results_term as search_term,
        nsr.event_date,
        nsr.event_timestamp,
        nsr.user_prop_default_branch_id as branch_id,
        COUNT(*) as search_attempts,
        EXISTS(
          SELECT 1 FROM purchase p 
          WHERE p.param_ga_session_id = nsr.param_ga_session_id
          ${locationId ? 'AND p.user_prop_default_branch_id = nsr.user_prop_default_branch_id' : ''}
          ${dateFilter.replace(/event_date/g, 'p.event_date')}
        ) as has_purchase,
        l.warehouse_name as location_name,
        l.city,
        l.state
      FROM no_search_results nsr
      LEFT JOIN locations l ON nsr.user_prop_default_branch_id = l.warehouse_code
      WHERE nsr.param_no_search_results_term IS NOT NULL
      ${failedSearchFilter}
      ${locationFilter}
      ${dateFilter}
      GROUP BY nsr.param_ga_session_id, nsr.param_no_search_results_term, nsr.user_prop_default_branch_id
      ORDER BY search_attempts DESC, nsr.event_timestamp DESC
      LIMIT ? OFFSET ?
    `
    
    // Build search filter for unconverted searches
    const searchFilter = query ? " AND LOWER(vsr.param_search_term) LIKE ? " : ""
    const searchQueryParams = query ? [`%${query}%`] : []
    
    // Build conversion filter
    const conversionFilter = includeConverted ? "" : `
      AND vsr.param_ga_session_id NOT IN (
        SELECT DISTINCT param_ga_session_id FROM purchase
        WHERE 1=1 ${locationFilter}
        ${dateFilter}
      )
    `
    
    // Count unconverted searches
    const unconvertedSearchCountQuery = `
      SELECT COUNT(DISTINCT param_ga_session_id) as count
      FROM view_search_results vsr
      WHERE param_search_term IS NOT NULL
        ${conversionFilter}
        ${searchFilter}
        ${locationFilter}
        ${dateFilter}
        AND param_ga_session_id IN (
          SELECT param_ga_session_id 
          FROM view_search_results 
          WHERE param_search_term IS NOT NULL
            ${searchFilter}
            ${locationFilter}
            ${dateFilter}
          GROUP BY param_ga_session_id 
          HAVING COUNT(*) > 2
        )
    `
    
    // Get unconverted searches
    const unconvertedSearchesQuery = `
      WITH search_sessions AS (
        SELECT 
          vsr.param_ga_session_id as session_id,
          vsr.event_date,
          vsr.event_timestamp,
          vsr.user_prop_default_branch_id as branch_id,
          COUNT(DISTINCT vsr.param_search_term) as unique_terms,
          COUNT(*) as total_searches,
          GROUP_CONCAT(vsr.param_search_term, ', ') as all_search_terms,
          ${includeConverted ? `
            EXISTS(
              SELECT 1 FROM purchase p 
              WHERE p.param_ga_session_id = vsr.param_ga_session_id
              ${locationId ? 'AND p.user_prop_default_branch_id = vsr.user_prop_default_branch_id' : ''}
              ${dateFilter.replace(/event_date/g, 'p.event_date')}
            )
          ` : '0'} as has_purchase,
          l.warehouse_name as location_name,
          l.city,
          l.state
        FROM view_search_results vsr
        LEFT JOIN locations l ON vsr.user_prop_default_branch_id = l.warehouse_code
        WHERE vsr.param_search_term IS NOT NULL
          ${conversionFilter}
          ${searchFilter}
          ${locationFilter}
          ${dateFilter}
        GROUP BY vsr.param_ga_session_id, vsr.user_prop_default_branch_id
        HAVING total_searches > 2
      )
      SELECT * FROM search_sessions
      ORDER BY total_searches DESC
      LIMIT ? OFFSET ?
    `
    
    // Execute queries
    const failedSearchCount = await db.get(failedSearchCountQuery, ...failedSearchAllParams)
    const unconvertedCountParams = query ? 
      (includeConverted ? [...searchQueryParams, ...locationParams, ...dateParams, ...searchQueryParams, ...locationParams, ...dateParams] : [...searchQueryParams, ...locationParams, ...dateParams, ...dateParams, ...searchQueryParams, ...locationParams, ...dateParams]) 
      : (includeConverted ? [...locationParams, ...dateParams, ...locationParams, ...dateParams] : [...locationParams, ...dateParams, ...dateParams, ...locationParams, ...dateParams])
    const unconvertedSearchCount = await db.get(unconvertedSearchCountQuery, ...unconvertedCountParams)
    
    const failedSearches = await db.all(
      failedSearchesQuery, 
      ...failedSearchAllParams, 
      Math.floor(limit / 2), 
      offset
    )
    
    const unconvertedSearchAllParams = [...searchQueryParams, ...locationParams, ...dateParams]
    const unconvertedSearches = await db.all(
      unconvertedSearchesQuery,
      ...unconvertedSearchAllParams,
      Math.ceil(limit / 2),
      offset
    )
    
    // Transform into tasks
    const tasks: Task[] = []
    
    // Process failed searches
    for (const [index, search] of failedSearches.entries()) {
      const user = await correlateSessionToUser(search.session_id, db, index)
      
      // Determine priority based on search attempts
      const priority: 'high' | 'medium' | 'low' = 
        search.search_attempts > 3 ? 'high' :
        search.search_attempts === 2 ? 'medium' : 'low'
      
      const locationInfo = search.location_name ? ` at ${search.location_name}` : ''
      
      tasks.push({
        id: `search-failed-${search.session_id}-${index}`,
        type: 'search',
        priority,
        title: 'Product not found - Add to inventory?',
        description: `Customer searched "${search.search_term}" ${search.search_attempts} times with no results${search.has_purchase ? ' (purchased other items)' : ''}${locationInfo}`,
        customer: {
          name: user?.name || 'Unknown Customer',
          email: user?.email || '',
          phone: user?.cell_phone || user?.office_phone || '',
          company: user?.customer_name || ''
        },
        metadata: {
          searchTerms: [search.search_term],
          issueType: 'no_results',
          visitCount: search.search_attempts,
          hasPurchase: Boolean(search.has_purchase),
          location: search.location_name ? `${search.location_name} - ${search.city}, ${search.state}` : undefined,
          branchId: search.branch_id
        },
        createdAt: new Date().toISOString()
      })
    }
    
    // Process unconverted searches
    for (const [index, search] of unconvertedSearches.entries()) {
      const user = await correlateSessionToUser(search.session_id, db, failedSearches.length + index)
      
      // Parse and deduplicate search terms
      const searchTerms: string[] = search.all_search_terms ? 
        [...new Set((search.all_search_terms as string).split(', ').filter(Boolean))].slice(0, 5) : 
        []
      
      const priority: 'high' | 'medium' | 'low' = 
        search.total_searches > 5 ? 'high' : 'medium'
      
      const locationInfo = search.location_name ? ` at ${search.location_name}` : ''
      
      tasks.push({
        id: `search-unconverted-${search.session_id}-${index}`,
        type: 'search',
        priority,
        title: search.has_purchase ? 
          'Customer searched extensively before purchasing' : 
          'Active searcher needs assistance',
        description: `Performed ${search.total_searches} searches across ${search.unique_terms} different terms${search.has_purchase ? ' before purchasing' : ' without purchasing'}${locationInfo}`,
        customer: {
          name: user?.name || 'Unknown Customer',
          email: user?.email || '',
          phone: user?.cell_phone || user?.office_phone || '',
          company: user?.customer_name || ''
        },
        metadata: {
          searchTerms: searchTerms.length > 0 ? searchTerms : ['Multiple searches'],
          visitCount: search.total_searches,
          issueType: 'no_conversion',
          hasPurchase: Boolean(search.has_purchase),
          location: search.location_name ? `${search.location_name} - ${search.city}, ${search.state}` : undefined,
          branchId: search.branch_id
        },
        createdAt: new Date().toISOString()
      })
    }
    
    const totalCount = (failedSearchCount?.count || 0) + (unconvertedSearchCount?.count || 0)
    
    return NextResponse.json({ 
      tasks,
      total: totalCount,
      page,
      limit,
      totalPages: Math.ceil(totalCount / limit),
      breakdown: {
        failedSearches: failedSearchCount?.count || 0,
        unconvertedSearches: unconvertedSearchCount?.count || 0
      }
    })
  } catch (error) {
    console.error('Error fetching search tasks:', error)
    return NextResponse.json({ error: 'Failed to fetch search tasks' }, { status: 500 })
  } finally {
    await db.close()
  }
} 