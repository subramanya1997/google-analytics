"use client"

import * as React from "react"
import type { Column } from "@tanstack/react-table"
import { CheckIcon, ListFilter, PlusCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Separator } from "@/components/ui/separator"

interface FacetOption {
  value: string
  label: string
  count?: number
  icon?: React.ComponentType<{ className?: string }>
}

interface DataTableFacetedFilterProps<TData, TValue> {
  column?: Column<TData, TValue>
  title: string
  options: FacetOption[]
}

export function DataTableFacetedFilter<TData, TValue>({
  column,
  title,
  options,
}: DataTableFacetedFilterProps<TData, TValue>) {
  const filterValue = column?.getFilterValue()
  const selectedValues = new Set(
    Array.isArray(filterValue) ? filterValue as string[] : filterValue ? [filterValue as string] : []
  )

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant={selectedValues.size > 0 ? "secondary" : "ghost"}
          size="sm"
          className={cn("h-7", title ? "border-dashed border" : "h-6 w-6 p-0")}
        >
          {title ? (
            <PlusCircle className="mr-2 h-4 w-4" />
          ) : (
            <ListFilter className={cn("h-3.5 w-3.5", selectedValues.size > 0 && "text-primary")} />
          )}
          {title && <span>{title}</span>}
          {title && selectedValues.size > 0 && (
            <>
              <Separator orientation="vertical" className="mx-2 h-4" />
              <div className="flex gap-1">
                {options
                  .filter((opt) => selectedValues.has(opt.value))
                  .map((opt) => (
                    <Badge key={opt.value} variant="secondary" className="rounded-sm px-1 font-normal text-xs">
                      {opt.label}
                    </Badge>
                  ))}
              </div>
            </>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[220px] p-0" align="start">
        <div className="p-2 space-y-1">
          {options.map((option) => {
            const isSelected = selectedValues.has(option.value)
            return (
              <button
                key={option.value}
                className={cn(
                  "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground transition-colors",
                  isSelected && "bg-accent"
                )}
                onClick={() => {
                  const next = new Set(selectedValues)
                  if (isSelected) {
                    next.delete(option.value)
                  } else {
                    next.clear()
                    next.add(option.value)
                  }
                  const values = Array.from(next)
                  column?.setFilterValue(values.length ? values[0] : undefined)
                }}
              >
                <div
                  className={cn(
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border border-primary",
                    isSelected ? "bg-primary text-primary-foreground" : "opacity-50 [&_svg]:invisible"
                  )}
                >
                  <CheckIcon className="h-3 w-3" />
                </div>
                {option.icon && <option.icon className="h-4 w-4 text-muted-foreground" />}
                <span className="flex-1 text-left">{option.label}</span>
                {option.count != null && (
                  <span className="ml-auto text-xs tabular-nums text-muted-foreground">
                    {option.count}
                  </span>
                )}
              </button>
            )
          })}
        </div>
        {selectedValues.size > 0 && (
          <>
            <Separator />
            <div className="p-1">
              <button
                className="w-full rounded-sm px-2 py-1.5 text-sm text-center hover:bg-accent cursor-pointer transition-colors"
                onClick={() => column?.setFilterValue(undefined)}
              >
                Clear filter
              </button>
            </div>
          </>
        )}
      </PopoverContent>
    </Popover>
  )
}
