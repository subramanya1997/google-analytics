"use client"

import * as React from "react"
import {
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  type PaginationState,
  type ExpandedState,
  type Row,
  type Table as TanstackTable,
  type OnChangeFn,
  flexRender,
  getCoreRowModel,
  getExpandedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"

interface DataTableProps<TData> {
  columns: ColumnDef<TData, unknown>[]
  data: TData[]

  pageCount: number
  pagination: PaginationState
  onPaginationChange: OnChangeFn<PaginationState>

  sorting?: SortingState
  onSortingChange?: OnChangeFn<SortingState>

  columnFilters?: ColumnFiltersState
  onColumnFiltersChange?: OnChangeFn<ColumnFiltersState>

  toolbar?: (table: TanstackTable<TData>) => React.ReactNode
  pagination_ui?: (table: TanstackTable<TData>) => React.ReactNode

  renderSubComponent?: React.ComponentType<{ row: Row<TData> }>
  getRowCanExpand?: (row: Row<TData>) => boolean

  loading?: boolean
  emptyMessage?: string
  emptyIcon?: React.ReactNode
}

export function DataTable<TData>({
  columns,
  data,
  pageCount,
  pagination,
  onPaginationChange,
  sorting,
  onSortingChange,
  columnFilters,
  onColumnFiltersChange,
  toolbar,
  pagination_ui,
  renderSubComponent,
  getRowCanExpand,
  loading = false,
  emptyMessage = "No results.",
  emptyIcon,
}: DataTableProps<TData>) {
  const [expanded, setExpanded] = React.useState<ExpandedState>({})

  const table = useReactTable({
    data,
    columns,
    pageCount,
    state: {
      pagination,
      sorting,
      columnFilters,
      expanded,
    },
    onPaginationChange,
    onSortingChange,
    onColumnFiltersChange,
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowCanExpand,
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
  })

  return (
    <div className="space-y-4">
      {toolbar?.(table)}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: pagination.pageSize > 5 ? 5 : pagination.pageSize }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : table.getRowModel().rows.length === 0 ? (
        <div className="text-center py-8 sm:py-12">
          {emptyIcon}
          <p className="text-muted-foreground mt-4">{emptyMessage}</p>
        </div>
      ) : (
        <>
          <div className="rounded-md border overflow-hidden">
            <div className="overflow-x-auto">
              <Table className="min-w-full table-fixed">
                <TableHeader>
                  {table.getHeaderGroups().map((headerGroup) => (
                    <TableRow key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <TableHead
                          key={header.id}
                          style={{ width: header.column.columnDef.size ? header.getSize() : undefined }}
                          className={header.column.getCanSort() ? "cursor-pointer select-none hover:bg-muted/50" : ""}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {header.isPlaceholder
                            ? null
                            : flexRender(header.column.columnDef.header, header.getContext())}
                        </TableHead>
                      ))}
                    </TableRow>
                  ))}
                </TableHeader>
                <TableBody>
                  {table.getRowModel().rows.map((row) => {
                    const SubComponent = renderSubComponent
                    return (
                      <React.Fragment key={row.id}>
                        <TableRow
                          data-state={row.getIsSelected() && "selected"}
                          className={row.getCanExpand() ? "cursor-pointer hover:bg-muted/50" : ""}
                          onClick={row.getCanExpand() ? row.getToggleExpandedHandler() : undefined}
                        >
                          {row.getVisibleCells().map((cell) => (
                            <TableCell
                              key={cell.id}
                              style={{ width: cell.column.columnDef.size ? cell.column.getSize() : undefined }}
                              className="overflow-hidden whitespace-normal"
                            >
                              {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </TableCell>
                          ))}
                        </TableRow>
                        {row.getIsExpanded() && SubComponent && (
                          <TableRow>
                            <TableCell colSpan={row.getVisibleCells().length} className="bg-muted/30 p-0">
                              <SubComponent row={row} />
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          </div>

          {pagination_ui?.(table)}
        </>
      )}
    </div>
  )
}
