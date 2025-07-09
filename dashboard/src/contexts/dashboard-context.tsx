"use client"

import React, { createContext, useContext, useState, useEffect } from 'react'
import { DateRange } from 'react-day-picker'
import { startOfDay, subDays } from 'date-fns'

interface DashboardContextType {
  selectedLocation: string | null
  setSelectedLocation: (location: string | null) => void
  dateRange: DateRange | undefined
  setDateRange: (range: DateRange | undefined) => void
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined)

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null)
  
  // Initialize with last 7 days from yesterday
  const yesterday = startOfDay(subDays(new Date(), 1))
  const sevenDaysAgo = startOfDay(subDays(yesterday, 6))
  const [dateRange, setDateRange] = useState<DateRange | undefined>({
    from: sevenDaysAgo,
    to: yesterday,
  })

  return (
    <DashboardContext.Provider 
      value={{ 
        selectedLocation, 
        setSelectedLocation, 
        dateRange, 
        setDateRange 
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