"use client"

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'
import { DateRange } from 'react-day-picker'
import { startOfDay, subDays } from 'date-fns'
import { fetchLocations } from '@/lib/api-utils'
import { Location } from '@/types'

interface DashboardContextType {
  selectedLocation: string | null
  setSelectedLocation: (location: string | null) => void
  dateRange: DateRange | undefined
  setDateRange: (range: DateRange | undefined) => void
  locations: Location[]
  loadingLocations: boolean
  refreshLocations: () => Promise<void>
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined)

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null)
  const [locations, setLocations] = useState<Location[]>([])
  const [loadingLocations, setLoadingLocations] = useState(false)
  const [locationsCacheTime, setLocationsCacheTime] = useState<number>(0)
  const isFetchingRef = useRef(false)
  const didInitRef = useRef(false)
  const lastFetchAtRef = useRef<number>(0)
  
  // Initialize with last 7 days from yesterday
  const yesterday = startOfDay(subDays(new Date(), 1))
  const sevenDaysAgo = startOfDay(subDays(yesterday, 6))
  const [dateRange, setDateRange] = useState<DateRange | undefined>({
    from: sevenDaysAgo,
    to: yesterday,
  })
  
  // Internal fetch function with TTL and in-flight guard
  const doFetchLocations = useCallback(async (force: boolean = false) => {
    if (isFetchingRef.current) return
    const now = Date.now()

    const SESSION_STORAGE_KEY = 'dashboard_locations_cache'
    const CACHE_TTL_MS = 5 * 60 * 1000

    const cachedAt = locationsCacheTime || lastFetchAtRef.current
    if (!force && locations.length > 0 && cachedAt && (now - cachedAt) < CACHE_TTL_MS) {
      return
    }

    try {
      isFetchingRef.current = true
      setLoadingLocations(true)

      const controller = new AbortController()
      const timeoutId = setTimeout(() => {
        controller.abort(new Error('Request timeout after 2.5 seconds'))
      }, 2500)
      
      let data: Location[] = []
      
      try {
        const response = await fetchLocations(controller.signal)
        
        if (!response || !response.ok) {
          throw new Error(`Failed to fetch locations${response ? `: ${response.status}` : ''}`)
        }
        
        clearTimeout(timeoutId)

        data = await response.json()
        setLocations(data)
        setLocationsCacheTime(now)
        lastFetchAtRef.current = now
      } catch (error) {
        clearTimeout(timeoutId)
        
        // Handle AbortError specifically
        if (error instanceof Error && error.name === 'AbortError') {
          console.warn('Location fetch was aborted (likely due to timeout)')
          return // Don't throw AbortError, just return silently
        }
        
        throw error
      }

      try {
        if (data && data.length > 0) {
          sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ data: data, cachedAt: now }))
        }
      } catch {
        // ignore storage errors
      }
    } catch (error) {
      // Only log non-abort errors
      if (!(error instanceof Error && error.name === 'AbortError')) {
        console.error('Error fetching locations:', error)
      }
    } finally {
      isFetchingRef.current = false
      setLoadingLocations(false)
    }
  }, [locationsCacheTime, locations.length])

  // Refresh locations (force fetch)
  const refreshLocations = useCallback(async () => {
    const SESSION_STORAGE_KEY = 'dashboard_locations_cache'
    try {
      sessionStorage.removeItem(SESSION_STORAGE_KEY)
    } catch {
      // ignore storage errors
    }
    setLocations([])
    setLocationsCacheTime(0)
    await doFetchLocations(true)
  }, [doFetchLocations])

  // Fetch locations on mount
  useEffect(() => {
    if (didInitRef.current) return
    didInitRef.current = true

    const loadFromSession = () => {
      const SESSION_STORAGE_KEY = 'dashboard_locations_cache'
      const CACHE_TTL_MS = 5 * 60 * 1000
      try {
        const raw = sessionStorage.getItem(SESSION_STORAGE_KEY)
        if (!raw) return false
        const parsed = JSON.parse(raw) as { data: Location[]; cachedAt: number }
        if (!Array.isArray(parsed.data) || typeof parsed.cachedAt !== 'number') return false
        const age = Date.now() - parsed.cachedAt
        if (age >= CACHE_TTL_MS) return false
        setLocations(parsed.data)
        setLocationsCacheTime(parsed.cachedAt)
        lastFetchAtRef.current = parsed.cachedAt
        return true
      } catch {
        return false
      }
    }

    const init = async () => {
      const hasValidCache = loadFromSession()
      if (!hasValidCache) {
        await doFetchLocations(false)
      }
    }

    void init()
  }, [doFetchLocations])

  return (
    <DashboardContext.Provider 
      value={{ 
        selectedLocation, 
        setSelectedLocation, 
        dateRange, 
        setDateRange,
        locations,
        loadingLocations,
        refreshLocations
      }}
    >
      {children}
    </DashboardContext.Provider>
  )
}

export function useDashboard() {
  const context = useContext(DashboardContext)
  if (context === undefined) {
    throw new Error('useDashboard must be used within a DashboardProvider')
  }
  return context
} 