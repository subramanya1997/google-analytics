import { NextRequest, NextResponse } from 'next/server'
import { getDb } from '@/lib/db'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const taskId = searchParams.get('taskId')
  const taskType = searchParams.get('taskType')

  if (!taskId || !taskType) {
    return NextResponse.json({ error: 'taskId and taskType are required' }, { status: 400 })
  }

  const db = await getDb()
  
  try {
    const query = `
      SELECT * FROM task_tracking 
      WHERE task_id = ? AND task_type = ?
    `
    
    const result = await db.get(query, taskId, taskType)
    
    return NextResponse.json({ 
      taskId,
      taskType,
      completed: result?.completed || false,
      notes: result?.notes || '',
      completedAt: result?.completed_at || null,
      completedBy: result?.completed_by || null
    })
  } catch (error) {
    console.error('Error fetching task status:', error)
    return NextResponse.json({ error: 'Failed to fetch task status' }, { status: 500 })
  } finally {
    await db.close()
  }
}

export async function PUT(request: NextRequest) {
  const body = await request.json()
  const { taskId, taskType, completed, notes, completedBy } = body

  if (!taskId || !taskType) {
    return NextResponse.json({ error: 'taskId and taskType are required' }, { status: 400 })
  }

  const db = await getDb()
  
  try {
    const now = new Date().toISOString()
    
    const query = `
      INSERT INTO task_tracking (task_id, task_type, completed, notes, completed_at, completed_by, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(task_id, task_type) 
      DO UPDATE SET 
        completed = excluded.completed,
        notes = excluded.notes,
        completed_at = CASE 
          WHEN excluded.completed = 1 AND task_tracking.completed = 0 THEN excluded.completed_at
          WHEN excluded.completed = 0 THEN NULL
          ELSE task_tracking.completed_at
        END,
        completed_by = CASE 
          WHEN excluded.completed = 1 THEN excluded.completed_by
          ELSE task_tracking.completed_by
        END,
        updated_at = excluded.updated_at
    `
    
    await db.run(
      query, 
      taskId, 
      taskType, 
      completed ? 1 : 0, 
      notes || null, 
      completed ? now : null,
      completed ? completedBy || 'Unknown' : null,
      now
    )
    
    return NextResponse.json({ 
      success: true,
      taskId,
      taskType,
      completed,
      notes,
      completedAt: completed ? now : null,
      completedBy: completed ? completedBy || 'Unknown' : null
    })
  } catch (error) {
    console.error('Error updating task status:', error)
    return NextResponse.json({ error: 'Failed to update task status' }, { status: 500 })
  } finally {
    await db.close()
  }
}

export async function POST(request: NextRequest) {
  // Batch update for multiple tasks
  const body = await request.json()
  const { tasks } = body

  if (!tasks || !Array.isArray(tasks)) {
    return NextResponse.json({ error: 'tasks array is required' }, { status: 400 })
  }

  const db = await getDb()
  
  try {
    const now = new Date().toISOString()
    
    // Prepare batch insert/update
    const query = `
      INSERT INTO task_tracking (task_id, task_type, completed, notes, completed_at, completed_by, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(task_id, task_type) 
      DO UPDATE SET 
        completed = excluded.completed,
        notes = excluded.notes,
        completed_at = CASE 
          WHEN excluded.completed = 1 AND task_tracking.completed = 0 THEN excluded.completed_at
          WHEN excluded.completed = 0 THEN NULL
          ELSE task_tracking.completed_at
        END,
        completed_by = CASE 
          WHEN excluded.completed = 1 THEN excluded.completed_by
          ELSE task_tracking.completed_by
        END,
        updated_at = excluded.updated_at
    `
    
    const stmt = await db.prepare(query)
    
    for (const task of tasks) {
      await stmt.run(
        task.taskId,
        task.taskType,
        task.completed ? 1 : 0,
        task.notes || null,
        task.completed ? now : null,
        task.completed ? task.completedBy || 'Unknown' : null,
        now
      )
    }
    
    await stmt.finalize()
    
    return NextResponse.json({ 
      success: true,
      updatedCount: tasks.length
    })
  } catch (error) {
    console.error('Error batch updating task status:', error)
    return NextResponse.json({ error: 'Failed to batch update task status' }, { status: 500 })
  } finally {
    await db.close()
  }
} 