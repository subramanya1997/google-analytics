"use client"

import { useEffect, useState } from "react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { MapPin } from "lucide-react"

interface Location {
  locationId: string
  locationName: string
  city: string
  state: string
}

interface LocationSelectorProps {
  selectedLocation: string | null
  onLocationChange: (locationId: string | null) => void
  className?: string
}

export function LocationSelector({ selectedLocation, onLocationChange, className }: LocationSelectorProps) {
  const [locations, setLocations] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLocations()
  }, [])

  const fetchLocations = async () => {
    try {
      const response = await fetch('/api/locations')
      const data = await response.json()
      setLocations(data.locations)
    } catch (error) {
      console.error('Error fetching locations:', error)
    } finally {
      setLoading(false)
    }
  }

  const getLocationDisplay = () => {
    if (selectedLocation === null || selectedLocation === "all") {
      return "All Locations"
    }
    const location = locations.find(loc => loc.locationId === selectedLocation)
    if (location) {
      return `${location.locationName} - ${location.city}, ${location.state}`
    }
    return "Select location"
  }

  return (
    <Select
      value={selectedLocation || "all"}
      onValueChange={(value) => onLocationChange(value === "all" ? null : value)}
    >
      <SelectTrigger className={`w-full sm:w-[250px] ${className || ''}`}>
        <div className="flex items-center gap-2 truncate">
          <MapPin className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="truncate">{getLocationDisplay()}</span>
        </div>
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All Locations</SelectItem>
        {locations.map((location) => (
          <SelectItem key={location.locationId} value={location.locationId}>
            <span className="truncate">
              {location.locationName} - {location.city}, {location.state}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
} 