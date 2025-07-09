"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { TaskCard } from "@/components/tasks/task-card"
import { Skeleton } from "@/components/ui/skeleton"
import { Task } from "@/types/tasks"
import { useDashboard } from "@/contexts/dashboard-context"
import { buildApiQueryParams } from "@/lib/api-utils"

export default function CartAbandonmentPage() {
  const { selectedLocation, dateRange } = useDashboard()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchCartTasks()
    }
  }, [selectedLocation, dateRange])

  const fetchCartTasks = async () => {
    try {
      setLoading(true)
      
      const queryParams = buildApiQueryParams(selectedLocation, dateRange)
      const url = `/api/tasks/cart-abandonment${queryParams}`
        
      const response = await fetch(url)
      const data = await response.json()
      setTasks(data.tasks || [])
    } catch (error) {
      console.error('Error fetching cart tasks:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-4 sm:space-y-6">
        {loading ? (
          <div className="grid gap-4 sm:gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-[200px]" />
            ))}
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-8 sm:py-12">
            <p className="text-muted-foreground">
              {selectedLocation 
                ? "No abandoned cart tasks for this location and date range" 
                : "No abandoned cart tasks for this date range"}
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
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