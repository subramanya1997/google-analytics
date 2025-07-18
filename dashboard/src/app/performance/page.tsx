"use client"

import { useEffect, useState, useMemo } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useDashboard } from "@/contexts/dashboard-context"
import { buildApiQueryParams } from "@/lib/api-utils"
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
import { TaskDetailSheet } from "@/components/tasks/task-detail-sheet"
import { Mail, Phone, AlertTriangle, Clock, TrendingDown, FileX, ChevronLeft, ChevronRight, X, ChevronUp, ChevronDown, ChevronsUpDown, ExternalLink, MapPin } from "lucide-react"

type SortField = 'customer' | 'type' | 'metric' | 'priority'
type SortOrder = 'asc' | 'desc'

export default function PerformancePage() {
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
  const [typeFilter, setTypeFilter] = useState<string>("all")
  
  // Sort states
  const [sortField, setSortField] = useState<SortField>('priority')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery)
      setCurrentPage(1) // Reset to first page on new search
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery])

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchPerformanceTasks()
    }
  }, [currentPage, itemsPerPage, debouncedSearchQuery, selectedLocation, dateRange])

  const fetchPerformanceTasks = async () => {
    try {
      setLoading(true)
      const qParam = debouncedSearchQuery ? `&q=${encodeURIComponent(debouncedSearchQuery)}` : ''
      const locationParam = selectedLocation ? `&locationId=${selectedLocation}` : ''
      const url = `/api/tasks/performance?page=${currentPage}&limit=${itemsPerPage}${qParam}${locationParam}`
      const response = await fetch(url)
      const data = await response.json()
      setTasks(data.tasks || [])
      setTotalPages(data.totalPages || 1)
      setTotalCount(data.total || 0)
    } catch (error) {
      console.error('Error fetching performance tasks:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCompleteTask = (taskId: string) => {
    setTasks(prev => prev.map(task => 
      task.id === taskId ? { ...task, status: 'completed' as const } : task
    ))
  }

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
      // Client-side filters (priority, type)
      if (priorityFilter !== "all" && task.priority !== priorityFilter) return false
      if (typeFilter !== "all" && task.metadata?.issueType !== typeFilter) return false
      return true
    })

    // Sort the filtered tasks
    return [...filtered].sort((a, b) => {
      let compareValue = 0
      
      switch (sortField) {
        case 'customer':
          compareValue = a.customer.name.localeCompare(b.customer.name)
          break
        case 'type':
          const aType = a.metadata?.issueType || ''
          const bType = b.metadata?.issueType || ''
          compareValue = aType.localeCompare(bType)
          break
        case 'metric':
          // Sort by description which contains the metric
          compareValue = a.description.localeCompare(b.description)
          break
        case 'priority':
          const priorityOrder = { high: 3, medium: 2, low: 1 }
          compareValue = (priorityOrder[a.priority] || 0) - (priorityOrder[b.priority] || 0)
          break
      }
      
      return sortOrder === 'asc' ? compareValue : -compareValue
    })
  }, [tasks, priorityFilter, typeFilter, sortField, sortOrder])

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
    setTypeFilter("all")
  }

  const hasActiveFilters = searchQuery || priorityFilter !== "all" || typeFilter !== "all"

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ChevronsUpDown className="h-4 w-4 text-muted-foreground" />
    }
    return sortOrder === 'asc' 
      ? <ChevronUp className="h-4 w-4" />
      : <ChevronDown className="h-4 w-4" />
  }

  const getIssueIcon = (issueType?: string) => {
    switch (issueType) {
      case 'slow_page':
        return <Clock className="h-4 w-4" />
      case 'high_bounce':
        return <TrendingDown className="h-4 w-4" />
      case 'form_abandonment':
        return <FileX className="h-4 w-4" />
      default:
        return <AlertTriangle className="h-4 w-4" />
    }
  }

  const subtitle = selectedLocation 
    ? `Address technical issues affecting user experience and conversions (Filtered by location)`
    : "Address technical issues affecting user experience and conversions"

  return (
    <DashboardLayout>
      <div className="space-y-4 sm:space-y-6">

        {/* Filters */}
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <AlertTriangle className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search issues, pages, or customer..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-3">
            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger className="w-full sm:w-[140px]">
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priorities</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>

            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Issue Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="slow_page">Slow Page</SelectItem>
                <SelectItem value="high_bounce">High Bounce</SelectItem>
                <SelectItem value="page_bounce_issue">Page Bounce Issue</SelectItem>
                <SelectItem value="form_abandonment">Form Abandonment</SelectItem>
              </SelectContent>
            </Select>

            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="h-10 px-3 self-start"
              >
                <X className="h-4 w-4 mr-1" />
                Clear
              </Button>
            )}
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : filteredAndSortedTasks.length === 0 ? (
          <div className="text-center py-8 sm:py-12">
            <AlertTriangle className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">
              {hasActiveFilters 
                ? "No performance issues match your filters" 
                : "No performance issues detected"}
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
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-[200px] sm:min-w-[250px]">
                      Page
                    </TableHead>
                    <TableHead 
                      className="cursor-pointer hover:bg-muted/50 min-w-[120px]"
                      onClick={() => handleSort('type')}
                    >
                      <div className="flex items-center gap-2">
                        Issue
                        <SortIcon field="type" />
                      </div>
                    </TableHead>
                    <TableHead 
                      className="cursor-pointer hover:bg-muted/50 min-w-[150px]"
                      onClick={() => handleSort('customer')}
                    >
                      <div className="flex items-center gap-2">
                        Customer
                        <SortIcon field="customer" />
                      </div>
                    </TableHead>
                    <TableHead 
                      className="cursor-pointer hover:bg-muted/50 min-w-[200px]"
                      onClick={() => handleSort('metric')}
                    >
                      <div className="flex items-center gap-2">
                        Details
                        <SortIcon field="metric" />
                      </div>
                    </TableHead>
                    <TableHead 
                      className="cursor-pointer hover:bg-muted/50 min-w-[100px]"
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
                    <TableRow key={task.id}>
                      <TableCell className="max-w-xs sm:max-w-md">
                        <div className="space-y-1">
                          {task.metadata?.pageTitle && task.metadata?.pageUrl ? (
                            <a 
                              href={task.metadata.pageUrl} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="font-medium text-sm text-foreground hover:text-primary flex items-center gap-1 transition-colors"
                            >
                              <span className="truncate">{task.metadata.pageTitle}</span>
                              <ExternalLink className="h-3 w-3 flex-shrink-0" />
                            </a>
                          ) : (
                            <span className="font-medium text-sm">{task.title}</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getIssueIcon(task.metadata?.issueType)}
                          <Badge variant={
                            task.metadata?.issueType === 'slow_page' ? 'destructive' : 
                            task.metadata?.issueType === 'high_bounce' ? 'default' : 
                            task.metadata?.issueType === 'page_bounce_issue' ? 'default' : 'secondary'
                          } className="text-xs">
                            {task.metadata?.issueType === 'slow_page' && 'Slow Page'}
                            {task.metadata?.issueType === 'high_bounce' && 'High Bounce'}
                            {task.metadata?.issueType === 'page_bounce_issue' && 'Page Bounce'}
                            {task.metadata?.issueType === 'form_abandonment' && 'Form Abandonment'}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="font-medium text-sm">{task.customer.name}</div>
                          {task.customer.email && (
                            <a href={`mailto:${task.customer.email}`} className="flex items-center gap-1 text-xs text-muted-foreground hover:underline">
                              <Mail className="h-3 w-3" />
                              <span className="truncate">{task.customer.email}</span>
                            </a>
                          )}
                          {task.metadata?.location && (
                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                              <MapPin className="h-3 w-3" />
                              <span className="truncate">{task.metadata.location}</span>
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <p className="text-xs sm:text-sm text-muted-foreground">{task.description}</p>
                      </TableCell>
                      <TableCell>
                        <Badge variant={
                          task.priority === 'high' ? 'destructive' : 
                          task.priority === 'medium' ? 'default' : 'secondary'
                        } className="text-xs">
                          {task.priority}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Pagination Controls */}
            <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
              <div className="flex items-center space-x-2 text-xs sm:text-sm">
                <p className="text-muted-foreground">
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
                <span className="text-muted-foreground hidden sm:inline">per page</span>
              </div>
              
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="h-8 text-xs sm:text-sm"
                >
                  <ChevronLeft className="h-4 w-4" />
                  <span className="hidden sm:inline">Previous</span>
                </Button>
                <div className="flex items-center gap-1">
                  {/* Show fewer page buttons on mobile */}
                  {Array.from({ length: Math.min(3, totalPages) }, (_, i) => {
                    let pageNum
                    if (totalPages <= 3) {
                      pageNum = i + 1
                    } else if (currentPage === 1) {
                      pageNum = i + 1
                    } else if (currentPage === totalPages) {
                      pageNum = totalPages - 2 + i
                    } else {
                      pageNum = currentPage - 1 + i
                    }
                    
                    return (
                      <Button
                        key={i}
                        variant={pageNum === currentPage ? "default" : "outline"}
                        size="sm"
                        onClick={() => handlePageChange(pageNum)}
                        className="h-8 w-8 p-0 text-xs sm:text-sm"
                      >
                        {pageNum}
                      </Button>
                    )
                  })}
                  <span className="text-xs text-muted-foreground px-1 sm:hidden">
                    of {totalPages}
                  </span>
                  {/* Show more page buttons on desktop */}
                  <div className="hidden sm:flex items-center gap-1">
                    {Array.from({ length: Math.min(5, totalPages) - 3 }, (_, i) => {
                      const pageNum = currentPage <= 3 ? 4 + i : currentPage >= totalPages - 2 ? totalPages - 4 + i : currentPage + i
                      if (pageNum > totalPages || pageNum < 1) return null
                      
                      return (
                        <Button
                          key={`desktop-${i}`}
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
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="h-8 text-xs sm:text-sm"
                >
                  <span className="hidden sm:inline">Next</span>
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  )
} 