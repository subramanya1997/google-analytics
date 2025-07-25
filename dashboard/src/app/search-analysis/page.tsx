"use client"

import { useEffect, useState, useMemo, useCallback } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useDashboard } from "@/contexts/dashboard-context"
import { Task } from "@/types/tasks"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Checkbox } from "@/components/ui/checkbox"
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
import { Mail, Phone, Search, AlertCircle, ChevronLeft, ChevronRight, X, ShoppingCart, ChevronUp, ChevronDown, ChevronsUpDown, MapPin } from "lucide-react"
import { format } from "date-fns"

type SortField = 'searchTerms' | 'customer' | 'type' | 'attempts' | 'priority'
type SortOrder = 'asc' | 'desc'

export default function SearchAnalysisPage() {
  const { selectedLocation, dateRange } = useDashboard()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [itemsPerPage, setItemsPerPage] = useState(50)
  const [includeConverted, setIncludeConverted] = useState(false)
  
  // Filter states
  const [searchQuery, setSearchQuery] = useState("")
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("")
  const [priorityFilter, setPriorityFilter] = useState<string>("all")
  const [typeFilter, setTypeFilter] = useState<string>("all")
  
  // Sort states
  const [sortField, setSortField] = useState<SortField>('attempts')
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
      fetchSearchTasks()
    }
  }, [currentPage, itemsPerPage, includeConverted, debouncedSearchQuery, selectedLocation, dateRange])

  const fetchSearchTasks = async () => {
    try {
      setLoading(true)
      const qParam = debouncedSearchQuery ? `&q=${encodeURIComponent(debouncedSearchQuery)}` : ''
      const locationParam = selectedLocation ? `&locationId=${selectedLocation}` : ''
      const dateParams = dateRange?.from && dateRange?.to 
        ? `&startDate=${format(dateRange.from, 'yyyy-MM-dd')}&endDate=${format(dateRange.to, 'yyyy-MM-dd')}`
        : ''
      const url = `/api/tasks/search-analysis?page=${currentPage}&limit=${itemsPerPage}&includeConverted=${includeConverted}${qParam}${locationParam}${dateParams}`
      const response = await fetch(url)
      const data = await response.json()
      setTasks(data.tasks || [])
      setTotalPages(data.totalPages || 1)
      setTotalCount(data.total || 0)
    } catch (error) {
      console.error('Error fetching search tasks:', error)
    } finally {
      setLoading(false)
    }
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const handleItemsPerPageChange = (value: string) => {
    setItemsPerPage(parseInt(value))
    setCurrentPage(1) // Reset to first page when changing items per page
  }

  const handleIncludeConvertedChange = (checked: boolean) => {
    setIncludeConverted(checked)
    setCurrentPage(1) // Reset to first page when changing filter
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
        case 'searchTerms':
          const aTerms = a.metadata?.searchTerms?.[0] || ''
          const bTerms = b.metadata?.searchTerms?.[0] || ''
          compareValue = aTerms.localeCompare(bTerms)
          break
        case 'customer':
          compareValue = a.customer.name.localeCompare(b.customer.name)
          break
        case 'type':
          const aType = a.metadata?.issueType || ''
          const bType = b.metadata?.issueType || ''
          compareValue = aType.localeCompare(bType)
          break
        case 'attempts':
          const aAttempts = a.metadata?.visitCount || 0
          const bAttempts = b.metadata?.visitCount || 0
          compareValue = aAttempts - bAttempts
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

  const subtitle = selectedLocation 
    ? `Follow up with customers who searched but didn't find what they needed (Filtered by location)`
    : "Follow up with customers who searched but didn't find what they needed"

  return (
    <DashboardLayout>
      <div className="space-y-6">

        {/* Filters */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search for products (e.g. 'bay vent', 'pvc')..."
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

            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="no_results">No Results</SelectItem>
                <SelectItem value="no_conversion">No Conversion</SelectItem>
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

          <div className="flex items-center space-x-2">
            <Checkbox 
              id="include-converted" 
              checked={includeConverted}
              onCheckedChange={handleIncludeConvertedChange}
            />
            <label
              htmlFor="include-converted"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              Include active searches from sessions that resulted in purchases
            </label>
            <span className="text-xs text-muted-foreground">
              (All "no results" searches are always shown)
            </span>
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : filteredAndSortedTasks.length === 0 ? (
          <div className="text-center py-12">
            <Search className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">
              {hasActiveFilters 
                ? "No search tasks match your filters" 
                : "No search analysis tasks at the moment"}
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
                    <TableHead 
                      className="w-[250px] cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort('searchTerms')}
                    >
                      <div className="flex items-center gap-2">
                        Search Terms
                        <SortIcon field="searchTerms" />
                      </div>
                    </TableHead>
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
                      onClick={() => handleSort('type')}
                    >
                      <div className="flex items-center gap-2">
                        Type
                        <SortIcon field="type" />
                      </div>
                    </TableHead>
                    <TableHead 
                      className="text-center cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort('attempts')}
                    >
                      <div className="flex items-center justify-center gap-2">
                        Attempts
                        <SortIcon field="attempts" />
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
                    <TableRow key={task.id}>
                      <TableCell className="font-medium">
                        <div className="flex flex-wrap gap-1">
                          {task.metadata?.searchTerms?.map((term, i) => (
                            <Badge key={i} variant="secondary" className="text-xs">
                              <Search className="h-3 w-3 mr-1" />
                              {term}
                            </Badge>
                          ))}
                          {task.metadata?.hasPurchase && (
                            <Badge variant="outline" className="text-xs ml-2">
                              <ShoppingCart className="h-3 w-3 mr-1" />
                              Purchased
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="font-medium">{task.customer.name}</div>
                          {task.customer.company && (
                            <div className="text-xs text-muted-foreground">{task.customer.company}</div>
                          )}
                          {task.metadata?.location && (
                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                              <MapPin className="h-3 w-3" />
                              {task.metadata.location}
                            </div>
                          )}
                          <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            {task.customer.email && (
                              <a href={`mailto:${task.customer.email}`} className="flex items-center gap-1 hover:underline">
                                <Mail className="h-3 w-3" />
                                {task.customer.email}
                              </a>
                            )}
                            {task.customer.phone && (
                              <a href={`tel:${task.customer.phone}`} className="flex items-center gap-1 hover:underline">
                                <Phone className="h-3 w-3" />
                                {task.customer.phone}
                              </a>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={task.metadata?.issueType === 'no_results' ? 'destructive' : 'default'}>
                          {task.metadata?.issueType === 'no_results' ? (
                            <>
                              <AlertCircle className="h-3 w-3 mr-1" />
                              No Results
                            </>
                          ) : (
                            'No Conversion'
                          )}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center font-medium">
                        {task.metadata?.visitCount || 0}
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
    </DashboardLayout>
  )
} 