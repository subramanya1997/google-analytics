"use client"

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'
import { DateRange } from 'react-day-picker'
import { startOfDay, subDays } from 'date-fns'
import { analyticsHeaders } from '@/lib/api-utils'

interface Location {
  locationId: string
  locationName: string
  city: string
  state: string
}

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

      // Prefer same-origin proxy to avoid cross-origin DNS/TLS and CORS
      const proxyUrl = `/api/analytics/locations`

      // Fallback to direct origin if proxy isn't configured/reachable
      const directBase = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
      const directUrl = directBase ? `${directBase}/locations` : ''

      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 2500)
      let response: Response | null = null

      try {
        response = await fetch(proxyUrl, {
          method: 'GET',
          headers: analyticsHeaders(),
          signal: controller.signal,
          cache: 'no-store',
          // keepalive helps allow abort without killing request on nav
          keepalive: true,
        })
      } catch {
        // ignore and try fallback below
      } finally {
        clearTimeout(timeoutId)
      }

      if ((!response || !response.ok) && directUrl) {
        const fallbackController = new AbortController()
        const fallbackTimeoutId = setTimeout(() => fallbackController.abort(), 2500)
        try {
          response = await fetch(directUrl, {
            method: 'GET',
            headers: analyticsHeaders(),
            signal: fallbackController.signal,
            cache: 'no-store',
            // Avoid sending cookies to cross-origin endpoint
            credentials: 'omit',
            referrerPolicy: 'no-referrer',
            keepalive: true,
          })
        } finally {
          clearTimeout(fallbackTimeoutId)
        }
      }

      if (!response || !response.ok) {
        throw new Error(`Failed to fetch locations${response ? `: ${response.status}` : ''}`)
      }

      const data = await response.json()
      setLocations(data)
      setLocationsCacheTime(now)
      lastFetchAtRef.current = now

      try {
        sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ data, cachedAt: now }))
      } catch {
        // ignore storage errors
      }
    } catch (error) {
      console.error('Error fetching locations:', error)
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