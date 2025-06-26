"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { TaskCard } from "@/components/tasks/task-card"
import { LocationSelector } from "@/components/ui/location-selector"
import { Skeleton } from "@/components/ui/skeleton"
import { Task } from "@/types/tasks"

export default function CartAbandonmentPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null)

  useEffect(() => {
    fetchCartTasks()
  }, [selectedLocation])

  const fetchCartTasks = async () => {
    try {
      const url = selectedLocation 
        ? `/api/tasks/cart-abandonment?locationId=${selectedLocation}`
        : '/api/tasks/cart-abandonment'
        
      const response = await fetch(url)
      const data = await response.json()
      setTasks(data.tasks || [])
    } catch (error) {
      console.error('Error fetching cart tasks:', error)
    } finally {
      setLoading(false)
    }
  }

  const subtitle = selectedLocation 
    ? `Recover lost sales by reaching out to customers who left items in their cart (Filtered by location)`
    : "Recover lost sales by reaching out to customers who left items in their cart"

  return (
    <DashboardLayout
      title="Cart Abandonment Recovery"
      subtitle={subtitle}
    >
      <div className="space-y-6">
        {/* Location Selector */}
        <div className="flex justify-between items-center">
          <LocationSelector
            selectedLocation={selectedLocation}
            onLocationChange={setSelectedLocation}
          />
        </div>

        {loading ? (
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-[200px]" />
            ))}
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">
              {selectedLocation 
                ? "No abandoned cart tasks for this location" 
                : "No abandoned cart tasks at the moment"}
            </p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {tasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task as any}
              />
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
} 