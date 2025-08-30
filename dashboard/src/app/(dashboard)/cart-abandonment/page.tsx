"use client"

import { useEffect, useState, useCallback } from "react"
import { TaskCard } from "@/components/tasks/task-card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { ChevronLeft, ChevronRight } from "lucide-react"
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
  total: number
  page: number
  limit: number
  has_more: boolean
}

export default function CartAbandonmentPage() {
  const { selectedLocation, dateRange } = useDashboard()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [itemsPerPage, setItemsPerPage] = useState(50)

  const fetchCartTasks = useCallback(async () => {
    try {
      setLoading(true)
      
      const queryParams = buildApiQueryParams(selectedLocation, dateRange, {
        page: currentPage,
        limit: itemsPerPage
      })
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
      setTotalCount(data.total || 0)
      setTotalPages(data.total ? Math.ceil(data.total / itemsPerPage) : 1)
    } catch (error) {
      console.error('Error fetching cart tasks:', error)
    } finally {
      setLoading(false)
    }
  }, [selectedLocation, dateRange, currentPage, itemsPerPage])

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchCartTasks()
    }
  }, [dateRange, fetchCartTasks])

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const handleItemsPerPageChange = (value: string) => {
    setItemsPerPage(parseInt(value))
    setCurrentPage(1) // Reset to first page when changing items per page
  }

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
          <>
            <div className="grid gap-4 sm:gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
              {tasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task as PurchaseCartTask}
                />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-2">
                <div className="flex items-center space-x-2">
                  <p className="text-sm text-muted-foreground">
                    Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, totalCount)} of {totalCount} tasks
                  </p>
                  <Select value={itemsPerPage.toString()} onValueChange={handleItemsPerPageChange}>
                    <SelectTrigger className="w-[100px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="25">25</SelectItem>
                      <SelectItem value="50">50</SelectItem>
                      <SelectItem value="100">100</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-sm text-muted-foreground">per page</p>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum
                      if (totalPages <= 5) {
                        pageNum = i + 1
                      } else if (currentPage <= 3) {
                        pageNum = i + 1
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i
                      } else {
                        pageNum = currentPage - 2 + i
                      }
                      
                      return (
                        <Button
                          key={i}
                          variant={pageNum === currentPage ? "default" : "outline"}
                          size="sm"
                          onClick={() => handlePageChange(pageNum)}
                          className="h-8 w-8 p-0"
                        >
                          {pageNum}
                        </Button>
                      )
                    })}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
  )
} 