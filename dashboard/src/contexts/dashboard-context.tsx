"use client"

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'
import { DateRange } from 'react-day-picker'
import { startOfDay, subDays } from 'date-fns'
import { fetchLocations, fetchDataAvailability } from '@/lib/api-utils'
import { Location, DataAvailability } from '@/types'

interface DashboardContextType {
  selectedLocation: string | null
  setSelectedLocation: (location: string | null) => void
  dateRange: DateRange | undefined
  setDateRange: (range: DateRange | undefined) => void
  locations: Location[]
  loadingLocations: boolean
  refreshLocations: () => Promise<void>
  dataAvailability: DataAvailability | null
  loadingDataAvailability: boolean
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined)

const SESSION_STORAGE_KEY = 'dashboard_locations_cache'
const CACHE_TTL_MS = 5 * 60 * 1000

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null)
  const [locations, setLocations] = useState<Location[]>([])
  const [loadingLocations, setLoadingLocations] = useState(false)
  const [locationsCacheTime, setLocationsCacheTime] = useState<number>(0)
  const isFetchingRef = useRef(false)
  const didInitRef = useRef(false)
  const lastFetchAtRef = useRef<number>(0)
  
  // Data availability state
  const [dataAvailability, setDataAvailability] = useState<DataAvailability | null>(null)
  const [loadingDataAvailability, setLoadingDataAvailability] = useState(false)

  // Initialize with last 7 days from yesterday
  const [dateRange, setDateRange] = useState<DateRange | undefined>(() => {
    const yesterday = startOfDay(subDays(new Date(), 1))
    return { from: startOfDay(subDays(yesterday, 6)), to: yesterday }
  })
  
  // Internal fetch function with TTL and in-flight guard
  const doFetchLocations = useCallback(async (force: boolean = false) => {
    if (isFetchingRef.current) return
    const now = Date.now()

    const cachedAt = locationsCacheTime || lastFetchAtRef.current
    if (!force && locations.length > 0 && cachedAt && (now - cachedAt) < CACHE_TTL_MS) {
      return
    }

    try {
      isFetchingRef.current = true
      setLoadingLocations(true)

      const controller = new AbortController()
      const timeoutId = setTimeout(() => {
        controller.abort()
      }, 10000) // Increased to 10 seconds
      
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
        if (error instanceof Error && (error.name === 'AbortError' || error.message.includes('aborted'))) {
          console.warn('Location fetch was aborted (likely due to timeout)')
          return // Don't throw AbortError, just return silently
        }
        
        // Handle timeout errors
        if (error instanceof Error && error.message.includes('timeout')) {
          console.warn('Location fetch timed out')
          return // Don't throw timeout errors, just return silently
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
      console.error('Error fetching locations:', error)

      // Try to load from cache as fallback if we don't have any locations
      if (locations.length === 0) {
        try {
          const raw = sessionStorage.getItem(SESSION_STORAGE_KEY)
          if (raw) {
            const parsed = JSON.parse(raw) as { data: Location[]; cachedAt: number }
            if (Array.isArray(parsed.data) && parsed.data.length > 0) {
              console.info('Loaded locations from cache as fallback')
              setLocations(parsed.data)
              setLocationsCacheTime(parsed.cachedAt)
            }
          }
        } catch {
          // ignore cache errors
        }
      }
    } finally {
      isFetchingRef.current = false
      setLoadingLocations(false)
    }
  }, [locationsCacheTime, locations.length])

  // Refresh locations (force fetch)
  const refreshLocations = useCallback(async () => {
    try {
      sessionStorage.removeItem(SESSION_STORAGE_KEY)
    } catch {
      // ignore storage errors
    }
    setLocations([])
    setLocationsCacheTime(0)
    await doFetchLocations(true)
  }, [doFetchLocations])

  // Fetch data availability
  const doFetchDataAvailability = useCallback(async () => {
    try {
      setLoadingDataAvailability(true)
      const response = await fetchDataAvailability()
      if (!response.ok) {
        throw new Error('Failed to fetch data availability')
      }
      const data = await response.json()
      setDataAvailability(data.summary ?? data)
    } catch (error) {
      console.error('Error fetching data availability:', error)
    } finally {
      setLoadingDataAvailability(false)
    }
  }, [])

  // Fetch locations and data availability on mount
  useEffect(() => {
    if (didInitRef.current) return
    didInitRef.current = true

    const loadFromSession = () => {
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
      await doFetchDataAvailability()
    }

    void init()
  }, [doFetchLocations, doFetchDataAvailability])

  return (
    <DashboardContext.Provider 
      value={{ 
        selectedLocation, 
        setSelectedLocation, 
        dateRange, 
        setDateRange,
        locations,
        loadingLocations,
        refreshLocations,
        dataAvailability,
        loadingDataAvailability,
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