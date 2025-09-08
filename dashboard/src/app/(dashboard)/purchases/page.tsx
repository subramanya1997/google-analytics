"use client"

import { useEffect, useState, useCallback } from "react"
import { useDashboard } from "@/contexts/dashboard-context"
import { fetchPurchaseTasks } from "@/lib/api-utils"
import { TaskCard } from "@/components/tasks/task-card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Task, PurchaseCartTask, PurchaseApiProduct, PurchaseApiTask, PurchaseApiResponse } from "@/types"

export default function PurchasesPage() {
  const { selectedLocation, dateRange } = useDashboard()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [itemsPerPage, setItemsPerPage] = useState(50)

  const fetchPurchaseTasksData = useCallback(async () => {
    try {
      setLoading(true)
      
      const response = await fetchPurchaseTasks({
        selectedLocation,
        dateRange,
        page: currentPage,
        limit: itemsPerPage
      })
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
          office_phone: task.office_phone,
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
      setTotalCount(data.total || 0)
      setTotalPages(data.total ? Math.ceil(data.total / itemsPerPage) : 1)
    } catch (error) {
      console.error('Error fetching purchase tasks:', error)
      setError(error instanceof Error ? error.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }, [selectedLocation, dateRange, currentPage, itemsPerPage])

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchPurchaseTasksData()
    }
  }, [dateRange, fetchPurchaseTasksData])

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const handleItemsPerPageChange = (value: string) => {
    setItemsPerPage(parseInt(value))
    setCurrentPage(1) // Reset to first page when changing items per page
  }

  return (
    <div className="space-y-4 sm:space-y-6">
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