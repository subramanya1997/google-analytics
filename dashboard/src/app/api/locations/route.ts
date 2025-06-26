import { NextResponse } from 'next/server'
import { getDb } from '@/lib/db'

export async function GET() {
  try {
    const db = await getDb()
    
    // Get all locations that have activity
    const locations = await db.all(`
      SELECT DISTINCT
        l.warehouse_code as locationId,
        l.warehouse_name as locationName,
        l.city,
        l.state
      FROM locations l
      WHERE EXISTS (
        SELECT 1 FROM page_view pv WHERE pv.user_prop_default_branch_id = l.warehouse_code
      )
      ORDER BY l.warehouse_code
    `)
    
    await db.close()
    
    return NextResponse.json({ locations })
  } catch (error) {
    console.error('Error fetching locations:', error)
    return NextResponse.json({ error: 'Failed to fetch locations' }, { status: 500 })
  }
} 