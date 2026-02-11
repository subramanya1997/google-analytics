"use client"

import { useEffect, useState, useMemo, useCallback } from "react"
import { useDashboard } from "@/contexts/dashboard-context"
import { usePageNumbers, PAGE_SIZE_OPTIONS, DEFAULT_PAGE_SIZE } from "@/hooks/use-pagination"
import { Task, SearchAnalysisApiTask, SearchAnalysisApiResponse, SortField, SortOrder } from "@/types"
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
import { Mail, Phone, Search, AlertCircle, ChevronLeft, ChevronRight, ShoppingCart, ChevronUp, ChevronDown, ChevronsUpDown, MapPin } from "lucide-react"

import { fetchSearchAnalysisTasks } from "@/lib/api-utils"

export default function SearchAnalysisPage() {
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

  const fetchSearchTasksData = useCallback(async () => {
    try {
      setLoading(true)

      const response = await fetchSearchAnalysisTasks({
        selectedLocation,
        dateRange,
        page: currentPage,
        limit: itemsPerPage,
        query: debouncedSearchQuery
      })
      const data: SearchAnalysisApiResponse = await response.json()

      const transformedTasks: Task[] = (data.data || []).map((task: SearchAnalysisApiTask) => {
        // Calculate priority based on search count and type
        const searchCount = task.search_count || 0;
        const searchType = task.search_type || '';
        
        let priority: 'high' | 'medium' | 'low' = 'medium';
        
        // No results searches are higher priority than unconverted searches
        if (searchType === 'no_results') {
          if (searchCount > 3) {
            priority = 'high';
          } else if (searchCount <= 1) {
            priority = 'low';
          }
        } else { // no_conversion type
          if (searchCount > 5) {
            priority = 'high';
          } else if (searchCount <= 2) {
            priority = 'low';
          }
        }
        
        const searchTerm = task.search_term || 'Unknown Search';
        
        return {
          id: `${task.session_id}-${searchTerm}`,
          type: 'search',
          priority,
          title: `Search: ${searchTerm}`,
          description: `User searched for "${searchTerm}" ${task.search_count} times`,
          customer: {
            id: task.user_id,
            name: task.customer_name || 'Unknown User',
            email: task.email,
            phone: task.phone,
            office_phone: task.office_phone,
          },
          metadata: {
            searchTerms: searchTerm ? searchTerm.split(', ') : [],
            issueType: task.search_type,
            visitCount: task.search_count,
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
      console.error('Error fetching search tasks:', error)
    } finally {
      setLoading(false)
    }
  }, [currentPage, itemsPerPage, debouncedSearchQuery, selectedLocation, dateRange])

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchSearchTasksData()
    }
  }, [dateRange, fetchSearchTasksData])

  const pageNumbers = usePageNumbers(currentPage, totalPages)

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
                      key={`search-analysis-${pageNum}`}
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