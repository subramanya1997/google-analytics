"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { TaskCard } from "@/components/tasks/task-card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Search, Filter } from "lucide-react"
import { LocationSelector } from "@/components/ui/location-selector"
import { Task } from "@/types/tasks"

export default function PurchasesPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null)

  useEffect(() => {
    fetchPurchaseTasks()
  }, [selectedLocation])

  const fetchPurchaseTasks = async () => {
    try {
      const url = selectedLocation 
        ? `/api/tasks/purchases?locationId=${selectedLocation}`
        : '/api/tasks/purchases'
        
      const response = await fetch(url)
      const data = await response.json()
      setTasks(data.tasks || [])
    } catch (error) {
      console.error('Error fetching purchase tasks:', error)
      setError(error instanceof Error ? error.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const subtitle = selectedLocation 
    ? `Engage with customers who made recent purchases (Filtered by location)`
    : "Engage with customers who made recent purchases"

  return (
    <DashboardLayout
      title="Purchase Follow-up"
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

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by customer, company, or product..."
              className="pl-9"
            />
          </div>
          <Select defaultValue="all">
            <SelectTrigger className="w-full sm:w-[180px]">
              <SelectValue placeholder="Filter by priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Priorities</SelectItem>
              <SelectItem value="high">High Priority</SelectItem>
              <SelectItem value="medium">Medium Priority</SelectItem>
              <SelectItem value="low">Low Priority</SelectItem>
            </SelectContent>
          </Select>
          <Select defaultValue="recent">
            <SelectTrigger className="w-full sm:w-[180px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="recent">Most Recent</SelectItem>
              <SelectItem value="value-high">Highest Value</SelectItem>
              <SelectItem value="value-low">Lowest Value</SelectItem>
              <SelectItem value="customer">Customer Name</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon">
            <Filter className="h-4 w-4" />
          </Button>
        </div>

        {/* Task Cards Grid */}
        {loading ? (
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-[200px]" />
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-8 text-red-500">
            Error: {error}
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">
              {selectedLocation 
                ? "No purchase tasks for this location" 
                : "No purchase tasks at the moment"}
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

        {/* Summary Stats */}
        {!loading && tasks.length > 0 && (
          <div className="mt-8 rounded-lg border bg-card p-6">
            <h3 className="text-lg font-semibold mb-4">Summary Statistics</h3>
            <div className="grid gap-4 md:grid-cols-4">
              <div>
                <p className="text-sm text-muted-foreground">Total Value</p>
                <p className="text-2xl font-bold">
                  ${tasks.reduce((sum, task) => sum + ((task.customer as any).orderValue || 0), 0).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Avg Order Value</p>
                <p className="text-2xl font-bold">
                  ${(tasks.reduce((sum, task) => sum + ((task.customer as any).orderValue || 0), 0) / tasks.length).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">High Priority</p>
                <p className="text-2xl font-bold">
                  {tasks.filter(task => task.priority === 'high').length}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Tasks</p>
                <p className="text-2xl font-bold">{tasks.length}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
} 