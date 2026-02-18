"use client"

import { useEffect, useState, useCallback } from "react"
import { usePageNumbers, PAGE_SIZE_OPTIONS, DEFAULT_PAGE_SIZE } from "@/hooks/use-pagination"
import { TaskCard } from "@/components/tasks/task-card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowDownUp, ChevronLeft, ChevronRight } from "lucide-react"
import { Task, PurchaseCartTask, CartApiProduct, CartApiTask, CartApiResponse } from "@/types"
import { useDashboard } from "@/contexts/dashboard-context"
import { fetchCartAbandonmentTasks } from "@/lib/api-utils"

export default function CartAbandonmentPage() {
  const { selectedLocation, dateRange } = useDashboard()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [itemsPerPage, setItemsPerPage] = useState(DEFAULT_PAGE_SIZE)
  const [sortValue, setSortValue] = useState("last_activity:desc")

  const [sortField, sortOrder] = sortValue.split(":") as [string, "asc" | "desc"]

  const fetchCartTasks = useCallback(async () => {
    try {
      setLoading(true)
      
      const response = await fetchCartAbandonmentTasks({
        selectedLocation,
        dateRange,
        page: currentPage,
        limit: itemsPerPage,
        sortField,
        sortOrder,
      })
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
          title: `#${task.session_id}`,
          description: `${task.items_count} items worth $${task.total_value.toFixed(2)}`,
        customer: {
          id: task.user_id,
          name: task.customer_name || 'Anonymous User',
          email: task.email,
          phone: task.phone,
          office_phone: task.office_phone,
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
  }, [selectedLocation, dateRange, currentPage, itemsPerPage, sortField, sortOrder])

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
    setCurrentPage(1)
  }

  const handleSortChange = (value: string) => {
    setSortValue(value)
    setCurrentPage(1)
  }

  const pageNumbers = usePageNumbers(currentPage, totalPages)

  const SORT_OPTIONS = [
    { value: "last_activity:desc", label: "Date (Newest)" },
    { value: "last_activity:asc", label: "Date (Oldest)" },
    { value: "total_value:desc", label: "Cart Value (High-Low)" },
    { value: "total_value:asc", label: "Cart Value (Low-High)" },
    { value: "customer_name:asc", label: "Customer (A-Z)" },
    { value: "items_count:desc", label: "Items Count (High-Low)" },
  ]

  return (
    <div className="space-y-4 sm:space-y-6">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {totalCount > 0 ? `${totalCount} abandoned carts` : ""}
          </p>
          <div className="flex items-center gap-2">
            <ArrowDownUp className="h-4 w-4 text-muted-foreground" />
            <Select value={sortValue} onValueChange={handleSortChange}>
              <SelectTrigger className="h-8 w-[200px]">
                <SelectValue placeholder="Sort by..." />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

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
                <div className="flex items-center gap-2">
                  <Select value={itemsPerPage.toString()} onValueChange={handleItemsPerPageChange}>
                    <SelectTrigger className="h-8 w-[70px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PAGE_SIZE_OPTIONS.map((size) => (
                        <SelectItem key={size} value={size.toString()}>{size}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <span className="text-sm text-muted-foreground">per page</span>
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
                    {pageNumbers.map((pageNum) => (
                      <Button
                        key={`cart-page-${pageNum}`}
                        variant={pageNum === currentPage ? "default" : "outline"}
                        size="sm"
                        onClick={() => handlePageChange(pageNum)}
                        className="h-8 w-8 p-0"
                      >
                        {pageNum}
                      </Button>
                    ))}
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