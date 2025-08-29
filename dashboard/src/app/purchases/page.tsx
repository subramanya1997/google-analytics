"use client"

import { useEffect, useState, useCallback } from "react"
import { useDashboard } from "@/contexts/dashboard-context"
import { buildApiQueryParams } from "@/lib/api-utils"
import { TaskCard } from "@/components/tasks/task-card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Search, Filter } from "lucide-react"
import { Task, PurchaseCartTask } from "@/types/tasks"

interface PurchaseApiProduct {
  item_name: string
  quantity: number
  price: number
  item_id: string
}

interface PurchaseApiTask {
  transaction_id: string
  user_id: string
  customer_name?: string
  email?: string
  phone?: string
  order_value: number
  products: PurchaseApiProduct[]
  event_date: string
  session_id: string
}

interface PurchaseApiResponse {
  data: PurchaseApiTask[]
}

export default function PurchasesPage() {
  const { selectedLocation, dateRange } = useDashboard()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchPurchaseTasks = useCallback(async () => {
    try {
      setLoading(true)
      const queryParams = buildApiQueryParams(selectedLocation, dateRange)
      const baseUrl = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
      const url = `${baseUrl}/tasks/purchases${queryParams}`
        
      const response = await fetch(url)
      const data: PurchaseApiResponse = await response.json()

      const transformedTasks: Task[] = (data.data || []).map((task: PurchaseApiTask) => {
        // Calculate priority based on order value and recency
        const orderValue = task.order_value || 0;
        const eventDate = new Date(task.event_date);
        const hoursSincePurchase = Math.floor((Date.now() - eventDate.getTime()) / (1000 * 60 * 60));
        
        let priority: 'high' | 'medium' | 'low' = 'medium';
        if (orderValue > 1000 || (orderValue > 500 && hoursSincePurchase < 24)) {
          priority = 'high';
        } else if (orderValue < 100 || hoursSincePurchase > 168) { // 1 week
          priority = 'low';
        }

        return {
          id: task.transaction_id,
          type: 'purchase',
          priority,
          title: `Purchase #${task.transaction_id}`,
          description: `Order value: $${task.order_value.toFixed(2)}`,
        customer: {
          id: task.user_id,
          name: task.customer_name || 'Unknown User',
          email: task.email,
          phone: task.phone,
          orderValue: task.order_value,
        } as const,
        productDetails: (task.products || []).map((p: PurchaseApiProduct) => ({
          name: p.item_name,
          quantity: p.quantity,
          price: p.price,
          sku: p.item_id
        })),
        createdAt: task.event_date,
        userId: task.user_id,
        sessionId: task.session_id,
      };
      });

      setTasks(transformedTasks)
    } catch (error) {
      console.error('Error fetching purchase tasks:', error)
      setError(error instanceof Error ? error.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }, [selectedLocation, dateRange])

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchPurchaseTasks()
    }
  }, [dateRange, fetchPurchaseTasks])

  return (
    <div className="space-y-4 sm:space-y-6">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
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
          <Button variant="outline" size="icon" className="shrink-0">
            <Filter className="h-4 w-4" />
          </Button>
        </div>

        {/* Task Cards Grid */}
        {loading ? (
          <div className="grid gap-4 sm:gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-[200px]" />
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-8 text-red-500">
            Error: {error}
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-8 sm:py-12">
            <p className="text-muted-foreground">
              {selectedLocation 
                ? "No purchase tasks for this location and date range" 
                : "No purchase tasks for this date range"}
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
            {tasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task as PurchaseCartTask}
              />
            ))}
          </div>
        )}

        {/* Summary Stats */}
        {!loading && tasks.length > 0 && (
          <div className="mt-6 sm:mt-8 rounded-lg border bg-card p-4 sm:p-6">
            <h3 className="text-base sm:text-lg font-semibold mb-4">Summary Statistics</h3>
            <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
              <div>
                <p className="text-xs sm:text-sm text-muted-foreground">Total Value</p>
                <p className="text-xl sm:text-2xl font-bold">
                  ${tasks.reduce((sum, task) => sum + (task.customer.orderValue || 0), 0).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-muted-foreground">Avg Order Value</p>
                <p className="text-xl sm:text-2xl font-bold">
                  ${(tasks.reduce((sum, task) => sum + (task.customer.orderValue || 0), 0) / tasks.length).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-muted-foreground">High Priority</p>
                <p className="text-xl sm:text-2xl font-bold">
                  {tasks.filter(task => task.priority === 'high').length}
                </p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-muted-foreground">Total Tasks</p>
                <p className="text-xl sm:text-2xl font-bold">{tasks.length}</p>
              </div>
            </div>
          </div>
        )}
      </div>
  )
} 