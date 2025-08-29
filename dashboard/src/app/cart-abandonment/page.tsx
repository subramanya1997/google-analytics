"use client"

import { useEffect, useState, useCallback } from "react"
import { TaskCard } from "@/components/tasks/task-card"
import { Skeleton } from "@/components/ui/skeleton"
import { Task, PurchaseCartTask } from "@/types/tasks"
import { useDashboard } from "@/contexts/dashboard-context"
import { buildApiQueryParams } from "@/lib/api-utils"

interface CartApiProduct {
  item_name: string
  quantity: number
  price: number
  item_id: string
}

interface CartApiTask {
  session_id: string
  user_id: string
  customer_name?: string
  email?: string
  phone?: string
  total_value: number
  items_count: number
  products: CartApiProduct[]
  event_date: string
}

interface CartApiResponse {
  data: CartApiTask[]
}

export default function CartAbandonmentPage() {
  const { selectedLocation, dateRange } = useDashboard()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)

  const fetchCartTasks = useCallback(async () => {
    try {
      setLoading(true)
      
      const queryParams = buildApiQueryParams(selectedLocation, dateRange)
      const baseUrl = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
      const url = `${baseUrl}/tasks/cart-abandonment${queryParams}`
        
      const response = await fetch(url)
      const data: CartApiResponse = await response.json()

      const transformedTasks: Task[] = (data.data || []).map((task: CartApiTask) => {
        // Calculate priority based on cart value and time
        const cartValue = task.total_value || 0;
        const eventDate = new Date(task.event_date);
        const hoursSinceAbandonment = Math.floor((Date.now() - eventDate.getTime()) / (1000 * 60 * 60));
        
        let priority: 'high' | 'medium' | 'low' = 'medium';
        if (cartValue > 500 || (cartValue > 200 && hoursSinceAbandonment < 24)) {
          priority = 'high';
        } else if (cartValue < 50 || hoursSinceAbandonment > 72) {
          priority = 'low';
        }

        return {
          id: task.session_id,
          type: 'cart',
          priority,
          title: `Abandoned Cart: ${task.session_id}`,
          description: `${task.items_count} items worth $${task.total_value.toFixed(2)}`,
        customer: {
          id: task.user_id,
          name: task.customer_name || 'Unknown User',
          email: task.email,
          phone: task.phone,
        },
        productDetails: (task.products || []).map((p: CartApiProduct) => ({
          name: p.item_name,
          quantity: p.quantity,
          price: p.price,
          sku: p.item_id
        })),
        metadata: {
          cartValue: task.total_value,
          products: task.products?.map((p: CartApiProduct) => p.item_name) || []
        },
        createdAt: task.event_date,
        userId: task.user_id,
        sessionId: task.session_id,
      };
      });

      setTasks(transformedTasks)
    } catch (error) {
      console.error('Error fetching cart tasks:', error)
    } finally {
      setLoading(false)
    }
  }, [selectedLocation, dateRange])

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchCartTasks()
    }
  }, [dateRange, fetchCartTasks])

  return (
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
                task={task as PurchaseCartTask}
              />
            ))}
          </div>
        )}
      </div>
  )
} 