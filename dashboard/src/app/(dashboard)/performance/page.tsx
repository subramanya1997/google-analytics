"use client"

import React, { useEffect, useState, useCallback, useMemo } from "react"
import type { ColumnDef, ColumnFiltersState, SortingState, PaginationState, Row } from "@tanstack/react-table"
import { useDashboard } from "@/contexts/dashboard-context"
import { fetchPerformanceTasks } from "@/lib/api-utils"
import { DEFAULT_PAGE_SIZE } from "@/hooks/use-pagination"
import { Task, PerformanceApiTask, FrequentlyBouncedPage, PerformanceApiResponse, FacetItem } from "@/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip"
import { DataTable } from "@/components/ui/data-table"
import { DataTableFacetedFilter } from "@/components/ui/data-table-faceted-filter"
import { DataTablePagination } from "@/components/ui/data-table-pagination"
import {
  Mail, Phone, MonitorSmartphone, AlertTriangle, Clock, TrendingDown,
  FileX, ChevronRight, ChevronUp, ChevronDown, ChevronsUpDown,
  ExternalLink, MapPin, Copy, Check, Info,
} from "lucide-react"

type BouncedSession = PerformanceApiTask

const ISSUE_LABEL: Record<string, string> = {
  slow_page: "Slow Page",
  high_bounce: "High Bounce",
  page_bounce_issue: "Page Bounce",
  form_abandonment: "Form Abandonment",
}

function IssueIcon({ issueType }: { issueType?: string }) {
  switch (issueType) {
    case "slow_page":
      return <Clock className="h-4 w-4" />
    case "high_bounce":
      return <TrendingDown className="h-4 w-4" />
    case "form_abandonment":
      return <FileX className="h-4 w-4" />
    default:
      return <AlertTriangle className="h-4 w-4" />
  }
}

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
      <div className="font-medium text-sm flex items-center gap-1">
        <span className="truncate">{task.customer.name}</span>
        {task.customer.name === "Anonymous Visitor" && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground cursor-help" />
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-[220px]">
              <p className="text-xs">A real user who visited the site but whose identity could not be determined.</p>
            </TooltipContent>
          </Tooltip>
        )}
        {task.customer.name === "System" && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground cursor-help" />
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-[220px]">
              <p className="text-xs">An aggregate page-level insight — not tied to a specific user. This flags pages with high overall bounce rates.</p>
            </TooltipContent>
          </Tooltip>
        )}
      </div>
      {task.customer.email && (
        <Tooltip>
          <TooltipTrigger asChild>
            <a
              href={`mailto:${task.customer.email}`}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
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
        <a
          href={`tel:${task.customer.phone}`}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          <Phone className="h-3 w-3 flex-shrink-0" />
          <span className="truncate">{task.customer.phone}</span>
        </a>
      )}
      {task.customer.office_phone?.trim() && (
        <a
          href={`tel:${task.customer.office_phone}`}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          <MonitorSmartphone className="h-3 w-3 flex-shrink-0" />
          <span className="truncate">{task.customer.office_phone}</span>
        </a>
      )}
      {task.metadata?.location && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <MapPin className="h-3 w-3 flex-shrink-0" />
          <span className="truncate">{task.metadata.location}</span>
        </div>
      )}
    </div>
  )
}

function ExpandedRow({ row }: { row: Row<Task> }) {
  const task = row.original
  const [copiedUrl, setCopiedUrl] = useState<boolean>(false)

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedUrl(true)
    setTimeout(() => setCopiedUrl(false), 2000)
  }

  return (
    <div className="px-6 py-4 border-t border-border/50">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-3">
          <div>
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Page URL</h4>
            {task.metadata?.pageUrl ? (
              <div className="flex items-start gap-2">
                <a
                  href={task.metadata.pageUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary hover:underline break-all flex-1"
                  onClick={(e) => e.stopPropagation()}
                >
                  {task.metadata.pageUrl}
                </a>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={(e) => {
                      e.stopPropagation()
                      copyToClipboard(task.metadata?.pageUrl || "")
                    }}
                  >
                    {copiedUrl ? (
                      <Check className="h-3.5 w-3.5 text-green-500" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </Button>
                  <a
                    href={task.metadata.pageUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0" asChild>
                      <span><ExternalLink className="h-3.5 w-3.5" /></span>
                    </Button>
                  </a>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No URL available</p>
            )}
          </div>
          <div>
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Description</h4>
            <p className="text-sm">{task.description}</p>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Customer</h4>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">{task.customer.name}</p>
              {task.customer.email && (
                <a
                  href={`mailto:${task.customer.email}`}
                  className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Mail className="h-3.5 w-3.5 flex-shrink-0" />
                  {task.customer.email}
                </a>
              )}
              {task.customer.phone?.trim() && (
                <a
                  href={`tel:${task.customer.phone}`}
                  className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Phone className="h-3.5 w-3.5 flex-shrink-0" />
                  {task.customer.phone}
                </a>
              )}
              {task.customer.office_phone?.trim() && (
                <a
                  href={`tel:${task.customer.office_phone}`}
                  className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MonitorSmartphone className="h-3.5 w-3.5 flex-shrink-0" />
                  {task.customer.office_phone} (office)
                </a>
              )}
              {task.metadata?.location && (
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
                  {task.metadata.location}
                </div>
              )}
            </div>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Details</h4>
            <div className="space-y-1.5 text-sm">
              {task.metadata?.issueType && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Type:</span>
                  <div className="flex items-center gap-1.5">
                    <IssueIcon issueType={task.metadata.issueType} />
                    <Badge variant={
                      task.metadata.issueType === "slow_page" ? "destructive" :
                      task.metadata.issueType === "high_bounce" ? "default" :
                      task.metadata.issueType === "page_bounce_issue" ? "default" : "secondary"
                    } className="text-xs">
                      {ISSUE_LABEL[task.metadata.issueType] ?? task.metadata.issueType}
                    </Badge>
                  </div>
                </div>
              )}
              {task.metadata?.bounceCount != null && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Bounce count:</span>
                  <Badge variant="secondary" className="text-xs">{task.metadata.bounceCount}</Badge>
                </div>
              )}
              {task.sessionId && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Session:</span>
                  <span className="font-mono text-xs">{task.sessionId}</span>
                </div>
              )}
              {task.createdAt && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Date:</span>
                  <span>{new Date(task.createdAt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function PerformancePage() {
  const { selectedLocation, dateRange } = useDashboard()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [totalCount, setTotalCount] = useState(0)
  const [issueTypeFacets, setIssueTypeFacets] = useState<FacetItem[]>([])

  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  })
  const [sorting, setSorting] = useState<SortingState>([
    { id: "details", desc: true },
  ])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])

  const issueTypeFilter = useMemo(() => {
    const f = columnFilters.find((f) => f.id === "issueType")
    return (f?.value as string) || undefined
  }, [columnFilters])

  const SORT_FIELD_MAP: Record<string, string> = {
    details: "last_activity",
    customer: "customer_name",
    page: "entry_page",
  }
  const sortField = sorting[0] ? SORT_FIELD_MAP[sorting[0].id] : undefined
  const sortOrder = sorting[0] ? (sorting[0].desc ? "desc" : "asc") : undefined

  const pageCount = Math.max(1, Math.ceil(totalCount / pagination.pageSize))

  const columns = useMemo<ColumnDef<Task, unknown>[]>(() => [
    {
      id: "expand",
      size: 32,
      enableSorting: false,
      cell: ({ row }) => (
        <ChevronRight
          className={`h-4 w-4 transition-transform ${row.getIsExpanded() ? "rotate-90" : ""}`}
        />
      ),
    },
    {
      id: "page",
      accessorFn: (row) => row.metadata?.pageTitle,
      header: ({ column }) => <SortHeader label="Page" column={column} />,
      size: 350,
      enableSorting: true,
      cell: ({ row }) => {
        const task = row.original
        const pageTitle = task.metadata?.pageTitle
        const pageUrl = task.metadata?.pageUrl

        if (pageTitle && pageUrl) {
          return (
            <Tooltip>
              <TooltipTrigger asChild>
                <a
                  href={pageUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-sm text-foreground hover:text-primary flex items-center gap-1 transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  <span className="truncate">{pageTitle}</span>
                  <ExternalLink className="h-3 w-3 flex-shrink-0 text-muted-foreground" />
                </a>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-sm">
                <p className="break-all text-xs">{pageUrl}</p>
              </TooltipContent>
            </Tooltip>
          )
        }

        return (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="font-medium text-sm truncate block">{task.title}</span>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-sm">
              <p className="break-all text-xs">{task.title}</p>
            </TooltipContent>
          </Tooltip>
        )
      },
    },
    {
      id: "issueType",
      accessorFn: (row) => row.metadata?.issueType,
      header: ({ column }) => (
        <div className="flex items-center gap-1">
          Issue
          {issueTypeFacets.length > 0 && (
            <DataTableFacetedFilter
              column={column}
              title=""
              options={issueTypeFacets.map((f) => ({
                value: f.value,
                label: f.label,
                count: f.count,
              }))}
            />
          )}
        </div>
      ),
      size: 150,
      enableSorting: false,
      cell: ({ row }) => {
        const issueType = row.original.metadata?.issueType
        return (
          <div className="flex items-center gap-1.5">
            <IssueIcon issueType={issueType} />
            <Badge
              variant={
                issueType === "slow_page" ? "destructive" :
                issueType === "high_bounce" ? "default" :
                issueType === "page_bounce_issue" ? "default" : "secondary"
              }
              className="text-xs whitespace-nowrap"
            >
              {ISSUE_LABEL[issueType ?? ""] ?? issueType}
            </Badge>
          </div>
        )
      },
    },
    {
      id: "customer",
      accessorFn: (row) => row.customer.name,
      header: ({ column }) => <SortHeader label="Customer" column={column} />,
      size: 180,
      enableSorting: true,
      cell: ({ row }) => <CustomerCell task={row.original} />,
    },
    {
      id: "details",
      accessorKey: "description",
      header: ({ column }) => <SortHeader label="Details" column={column} />,
      size: 160,
      enableSorting: true,
      cell: ({ row }) => (
        <p className="text-xs sm:text-sm text-muted-foreground truncate" title={row.original.description}>
          {row.original.description}
        </p>
      ),
    },
    {
      accessorKey: "priority",
      header: "Priority",
      size: 80,
      enableSorting: false,
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
  ], [issueTypeFacets])

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetchPerformanceTasks({
        selectedLocation,
        dateRange,
        page: pagination.pageIndex + 1,
        limit: pagination.pageSize,
        sortField,
        sortOrder,
        issueType: issueTypeFilter,
      })
      const data: PerformanceApiResponse = await response.json()

      const bouncedSessions = data.data.bounced_sessions || []
      const frequentlyBouncedPages = data.data.frequently_bounced_pages || []

      const transformedTasks: Task[] = [
        ...bouncedSessions.map((session: BouncedSession) => ({
          id: `bounced-session-${session.session_id}`,
          type: "performance" as const,
          title: `Bounced Session: ${session.session_id}`,
          description: `User session with a single page view. Entry page: ${session.entry_page}`,
          priority: "high" as const,
          status: "pending" as const,
          customer: {
            id: session.user_id,
            name: session.customer_name || "Anonymous Visitor",
            email: session.email,
            phone: session.phone,
            office_phone: session.office_phone,
          },
          metadata: {
            issueType: "high_bounce",
            pageUrl: session.entry_page,
            pageTitle: session.entry_page,
            location: session.location_id,
          },
          createdAt: session.event_date,
          userId: session.user_id,
          sessionId: session.session_id,
        })),
        ...frequentlyBouncedPages.map((page: FrequentlyBouncedPage) => ({
          id: `bounced-page-${page.entry_page}`,
          type: "performance" as const,
          title: `Frequently Bounced Page: ${page.entry_page}`,
          description: `This page has a high bounce rate with ${page.bounce_count} bounces.`,
          priority: "high" as const,
          status: "pending" as const,
          customer: {
            id: "system",
            name: "System",
            email: undefined,
            phone: undefined,
            office_phone: undefined,
          },
          metadata: {
            issueType: "page_bounce_issue",
            pageUrl: page.entry_page,
            pageTitle: page.entry_page,
            bounceCount: page.bounce_count,
          },
          createdAt: new Date().toISOString(),
        })),
      ]

      setTasks(transformedTasks)
      setIssueTypeFacets(data.facets?.issue_types || [])
      setTotalCount(data.total || 0)
    } catch (error) {
      console.error("Error fetching performance tasks:", error)
    } finally {
      setLoading(false)
    }
  }, [pagination.pageIndex, pagination.pageSize, selectedLocation, dateRange, sortField, sortOrder, issueTypeFilter])

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

  const hasActiveFilters = columnFilters.length > 0

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
        emptyIcon={<AlertTriangle className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-muted-foreground/50" />}
        emptyMessage={hasActiveFilters ? "No performance issues match your filters" : "No performance issues detected"}
        getRowCanExpand={() => true}
        renderSubComponent={ExpandedRow}
        pagination_ui={(table) => <DataTablePagination table={table} />}
      />
    </div>
  )
}
