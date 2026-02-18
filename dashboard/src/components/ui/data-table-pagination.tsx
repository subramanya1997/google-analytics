"use client"

import type { Table } from "@tanstack/react-table"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface DataTablePaginationProps<TData> {
  table: Table<TData>
  pageSizeOptions?: number[]
}

export function DataTablePagination<TData>({
  table,
  pageSizeOptions = [25, 50, 100],
}: DataTablePaginationProps<TData>) {
  const { pageIndex, pageSize } = table.getState().pagination
  const pageCount = table.getPageCount()

  const maxVisible = 5
  const half = Math.floor(maxVisible / 2)
  let start = Math.max(0, pageIndex - half)
  let end = Math.min(pageCount - 1, start + maxVisible - 1)
  if (end - start + 1 < maxVisible) {
    start = Math.max(0, end - maxVisible + 1)
  }
  const pageNumbers: number[] = []
  for (let i = start; i <= end; i++) {
    pageNumbers.push(i)
  }

  return (
    <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
      <div className="flex items-center gap-2">
        <Select
          value={pageSize.toString()}
          onValueChange={(val) => table.setPageSize(Number(val))}
        >
          <SelectTrigger className="h-8 w-[70px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {pageSizeOptions.map((size) => (
              <SelectItem key={size} value={size.toString()}>
                {size}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">per page</span>
      </div>

      <div className="flex items-center space-x-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
          className="h-8 text-xs sm:text-sm"
        >
          <ChevronLeft className="h-4 w-4" />
          <span className="hidden sm:inline">Previous</span>
        </Button>
        <div className="flex items-center gap-1">
          {pageNumbers.map((pIdx, i) => (
            <Button
              key={`page-${pIdx}`}
              variant={pIdx === pageIndex ? "default" : "outline"}
              size="sm"
              onClick={() => table.setPageIndex(pIdx)}
              className={`h-8 w-8 p-0 text-xs sm:text-sm ${
                i > 0 && i < pageNumbers.length - 1 && pIdx !== pageIndex
                  ? "hidden sm:inline-flex"
                  : ""
              }`}
            >
              {pIdx + 1}
            </Button>
          ))}
          <span className="text-xs text-muted-foreground px-1 sm:hidden">
            of {pageCount}
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
          className="h-8 text-xs sm:text-sm"
        >
          <span className="hidden sm:inline">Next</span>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
