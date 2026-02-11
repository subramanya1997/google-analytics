"use client"

import React, { useState } from "react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ChevronLeft, ChevronRight, Clock } from "lucide-react"
import { format } from "date-fns"
import { usePageNumbers, PAGE_SIZE_OPTIONS } from "@/hooks/use-pagination"
import { formatDurationBetween } from "@/lib/utils"
import { getStatusBadge } from "./job-status-badge"
import type { IngestionJob } from "@/types"

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function JobTableSkeleton() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <TableRow key={`skeleton-${i}`}>
          <TableCell className="w-12">
            <Skeleton className="h-4 w-4" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-24" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-32" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-6 w-20" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-16" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-12" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-20" />
          </TableCell>
        </TableRow>
      ))}
    </>
  )
}

function ExpandedJobDetails({ job }: { job: IngestionJob }) {
  return (
    <TableRow>
      <TableCell colSpan={7} className="bg-muted/30 p-0">
        <div className="px-6 py-4 border-t border-border/50">
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label className="text-sm font-medium text-muted-foreground">
                  Processing Details
                </Label>
                <div className="mt-1 space-y-1">
                  <p className="text-sm">
                    Started:{" "}
                    {job.started_at
                      ? format(new Date(job.started_at), "MMM d, HH:mm:ss")
                      : "Not started"}
                  </p>
                  <p className="text-sm">
                    Completed:{" "}
                    {job.completed_at
                      ? format(new Date(job.completed_at), "MMM d, HH:mm:ss")
                      : "Not completed"}
                  </p>
                </div>
              </div>
            </div>

            {/* Records Processed */}
            {job.records_processed &&
              Object.keys(job.records_processed).length > 0 && (
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">
                    Records Processed
                  </Label>
                  <div className="mt-2">
                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-xs">Event Type</TableHead>
                            <TableHead className="text-xs text-right">Count</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {Object.entries(job.records_processed).map(
                            ([eventType, count]) => (
                              <TableRow key={eventType}>
                                <TableCell className="text-sm capitalize">
                                  {eventType.replace("_", " ")}
                                </TableCell>
                                <TableCell className="text-sm text-right font-mono">
                                  {count.toLocaleString()}
                                </TableCell>
                              </TableRow>
                            )
                          )}
                          <TableRow className="bg-muted/50">
                            <TableCell className="text-sm font-medium">Total</TableCell>
                            <TableCell className="text-sm text-right font-mono font-medium">
                              {Object.values(job.records_processed)
                                .reduce((sum, count) => sum + count, 0)
                                .toLocaleString()}
                            </TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                </div>
              )}

            {/* Error Message */}
            {job.error_message && (
              <div>
                <Label className="text-sm font-medium text-destructive">Error Message</Label>
                <div className="mt-1 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                  <p className="text-sm text-destructive">{job.error_message}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </TableCell>
    </TableRow>
  )
}

// ---------------------------------------------------------------------------
// Table header (reused for both populated and empty states)
// ---------------------------------------------------------------------------

const TABLE_COLUMNS = (
  <TableRow>
    <TableHead className="w-12"></TableHead>
    <TableHead>Job ID</TableHead>
    <TableHead>Date Range</TableHead>
    <TableHead>Status</TableHead>
    <TableHead>Data Types</TableHead>
    <TableHead>Duration</TableHead>
    <TableHead>Created</TableHead>
  </TableRow>
)

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface JobHistoryTableProps {
  jobs: IngestionJob[]
  loading: boolean
  totalJobs: number
  currentPage: number
  jobsPerPage: number
  onPageChange: (page: number) => void
  onPageSizeChange: (value: string) => void
}

export function JobHistoryTable({
  jobs,
  loading,
  totalJobs,
  currentPage,
  jobsPerPage,
  onPageChange,
  onPageSizeChange,
}: JobHistoryTableProps) {
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set())

  const totalPages = Math.ceil(totalJobs / jobsPerPage)
  // usePageNumbers is 1-indexed; currentPage here is 0-indexed
  const pageNumbers = usePageNumbers(currentPage + 1, totalPages)

  const toggleJobExpansion = (jobId: string) => {
    setExpandedJobs((prev) => {
      const next = new Set(prev)
      if (next.has(jobId)) {
        next.delete(jobId)
      } else {
        next.add(jobId)
      }
      return next
    })
  }

  // ---------- Empty state ----------
  if (!loading && jobs.length === 0) {
    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>{TABLE_COLUMNS}</TableHeader>
          <TableBody>
            <TableRow>
              <TableCell colSpan={7} className="text-center py-8">
                <Clock className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">No ingestion jobs found</p>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    )
  }

  // ---------- Populated / loading state ----------
  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>{TABLE_COLUMNS}</TableHeader>
          <TableBody>
            {loading ? (
              <JobTableSkeleton />
            ) : (
              jobs.map((job) => (
                <React.Fragment key={job.job_id}>
                  <TableRow
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => toggleJobExpansion(job.job_id)}
                  >
                    <TableCell className="w-12">
                      <ChevronRight
                        className={`h-4 w-4 transition-transform ${
                          expandedJobs.has(job.job_id) ? "rotate-90" : ""
                        }`}
                      />
                    </TableCell>
                    <TableCell className="font-mono text-sm font-medium">
                      {job.job_id}
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        {format(new Date(job.start_date), "MMM d")} -{" "}
                        {format(new Date(job.end_date), "MMM d, yyyy")}
                      </div>
                    </TableCell>
                    <TableCell>{getStatusBadge(job.status)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {job.data_types.map((type) => (
                          <Badge key={type} variant="outline" className="text-xs">
                            {type}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm font-medium">
                        {formatDurationBetween(job.started_at, job.completed_at)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm text-muted-foreground">
                        {format(new Date(job.created_at), "MMM d, HH:mm")}
                      </div>
                    </TableCell>
                  </TableRow>
                  {expandedJobs.has(job.job_id) && <ExpandedJobDetails job={job} />}
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {!loading && totalPages > 1 && jobs.length > 0 && (
        <div className="flex items-center justify-between pt-4">
          <div className="flex items-center gap-2">
            <Select value={jobsPerPage.toString()} onValueChange={onPageSizeChange}>
              <SelectTrigger className="h-8 w-[70px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZE_OPTIONS.map((size) => (
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
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 0}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <div className="flex items-center gap-1">
              {pageNumbers.map((pageNum) => (
                <Button
                  key={`job-page-${pageNum}`}
                  variant={pageNum === currentPage + 1 ? "default" : "outline"}
                  size="sm"
                  onClick={() => onPageChange(pageNum - 1)}
                  className="h-8 w-8 p-0"
                >
                  {pageNum}
                </Button>
              ))}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage === totalPages - 1}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </>
  )
}
