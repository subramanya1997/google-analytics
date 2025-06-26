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

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <MapPin className="h-4 w-4 text-muted-foreground" />
      <Select
        value={selectedLocation || "all"}
        onValueChange={(value) => onLocationChange(value === "all" ? null : value)}
      >
        <SelectTrigger className="w-[250px]">
          <SelectValue placeholder="Select location" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Locations</SelectItem>
          {locations.map((location) => (
            <SelectItem key={location.locationId} value={location.locationId}>
              {location.locationName} - {location.city}, {location.state}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
} 