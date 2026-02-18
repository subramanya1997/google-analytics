"use client"

import React, { useEffect, useState, useMemo, useCallback } from "react"
import type { ColumnDef, ColumnFiltersState, SortingState, PaginationState } from "@tanstack/react-table"
import { useDashboard } from "@/contexts/dashboard-context"
import { DEFAULT_PAGE_SIZE } from "@/hooks/use-pagination"
import { Task, SearchAnalysisApiTask, SearchAnalysisApiResponse, FacetItem } from "@/types"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip"
import { DataTable } from "@/components/ui/data-table"
import { DataTableFacetedFilter } from "@/components/ui/data-table-faceted-filter"
import { DataTablePagination } from "@/components/ui/data-table-pagination"
import {
  Mail, Phone, MonitorSmartphone, Search, AlertCircle,
  ChevronUp, ChevronDown, ChevronsUpDown, MapPin, ShoppingCart,
} from "lucide-react"
import { fetchSearchAnalysisTasks } from "@/lib/api-utils"

function SortHeader({ label, column }: { label: string; column: { getIsSorted: () => false | "asc" | "desc" } }) {
  const sorted = column.getIsSorted()
  return (
    <div className="flex items-center gap-2">
      {label}
      {sorted === "asc" ? (
        <ChevronUp className="h-4 w-4" />
      ) : sorted === "desc" ? (
        <ChevronDown className="h-4 w-4" />
      ) : (
        <ChevronsUpDown className="h-4 w-4 text-muted-foreground" />
      )}
    </div>
  )
}

function CustomerCell({ task }: { task: Task }) {
  return (
    <div className="space-y-1">
      <div className="font-medium text-sm truncate">{task.customer.name}</div>
      {task.customer.company && (
        <div className="text-xs text-muted-foreground truncate">{task.customer.company}</div>
      )}
      {task.metadata?.location && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <MapPin className="h-3 w-3 flex-shrink-0" />
          <span className="truncate">{task.metadata.location}</span>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
        {task.customer.email && (
          <Tooltip>
            <TooltipTrigger asChild>
              <a href={`mailto:${task.customer.email}`} className="flex items-center gap-1 hover:underline">
                <Mail className="h-3 w-3 flex-shrink-0" />
                <span className="truncate">{task.customer.email}</span>
              </a>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <p className="text-xs">{task.customer.email}</p>
            </TooltipContent>
          </Tooltip>
        )}
        {task.customer.phone?.trim() && (
          <a href={`tel:${task.customer.phone}`} className="flex items-center gap-1 hover:underline">
            <Phone className="h-3 w-3 flex-shrink-0" />
            {task.customer.phone}
          </a>
        )}
        {task.customer.office_phone?.trim() && (
          <a href={`tel:${task.customer.office_phone}`} className="flex items-center gap-1 hover:underline">
            <MonitorSmartphone className="h-3 w-3 flex-shrink-0" />
            {task.customer.office_phone}
          </a>
        )}
      </div>
    </div>
  )
}

export default function SearchAnalysisPage() {
  const { selectedLocation, dateRange } = useDashboard()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [totalCount, setTotalCount] = useState(0)
  const [searchTypeFacets, setSearchTypeFacets] = useState<FacetItem[]>([])

  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  })
  const [sorting, setSorting] = useState<SortingState>([
    { id: "attempts", desc: true },
  ])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])

  const searchTypeFilter = useMemo(() => {
    const f = columnFilters.find((f) => f.id === "searchType")
    return (f?.value as string) || undefined
  }, [columnFilters])

  const SORT_FIELD_MAP: Record<string, string> = {
    searchTerms: "search_term",
    attempts: "search_count",
  }
  const sortField = sorting[0] ? SORT_FIELD_MAP[sorting[0].id] : undefined
  const sortOrder = sorting[0] ? (sorting[0].desc ? "desc" : "asc") : undefined

  const pageCount = Math.max(1, Math.ceil(totalCount / pagination.pageSize))

  const columns = useMemo<ColumnDef<Task, unknown>[]>(() => [
    {
      id: "searchTerms",
      accessorFn: (row) => row.metadata?.searchTerms?.join(", "),
      header: ({ column }) => <SortHeader label="Search Terms" column={column} />,
      enableSorting: true,
      size: 400,
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1.5">
          {row.original.metadata?.searchTerms?.map((term, i) => (
            <Badge key={i} variant="secondary" className="text-xs px-2 py-0.5">
              <Search className="h-3 w-3 mr-1" />
              {term}
            </Badge>
          ))}
          {row.original.metadata?.hasPurchase && (
            <Badge variant="outline" className="text-xs px-2 py-0.5 ml-1">
              <ShoppingCart className="h-3 w-3 mr-1" />
              Purchased
            </Badge>
          )}
        </div>
      ),
    },
    {
      id: "customer",
      accessorFn: (row) => row.customer.name,
      header: "Customer",
      enableSorting: false,
      size: 250,
      cell: ({ row }) => <CustomerCell task={row.original} />,
    },
    {
      id: "searchType",
      accessorFn: (row) => row.metadata?.issueType,
      header: ({ column }) => (
        <div className="flex items-center gap-1">
          Type
          {searchTypeFacets.length > 0 && (
            <DataTableFacetedFilter
              column={column}
              title=""
              options={searchTypeFacets.map((f) => ({
                value: f.value,
                label: f.label,
                count: f.count,
              }))}
            />
          )}
        </div>
      ),
      enableSorting: false,
      size: 140,
      cell: ({ row }) => {
        const searchType = row.original.metadata?.issueType
        return (
          <Badge variant={searchType === "no_results" ? "destructive" : "default"}>
            {searchType === "no_results" ? (
              <>
                <AlertCircle className="h-3 w-3 mr-1" />
                No Results
              </>
            ) : (
              "No Conversion"
            )}
          </Badge>
        )
      },
    },
    {
      id: "attempts",
      accessorFn: (row) => row.metadata?.visitCount,
      header: ({ column }) => (
        <div className="flex items-center justify-center gap-2">
          <SortHeader label="Attempts" column={column} />
        </div>
      ),
      enableSorting: true,
      size: 100,
      cell: ({ row }) => (
        <div className="text-center font-medium">
          {row.original.metadata?.visitCount || 0}
        </div>
      ),
    },
    {
      accessorKey: "priority",
      header: "Priority",
      enableSorting: false,
      size: 80,
      cell: ({ row }) => (
        <Badge
          variant={
            row.original.priority === "high" ? "destructive" :
            row.original.priority === "medium" ? "default" : "secondary"
          }
          className="text-xs whitespace-nowrap"
        >
          {row.original.priority}
        </Badge>
      ),
    },
  ], [searchTypeFacets])

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetchSearchAnalysisTasks({
        selectedLocation,
        dateRange,
        page: pagination.pageIndex + 1,
        limit: pagination.pageSize,
        sortField,
        sortOrder,
        searchType: searchTypeFilter,
      })
      const data: SearchAnalysisApiResponse = await response.json()

      const transformedTasks: Task[] = (data.data || []).map((task: SearchAnalysisApiTask) => {
        const searchCount = task.search_count || 0
        const searchType = task.search_type || ""

        let priority: "high" | "medium" | "low" = "medium"
        if (searchType === "no_results") {
          if (searchCount > 3) priority = "high"
          else if (searchCount <= 1) priority = "low"
        } else {
          if (searchCount > 5) priority = "high"
          else if (searchCount <= 2) priority = "low"
        }

        const searchTerm = task.search_term || "Unknown Search"

        return {
          id: `${task.session_id}-${searchTerm}`,
          type: "search" as const,
          priority,
          title: `Search: ${searchTerm}`,
          description: `User searched for "${searchTerm}" ${task.search_count} times`,
          status: "pending" as const,
          customer: {
            id: task.user_id,
            name: task.customer_name || "Anonymous User",
            email: task.email,
            phone: task.phone,
            office_phone: task.office_phone,
          },
          metadata: {
            searchTerms: searchTerm ? searchTerm.split(", ") : [],
            issueType: task.search_type,
            visitCount: task.search_count,
          },
          createdAt: task.event_date,
          userId: task.user_id,
          sessionId: task.session_id,
        }
      })

      setTasks(transformedTasks)
      setSearchTypeFacets(data.facets?.search_types || [])
      setTotalCount(data.total || 0)
    } catch (error) {
      console.error("Error fetching search tasks:", error)
    } finally {
      setLoading(false)
    }
  }, [pagination.pageIndex, pagination.pageSize, selectedLocation, dateRange, sortField, sortOrder, searchTypeFilter])

  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      fetchData()
    }
  }, [dateRange, fetchData])

  const handleColumnFiltersChange = useCallback(
    (updaterOrValue: ColumnFiltersState | ((old: ColumnFiltersState) => ColumnFiltersState)) => {
      setColumnFilters(updaterOrValue)
      setPagination((prev) => ({ ...prev, pageIndex: 0 }))
    },
    []
  )

  const handleSortingChange = useCallback(
    (updaterOrValue: SortingState | ((old: SortingState) => SortingState)) => {
      setSorting(updaterOrValue)
      setPagination((prev) => ({ ...prev, pageIndex: 0 }))
    },
    []
  )

  return (
    <div className="space-y-4 sm:space-y-6">
      <DataTable
        columns={columns}
        data={tasks}
        pageCount={pageCount}
        pagination={pagination}
        onPaginationChange={setPagination}
        sorting={sorting}
        onSortingChange={handleSortingChange}
        columnFilters={columnFilters}
        onColumnFiltersChange={handleColumnFiltersChange}
        loading={loading}
        emptyIcon={<Search className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-muted-foreground/50" />}
        emptyMessage={columnFilters.length > 0 ? "No search tasks match your filters" : "No search analysis tasks at the moment"}
        pagination_ui={(table) => <DataTablePagination table={table} />}
      />
    </div>
  )
}
