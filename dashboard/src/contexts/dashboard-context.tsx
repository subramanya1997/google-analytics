"use client"

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { DateRange } from 'react-day-picker'
import { startOfDay, subDays } from 'date-fns'

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
  
  // Initialize with last 7 days from yesterday
  const yesterday = startOfDay(subDays(new Date(), 1))
  const sevenDaysAgo = startOfDay(subDays(yesterday, 6))
  const [dateRange, setDateRange] = useState<DateRange | undefined>({
    from: sevenDaysAgo,
    to: yesterday,
  })
  
  // Fetch locations with caching (5 minutes TTL)
  const fetchLocations = useCallback(async () => {
    const now = Date.now()
    const cacheTTL = 5 * 60 * 1000 // 5 minutes in milliseconds
    
    // Check if we have cached locations that are still valid
    if (locations.length > 0 && (now - locationsCacheTime) < cacheTTL && !loadingLocations) {
      console.log('Using cached locations (cache age:', Math.round((now - locationsCacheTime) / 1000), 'seconds)')
      return
    }
    
    try {
      console.log('Fetching fresh locations from API...')
      setLoadingLocations(true)
      const baseUrl = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
      const tenantId = '550e8400-e29b-41d4-a716-446655440000'
      const url = `${baseUrl}/locations?tenant_id=${tenantId}`
      
      const response = await fetch(url)
      const data = await response.json()
      setLocations(data)
      setLocationsCacheTime(now)
      console.log('Locations cached successfully')
    } catch (error) {
      console.error('Error fetching locations:', error)
    } finally {
      setLoadingLocations(false)
    }
  }, [locations.length, locationsCacheTime, loadingLocations])

  // Refresh locations (force fetch)
  const refreshLocations = async () => {
    setLocations([])
    setLocationsCacheTime(0)
    await fetchLocations()
  }

  // Fetch locations on mount
  useEffect(() => {
    fetchLocations()
  }, [fetchLocations])

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