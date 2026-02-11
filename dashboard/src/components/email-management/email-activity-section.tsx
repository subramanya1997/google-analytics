"use client"

import React from "react"
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
import {
  Mail,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Users,
  Loader2
} from "lucide-react"
import { format } from "date-fns"
import { useIsMobile } from "@/hooks/use-mobile"
import { usePageNumbers, PAGE_SIZE_OPTIONS } from "@/hooks/use-pagination"
import { formatDurationBetween } from "@/lib/utils"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { EmailJob, EmailHistory } from "@/types"

interface EmailActivitySectionProps {
  activeTab: 'jobs' | 'history'
  setActiveTab: (tab: 'jobs' | 'history') => void
  
  // Jobs data
  jobs: EmailJob[]
  loadingJobs: boolean
  currentJobsPage: number
  totalJobs: number
  itemsPerPage: number
  onItemsPerPageChange: (value: string) => void
  fetchJobsData: (page: number) => Promise<void>
  
  // History data
  emailHistory: EmailHistory[]
  loadingHistory: boolean
  currentHistoryPage: number
  totalHistory: number
  fetchHistoryData: (page: number) => Promise<void>
  
  // Expanded rows
  expandedJobs: Set<string>
  expandedHistory: Set<string>
  toggleJobExpansion: (jobId: string) => void
  toggleHistoryExpansion: (historyId: string) => void
}

export function EmailActivitySection({
  activeTab,
  setActiveTab,
  jobs,
  loadingJobs,
  currentJobsPage,
  totalJobs,
  itemsPerPage,
  onItemsPerPageChange,
  fetchJobsData,
  emailHistory,
  loadingHistory,
  currentHistoryPage,
  totalHistory,
  fetchHistoryData,
  expandedJobs,
  expandedHistory,
  toggleJobExpansion,
  toggleHistoryExpansion
}: EmailActivitySectionProps) {
  const isMobile = useIsMobile()
  
  // Status badge component
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
          <CheckCircle className="h-3 w-3 mr-1" />
          Completed
        </Badge>
      case 'failed':
        return <Badge variant="destructive">
          <XCircle className="h-3 w-3 mr-1" />
          Failed
        </Badge>
      case 'processing':
        return <Badge variant="secondary" className="bg-blue-100 text-blue-800 border-blue-200">
          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          Processing
        </Badge>
      case 'queued':
        return <Badge variant="outline">
          <Clock className="h-3 w-3 mr-1" />
          Queued
        </Badge>
      case 'sent':
        return <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
          <CheckCircle className="h-3 w-3 mr-1" />
          Sent
        </Badge>
      default:
        return <Badge variant="outline">
          <AlertCircle className="h-3 w-3 mr-1" />
          {status}
        </Badge>
    }
  }


  // Pagination calculations
  const totalJobPages = Math.ceil(totalJobs / itemsPerPage)
  const totalHistoryPages = Math.ceil(totalHistory / itemsPerPage)
  // usePageNumbers is 1-indexed; currentJobsPage/currentHistoryPage are 0-indexed
  const jobPageNumbers = usePageNumbers(currentJobsPage + 1, totalJobPages)
  const historyPageNumbers = usePageNumbers(currentHistoryPage + 1, totalHistoryPages)

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="flex items-center gap-2 text-lg font-semibold">
            <Mail className="h-5 w-5" />
            Email Activity
          </h3>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant={activeTab === 'jobs' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveTab('jobs')}
            className={isMobile ? "w-10 px-0" : ""}
          >
            <Users className={`h-4 w-4 ${!isMobile ? 'mr-2' : ''}`} />
            {!isMobile && 'Jobs'}
          </Button>
          <Button
            variant={activeTab === 'history' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveTab('history')}
            className={isMobile ? "w-10 px-0" : ""}
          >
            <Mail className={`h-4 w-4 ${!isMobile ? 'mr-2' : ''}`} />
            {!isMobile && 'History'}
          </Button>
        </div>
      </div>
      
      <div>
        {activeTab === 'jobs' ? (
          // Jobs Tab
          <div className="space-y-4">
            {/* Always show table when loading, or when there are jobs */}
            {loadingJobs || jobs.length > 0 ? (
              <>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12"></TableHead>
                        <TableHead>Job ID</TableHead>
                        <TableHead>Report Date</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Branches</TableHead>
                        <TableHead>Emails</TableHead>
                        <TableHead>Duration</TableHead>
                        <TableHead>Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {loadingJobs ? (
                        // Loading skeleton rows
                        Array.from({ length: 5 }).map((_, i) => (
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
                              <Skeleton className="h-4 w-20" />
                            </TableCell>
                            <TableCell>
                              <Skeleton className="h-4 w-12" />
                            </TableCell>
                            <TableCell>
                              <Skeleton className="h-4 w-20" />
                            </TableCell>
                          </TableRow>
                        ))
                      ) : (
                        // Actual job data
                        jobs.map((job) => (
                          <React.Fragment key={job.job_id}>
                            <TableRow
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => toggleJobExpansion(job.job_id)}
                            >
                              <TableCell className="w-12">
                                <ChevronRight
                                  className={`h-4 w-4 transition-transform ${
                                    expandedJobs.has(job.job_id) ? 'rotate-90' : ''
                                  }`}
                                />
                              </TableCell>
                              <TableCell className="font-mono text-sm font-medium">
                                {job.job_id}
                              </TableCell>
                              <TableCell>
                                <div className="text-sm">
                                  {format(new Date(job.report_date), 'MMM d, yyyy')}
                                </div>
                              </TableCell>
                              <TableCell>
                                {getStatusBadge(job.status)}
                              </TableCell>
                              <TableCell>
                                <div className="text-sm">
                                  {job.target_branches.length > 0 ?
                                    `${job.target_branches.length} selected` :
                                    'All branches'
                                  }
                                </div>
                              </TableCell>
                              <TableCell>
                                <div className="text-sm">
                                  {job.emails_sent}/{job.total_emails}
                                  {job.emails_failed > 0 && (
                                    <span className="text-destructive ml-1">
                                      ({job.emails_failed} failed)
                                    </span>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell>
                                <div className="text-sm font-medium">
                                  {formatDurationBetween(job.started_at, job.completed_at)}
                                </div>
                              </TableCell>
                              <TableCell>
                                <div className="text-sm text-muted-foreground">
                                  {format(new Date(job.created_at), 'MMM d, HH:mm')}
                                </div>
                              </TableCell>
                            </TableRow>
                            {expandedJobs.has(job.job_id) && (
                              <TableRow>
                                <TableCell colSpan={8} className="bg-muted/30 p-0">
                                  <div className="px-6 py-4 border-t border-border/50">
                                    <div className="space-y-4">
                                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                          <Label className="text-sm font-medium text-muted-foreground">Processing Details</Label>
                                          <div className="mt-1 space-y-1">
                                            <p className="text-sm">Started: {job.started_at ? format(new Date(job.started_at), 'MMM d, HH:mm:ss') : 'Not started'}</p>
                                            <p className="text-sm">Completed: {job.completed_at ? format(new Date(job.completed_at), 'MMM d, HH:mm:ss') : 'Not completed'}</p>
                                          </div>
                                        </div>

                                        {job.target_branches.length > 0 && (
                                          <div>
                                            <Label className="text-sm font-medium text-muted-foreground">Target Branches</Label>
                                            <div className="mt-1 flex flex-wrap gap-1">
                                              {job.target_branches.map((branch) => (
                                                <Badge key={branch} variant="outline" className="text-xs">
                                                  {branch}
                                                </Badge>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                      </div>

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
                            )}
                          </React.Fragment>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                {/* Jobs Pagination */}
                {!loadingJobs && totalJobPages > 1 && jobs.length > 0 && (
                  <div className="flex items-center justify-between pt-4">
                    <div className="flex items-center gap-2">
                      <Select value={itemsPerPage.toString()} onValueChange={onItemsPerPageChange}>
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
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchJobsData(currentJobsPage - 1)}
                        disabled={currentJobsPage === 0}
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Previous
                      </Button>
                      <div className="flex items-center gap-1">
                        {jobPageNumbers.map((pageNum) => (
                          <Button
                            key={`job-page-${pageNum}`}
                            variant={pageNum === currentJobsPage + 1 ? "default" : "outline"}
                            size="sm"
                            onClick={() => fetchJobsData(pageNum - 1)}
                            className="h-8 w-8 p-0"
                          >
                            {pageNum}
                          </Button>
                        ))}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchJobsData(currentJobsPage + 1)}
                        disabled={currentJobsPage === totalJobPages - 1}
                      >
                        Next
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              // Show table with no data message
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12"></TableHead>
                      <TableHead>Job ID</TableHead>
                      <TableHead>Report Date</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Branches</TableHead>
                      <TableHead>Emails</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8">
                        <Clock className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                        <p className="text-muted-foreground">No email jobs found</p>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        ) : (
          // History Tab
          <div className="space-y-4">
            {/* Always show table when loading, or when there is history */}
            {loadingHistory || emailHistory.length > 0 ? (
              <>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12"></TableHead>
                        <TableHead>Branch</TableHead>
                        <TableHead>Recipient</TableHead>
                        <TableHead>Subject</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Report Date</TableHead>
                        <TableHead>Sent At</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {loadingHistory ? (
                        // Loading skeleton rows
                        Array.from({ length: 5 }).map((_, i) => (
                          <TableRow key={`skeleton-${i}`}>
                            <TableCell className="w-12">
                              <Skeleton className="h-4 w-4" />
                            </TableCell>
                            <TableCell>
                              <Skeleton className="h-4 w-16" />
                            </TableCell>
                            <TableCell>
                              <div className="space-y-1">
                                <Skeleton className="h-4 w-24" />
                                <Skeleton className="h-3 w-32" />
                              </div>
                            </TableCell>
                            <TableCell>
                              <Skeleton className="h-4 w-48" />
                            </TableCell>
                            <TableCell>
                              <Skeleton className="h-6 w-16" />
                            </TableCell>
                            <TableCell>
                              <Skeleton className="h-4 w-24" />
                            </TableCell>
                            <TableCell>
                              <Skeleton className="h-4 w-32" />
                            </TableCell>
                          </TableRow>
                        ))
                      ) : (
                        // Actual history data
                        emailHistory.map((history) => (
                          <React.Fragment key={history.id}>
                            <TableRow
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => toggleHistoryExpansion(history.id)}
                            >
                              <TableCell className="w-12">
                                <ChevronRight
                                  className={`h-4 w-4 transition-transform ${
                                    expandedHistory.has(history.id) ? 'rotate-90' : ''
                                  }`}
                                />
                              </TableCell>
                              <TableCell>
                                <Badge variant="outline" className="text-xs">
                                  {history.branch_code}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <div className="text-sm">
                                  <div className="font-medium">{history.sales_rep_name || 'Unknown'}</div>
                                  <div className="text-muted-foreground">{history.sales_rep_email}</div>
                                </div>
                              </TableCell>
                              <TableCell>
                                <div className="text-sm font-medium max-w-xs truncate">
                                  {history.subject}
                                </div>
                              </TableCell>
                              <TableCell>
                                {getStatusBadge(history.status)}
                              </TableCell>
                              <TableCell>
                                <div className="text-sm">
                                  {format(new Date(history.report_date), 'MMM d, yyyy')}
                                </div>
                              </TableCell>
                              <TableCell>
                                <div className="text-sm text-muted-foreground">
                                  {format(new Date(history.sent_at), 'MMM d, HH:mm:ss')}
                                </div>
                              </TableCell>
                            </TableRow>
                            {expandedHistory.has(history.id) && (
                              <TableRow>
                                <TableCell colSpan={7} className="bg-muted/30 p-0">
                                  <div className="px-6 py-4 border-t border-border/50">
                                    <div className="space-y-4">
                                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                          <Label className="text-sm font-medium text-muted-foreground">Email Details</Label>
                                          <div className="mt-1 space-y-1">
                                            <p className="text-sm"><strong>Job ID:</strong> {history.job_id || 'N/A'}</p>
                                            <p className="text-sm"><strong>Full Subject:</strong> {history.subject}</p>
                                            {history.smtp_response && (
                                              <p className="text-sm"><strong>SMTP Response:</strong> {history.smtp_response}</p>
                                            )}
                                          </div>
                                        </div>
                                      </div>

                                      {history.error_message && (
                                        <div>
                                          <Label className="text-sm font-medium text-destructive">Error Message</Label>
                                          <div className="mt-1 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                                            <p className="text-sm text-destructive">{history.error_message}</p>
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </TableCell>
                              </TableRow>
                            )}
                          </React.Fragment>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                {/* History Pagination */}
                {!loadingHistory && totalHistoryPages > 1 && emailHistory.length > 0 && (
                  <div className="flex items-center justify-between pt-4">
                    <div className="flex items-center gap-2">
                      <Select value={itemsPerPage.toString()} onValueChange={onItemsPerPageChange}>
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
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchHistoryData(currentHistoryPage - 1)}
                        disabled={currentHistoryPage === 0}
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Previous
                      </Button>
                      <div className="flex items-center gap-1">
                        {historyPageNumbers.map((pageNum) => (
                          <Button
                            key={`history-page-${pageNum}`}
                            variant={pageNum === currentHistoryPage + 1 ? "default" : "outline"}
                            size="sm"
                            onClick={() => fetchHistoryData(pageNum - 1)}
                            className="h-8 w-8 p-0"
                          >
                            {pageNum}
                          </Button>
                        ))}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchHistoryData(currentHistoryPage + 1)}
                        disabled={currentHistoryPage === totalHistoryPages - 1}
                      >
                        Next
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              // Show table with no data message
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12"></TableHead>
                      <TableHead>Branch</TableHead>
                      <TableHead>Recipient</TableHead>
                      <TableHead>Subject</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Report Date</TableHead>
                      <TableHead>Sent At</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        <Mail className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                        <p className="text-muted-foreground">No email history found</p>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
