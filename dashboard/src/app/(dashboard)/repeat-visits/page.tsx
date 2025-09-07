"use client"

import React, { useEffect, useState, useMemo, useCallback } from "react"
import { useDashboard } from "@/contexts/dashboard-context"
import { Task } from "@/types/tasks"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
import { Mail, Phone, Eye, ShoppingBag, ChevronLeft, ChevronRight, X, ChevronUp, ChevronDown, ChevronsUpDown, ExternalLink, Search } from "lucide-react"

import { buildApiQueryParams } from "@/lib/api-utils"
import { analyticsHeaders } from "@/lib/api-utils"

interface RepeatVisitApiTask {
  session_id: string
  user_id: string
  customer_name?: string
  email?: string
  phone?: string
  page_views_count: number
  products_viewed?: number
  event_date: string
  products_details?: Array<{
    title: string
    url?: string
  }>
}

interface RepeatVisitApiResponse {
  data: RepeatVisitApiTask[]
  total?: number
}

type SortField = 'customer' | 'lastVisit' | 'visitCount' | 'products' | 'priority'
type SortOrder = 'asc' | 'desc'

export default function RepeatVisitsPage() {
  const { selectedLocation, dateRange } = useDashboard()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [itemsPerPage, setItemsPerPage] = useState(50)
  
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

  const fetchRepeatVisitTasks = useCallback(async () => {
    try {
      setLoading(true)
      
      const additionalParams = {
        page: currentPage.toString(),
        limit: itemsPerPage.toString(),
        query: debouncedSearchQuery
      }

      const queryParams = buildApiQueryParams(selectedLocation, dateRange, additionalParams)
      const baseUrl = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
      const url = `${baseUrl}/api/v1/tasks/repeat-visits${queryParams}`
      
      const response = await fetch(url, { headers: analyticsHeaders() })
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
  }, [currentPage, itemsPerPage, debouncedSearchQuery, selectedLocation, dateRange])

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchRepeatVisitTasks()
    }
  }, [dateRange, fetchRepeatVisitTasks])

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const handleItemsPerPageChange = (value: string) => {
    setItemsPerPage(parseInt(value))
    setCurrentPage(1) // Reset to first page when changing items per page
  }

  // Filter and sort tasks
  const filteredAndSortedTasks = useMemo(() => {
    const filtered = tasks.filter(task => {
      // Client-side filter (priority only)
      if (priorityFilter !== "all" && task.priority !== priorityFilter) return false
      return true
    })

    // Sort the filtered tasks
    return [...filtered].sort((a, b) => {
      let compareValue = 0
      
      switch (sortField) {
        case 'customer':
          compareValue = a.customer.name.localeCompare(b.customer.name)
          break
        case 'lastVisit':
          const aDate = new Date(a.metadata?.lastVisit || 0).getTime()
          const bDate = new Date(b.metadata?.lastVisit || 0).getTime()
          compareValue = aDate - bDate
          break
        case 'visitCount':
          const aCount = a.metadata?.visitCount || 0
          const bCount = b.metadata?.visitCount || 0
          compareValue = aCount - bCount
          break
        case 'products':
          const aProducts = a.metadata?.products?.length || 0
          const bProducts = b.metadata?.products?.length || 0
          compareValue = aProducts - bProducts
          break
        case 'priority':
          const priorityOrder = { high: 3, medium: 2, low: 1 }
          compareValue = (priorityOrder[a.priority] || 0) - (priorityOrder[b.priority] || 0)
          break
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

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by customer name, email, or company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Priorities</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              className="h-10 px-3"
            >
              <X className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </div>

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
              <div className="flex items-center space-x-2">
                <p className="text-sm text-muted-foreground">
                  Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, totalCount)} of {totalCount} results
                </p>
                <Select value={itemsPerPage.toString()} onValueChange={handleItemsPerPageChange}>
                  <SelectTrigger className="h-8 w-[70px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="10">10</SelectItem>
                    <SelectItem value="25">25</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                    <SelectItem value="100">100</SelectItem>
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
          </>
        )}
      </div>
  )
} 