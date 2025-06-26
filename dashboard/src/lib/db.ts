import sqlite3 from 'sqlite3'
import { open } from 'sqlite'
import path from 'path'

// Database path - using the enhanced database with all fields
const DB_PATH = path.join(process.cwd(), '..', 'db', 'branch_wise_location.db')

export async function getDb() {
  return open({
    filename: DB_PATH,
    driver: sqlite3.Database
  })
}

export interface PurchaseTask {
  transaction_id: string
  event_date: string
  value: number
  page_location: string
  ga_session_id: string
  user_id?: string
  customer_name?: string
  email?: string
  phone?: string
}

export interface CartAbandonmentTask {
  session_id: string
  event_date: string
  last_activity: string
  items_count: number
}

export interface SearchTask {
  session_id: string
  event_date: string
  search_term: string
  search_type: 'no_results' | 'with_results'
  search_count: number
}

export interface RepeatVisitTask {
  product_url: string
  session_count: number
  last_view_date: string
  total_views: number
} 