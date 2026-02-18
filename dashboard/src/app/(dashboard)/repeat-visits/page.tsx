"use client"

import React, { useEffect, useState, useMemo, useCallback } from "react"
import { useDashboard } from "@/contexts/dashboard-context"
import { usePageNumbers, PAGE_SIZE_OPTIONS, DEFAULT_PAGE_SIZE } from "@/hooks/use-pagination"
import { Task, RepeatVisitApiTask, RepeatVisitApiResponse, SortField, SortOrder } from "@/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Mail, Phone, Eye, ShoppingBag, ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ChevronsUpDown, ExternalLink } from "lucide-react"

import { fetchRepeatVisitTasks } from "@/lib/api-utils"

export default function RepeatVisitsPage() {
  const { selectedLocation, dateRange } = useDashboard()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [itemsPerPage, setItemsPerPage] = useState(DEFAULT_PAGE_SIZE)
  
  // Filter states
  const [searchQuery, setSearchQuery] = useState("")
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("")
  const [priorityFilter, setPriorityFilter] = useState<string>("all")
  
  // Sort states
  const [sortField, setSortField] = useState<SortField>('visitCount')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  
  // Expanded rows state
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery)
      setCurrentPage(1) // Reset to first page on new search
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery])

  // Map frontend SortField values to backend column names for server-side sorting.
  // 'products' and 'priority' are computed on the frontend and remain client-side only.
  const SERVER_SORT_FIELDS: Partial<Record<SortField, string>> = {
    customer: 'customer_name',
    visitCount: 'page_views_count',
    lastVisit: 'last_activity',
  }

  const fetchRepeatVisitTasksData = useCallback(async () => {
    try {
      setLoading(true)

      const backendSortField = SERVER_SORT_FIELDS[sortField]
      const response = await fetchRepeatVisitTasks({
        selectedLocation,
        dateRange,
        page: currentPage,
        limit: itemsPerPage,
        query: debouncedSearchQuery,
        sortField: backendSortField,
        sortOrder: backendSortField ? sortOrder : undefined,
      })
      const data: RepeatVisitApiResponse = await response.json()

      const transformedTasks: Task[] = (data.data || []).map((task: RepeatVisitApiTask) => {
        // Calculate priority based on page views and product views
        const pageViews = task.page_views_count || 0;
        const productsViewed = task.products_viewed || 0;
        const eventDate = new Date(task.event_date);
        const daysSinceVisit = Math.floor((Date.now() - eventDate.getTime()) / (1000 * 60 * 60 * 24));
        
        let priority: 'high' | 'medium' | 'low' = 'low';
        if ((pageViews > 10 && productsViewed > 5) || (pageViews > 15 && daysSinceVisit < 3)) {
          priority = 'high';
        } else if (pageViews > 5 || productsViewed > 2 || daysSinceVisit < 7) {
          priority = 'medium';
        }

        return {
          id: task.session_id,
          type: 'repeat_visit',
          priority,
          title: `Repeat Visit by ${task.customer_name || 'Unknown User'}`,
          description: `Viewed ${task.page_views_count} pages, ${task.products_viewed || 0} products.`,
          customer: {
            id: task.user_id,
            name: task.customer_name || 'Unknown User',
            email: task.email,
            phone: task.phone,
            office_phone: task.office_phone,
          },
                  metadata: {
          visitCount: task.page_views_count,
          productsViewed: task.products_viewed || 0,
          products: (task.products_details || []).map(product => ({
            title: product.title,
            url: product.url || null
          })),
          lastVisit: task.event_date,
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
      console.error('Error fetching repeat visit tasks:', error)
      setTasks([])
    } finally {
      setLoading(false)
    }
  }, [currentPage, itemsPerPage, debouncedSearchQuery, selectedLocation, dateRange, sortField, sortOrder])

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchRepeatVisitTasksData()
    }
  }, [dateRange, fetchRepeatVisitTasksData])

  const pageNumbers = usePageNumbers(currentPage, totalPages)

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const handleItemsPerPageChange = (value: string) => {
    setItemsPerPage(parseInt(value))
    setCurrentPage(1) // Reset to first page when changing items per page
  }

  // Filter tasks client-side (priority is a computed field, not in DB).
  // For server-sortable fields (customer, visitCount, lastVisit) the data already
  // arrives pre-sorted from the API. For client-only fields (products, priority) we
  // fall back to a local sort on the current page.
  const filteredAndSortedTasks = useMemo(() => {
    const filtered = tasks.filter(task => {
      if (priorityFilter !== "all" && task.priority !== priorityFilter) return false
      return true
    })

    const isServerSorted = sortField in SERVER_SORT_FIELDS
    if (isServerSorted) return filtered

    return [...filtered].sort((a, b) => {
      let compareValue = 0
      switch (sortField) {
        case 'products': {
          const aProducts = a.metadata?.products?.length || 0
          const bProducts = b.metadata?.products?.length || 0
          compareValue = aProducts - bProducts
          break
        }
        case 'priority': {
          const priorityOrder: Record<string, number> = { high: 3, medium: 2, low: 1 }
          compareValue = (priorityOrder[a.priority] || 0) - (priorityOrder[b.priority] || 0)
          break
        }
      }
      return sortOrder === 'asc' ? compareValue : -compareValue
    })
  }, [tasks, priorityFilter, sortField, sortOrder])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
    setCurrentPage(1)
  }

  const clearFilters = () => {
    setSearchQuery("")
    setPriorityFilter("all")
  }

  const hasActiveFilters = searchQuery || priorityFilter !== "all"

  const toggleRowExpanded = (taskId: string) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev)
      if (newSet.has(taskId)) {
        newSet.delete(taskId)
      } else {
        newSet.add(taskId)
      }
      return newSet
    })
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ChevronsUpDown className="h-4 w-4 text-muted-foreground" />
    }
    return sortOrder === 'asc' 
      ? <ChevronUp className="h-4 w-4" />
      : <ChevronDown className="h-4 w-4" />
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Unknown'
    const date = new Date(dateString)
    const days = Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24))
    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    return `${days} days ago`
  }



  return (
    <div className="space-y-6">
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : filteredAndSortedTasks.length === 0 ? (
          <div className="text-center py-12">
            <Eye className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">
              {hasActiveFilters 
                ? "No repeat visits match your filters" 
                : "No repeat visit tasks at the moment"}
            </p>
            {hasActiveFilters && (
              <Button
                variant="outline"
                size="sm"
                onClick={clearFilters}
                className="mt-4"
              >
                Clear filters
              </Button>
            )}
          </div>
        ) : (
          <>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12"></TableHead>
                    <TableHead 
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort('customer')}
                    >
                      <div className="flex items-center gap-2">
                        Customer
                        <SortIcon field="customer" />
                      </div>
                    </TableHead>
                    <TableHead 
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort('lastVisit')}
                    >
                      <div className="flex items-center gap-2">
                        Last Visit
                        <SortIcon field="lastVisit" />
                      </div>
                    </TableHead>
                    <TableHead 
                      className="text-center cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort('visitCount')}
                    >
                      <div className="flex items-center justify-center gap-2">
                        Visits
                        <SortIcon field="visitCount" />
                      </div>
                    </TableHead>
                    <TableHead 
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort('products')}
                    >
                      <div className="flex items-center gap-2">
                        Products Viewed
                        <SortIcon field="products" />
                      </div>
                    </TableHead>
                    <TableHead 
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort('priority')}
                    >
                      <div className="flex items-center gap-2">
                        Priority
                        <SortIcon field="priority" />
                      </div>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAndSortedTasks.map((task) => (
                    <React.Fragment key={task.id}>
                      <TableRow 
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => toggleRowExpanded(task.id)}
                      >
                        <TableCell className="w-12">
                          <ChevronRight 
                            className={`h-4 w-4 transition-transform ${
                              expandedRows.has(task.id) ? 'rotate-90' : ''
                            }`}
                          />
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <div className="font-medium">{task.customer.name}</div>
                            {task.customer.company && (
                              <div className="text-xs text-muted-foreground">{task.customer.company}</div>
                            )}
                            <div className="flex items-center gap-3 text-xs text-muted-foreground">
                              {task.customer.email && (
                                <a 
                                  href={`mailto:${task.customer.email}`} 
                                  className="flex items-center gap-1 hover:underline"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <Mail className="h-3 w-3" />
                                  {task.customer.email}
                                </a>
                              )}
                              {task.customer.phone && (
                                <a 
                                  href={`tel:${task.customer.phone}`} 
                                  className="flex items-center gap-1 hover:underline"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <Phone className="h-3 w-3" />
                                  {task.customer.phone}
                                </a>
                              )}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Eye className="h-4 w-4 text-muted-foreground" />
                            {formatDate(task.metadata?.lastVisit)}
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant="secondary" className="font-medium">
                            {task.metadata?.visitCount || 0}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <ShoppingBag className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm">
                              {task.metadata?.products ? task.metadata.products.length : 0} products
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={
                            task.priority === 'high' ? 'destructive' : 
                            task.priority === 'medium' ? 'default' : 'secondary'
                          }>
                            {task.priority}
                          </Badge>
                        </TableCell>
                      </TableRow>
                      {expandedRows.has(task.id) && (
                        <TableRow>
                          <TableCell colSpan={6} className="bg-muted/30 p-0">
                            <div className="px-6 py-4 border-t border-border/50">
                              <div className="space-y-4">
                                <div className="flex items-center gap-2">
                                  <ShoppingBag className="h-4 w-4 text-primary" />
                                  <h4 className="font-semibold text-sm">Products Viewed</h4>
                                  <Badge variant="secondary" className="ml-auto text-xs">
                                    {task.metadata?.products?.length || 0} items
                                  </Badge>
                                </div>
                                {task.metadata?.products && task.metadata.products.length > 0 ? (
                                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {task.metadata.products.map((product, i) => {
                                      const isObject = typeof product === 'object' && product !== null
                                      const title = isObject ? product.title : product
                                      const url = isObject ? product.url : null
                                      
                                      return (
                                        <div 
                                          key={`${task.id}-${i}`} 
                                          className="group relative overflow-hidden rounded-lg border bg-card hover:bg-accent/50 transition-all duration-200 hover:shadow-md"
                                        >
                                          {url ? (
                                            <a 
                                              href={url} 
                                              target="_blank" 
                                              rel="noopener noreferrer"
                                              className="flex items-start gap-3 p-4 h-full"
                                              onClick={(e) => e.stopPropagation()}
                                            >
                                              <div className="rounded-md bg-primary/10 p-2 group-hover:bg-primary/20 transition-colors">
                                                <ShoppingBag className="h-4 w-4 text-primary" />
                                              </div>
                                              <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors line-clamp-2">
                                                  {title}
                                                </p>
                                                {url && (
                                                  <div className="flex items-center gap-1 mt-1">
                                                    <span className="text-xs text-muted-foreground">
                                                      {new URL(url).hostname.replace('www.', '')}
                                                    </span>
                                                    <ExternalLink className="h-3 w-3 text-muted-foreground group-hover:text-primary transition-colors" />
                                                  </div>
                                                )}
                                              </div>
                                              <div className="absolute inset-x-0 bottom-0 h-1 bg-gradient-to-r from-primary/0 via-primary to-primary/0 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300" />
                                            </a>
                                          ) : (
                                            <div className="flex items-start gap-3 p-4 h-full">
                                              <div className="rounded-md bg-muted p-2">
                                                <ShoppingBag className="h-4 w-4 text-muted-foreground" />
                                              </div>
                                              <p className="text-sm text-muted-foreground line-clamp-2">{title}</p>
                                            </div>
                                          )}
                                        </div>
                                      )
                                    })}
                                  </div>
                                ) : (
                                  <div className="text-center py-8">
                                    <ShoppingBag className="h-8 w-8 mx-auto text-muted-foreground/30 mb-2" />
                                    <p className="text-sm text-muted-foreground">No products viewed in this session</p>
                                  </div>
                                )}
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between">
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
                      key={`repeat-visits-${pageNum}`}
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
          </>
        )}
      </div>
  )
} 