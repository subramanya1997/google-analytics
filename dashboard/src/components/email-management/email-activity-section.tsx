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
  ChevronRight,
  RefreshCw,
  Users
} from "lucide-react"
import { format } from "date-fns"
import { toast } from "sonner"
import { useIsMobile } from "@/hooks/use-mobile"
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
          <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
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

  // Format duration
  const formatDuration = (startDate?: string, endDate?: string) => {
    if (!startDate || !endDate) return 'N/A'
    
    const start = new Date(startDate)
    const end = new Date(endDate)
    const durationMs = end.getTime() - start.getTime()
    const durationMinutes = Math.floor(durationMs / (1000 * 60))
    
    if (durationMinutes < 60) {
      return `${durationMinutes}m`
    } else {
      const hours = Math.floor(durationMinutes / 60)
      const minutes = durationMinutes % 60
      return `${hours}h ${minutes}m`
    }
  }

  // Pagination calculations
  const totalJobPages = Math.ceil(totalJobs / itemsPerPage)
  const totalHistoryPages = Math.ceil(totalHistory / itemsPerPage)

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
            variant="outline"
            size="sm"
            onClick={() => {
              fetchJobsData(currentJobsPage)
              fetchHistoryData(currentHistoryPage)
              toast.success('Email activity refreshed')
            }}
            className={`flex items-center gap-1 ${isMobile ? "w-10 px-0" : ""}`}
          >
            <RefreshCw className={`h-3 w-3 ${!isMobile ? 'mr-1' : ''}`} />
            {!isMobile && 'Refresh'}
          </Button>
          <div className="h-4 w-px bg-border" />
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
            {loadingJobs ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16" />
                ))}
              </div>
            ) : jobs.length > 0 ? (
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
                      {jobs.map((job) => (
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
                                {formatDuration(job.started_at, job.completed_at)}
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
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Jobs Pagination */}
                {totalJobPages > 1 && (
                  <div className="flex items-center justify-between pt-4">
                    <p className="text-sm text-muted-foreground">
                      Showing {currentJobsPage * itemsPerPage + 1} to {Math.min((currentJobsPage + 1) * itemsPerPage, totalJobs)} of {totalJobs} jobs
                    </p>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchJobsData(currentJobsPage - 1)}
                        disabled={currentJobsPage === 0}
                      >
                        Previous
                      </Button>
                      <span className="text-sm">
                        Page {currentJobsPage + 1} of {totalJobPages}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchJobsData(currentJobsPage + 1)}
                        disabled={currentJobsPage === totalJobPages - 1}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-8">
                <Clock className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">No email jobs found</p>
              </div>
            )}
          </div>
        ) : (
          // History Tab
          <div className="space-y-4">
            {loadingHistory ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16" />
                ))}
              </div>
            ) : emailHistory.length > 0 ? (
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
                      {emailHistory.map((history) => (
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
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* History Pagination */}
                {totalHistoryPages > 1 && (
                  <div className="flex items-center justify-between pt-4">
                    <p className="text-sm text-muted-foreground">
                      Showing {currentHistoryPage * itemsPerPage + 1} to {Math.min((currentHistoryPage + 1) * itemsPerPage, totalHistory)} of {totalHistory} emails
                    </p>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchHistoryData(currentHistoryPage - 1)}
                        disabled={currentHistoryPage === 0}
                      >
                        Previous
                      </Button>
                      <span className="text-sm">
                        Page {currentHistoryPage + 1} of {totalHistoryPages}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fetchHistoryData(currentHistoryPage + 1)}
                        disabled={currentHistoryPage === totalHistoryPages - 1}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-8">
                <Mail className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">No email history found</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
