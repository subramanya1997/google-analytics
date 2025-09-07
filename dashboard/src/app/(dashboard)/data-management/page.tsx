"use client"

import { useEffect, useState, useCallback } from "react"
import { useDashboard } from "@/contexts/dashboard-context"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { DateRangeSelector } from "@/components/ui/date-range-selector"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { 
  Database, 
  Calendar, 
  Play, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Download
} from "lucide-react"
import { format } from "date-fns"
import { toast } from "sonner"
import { analyticsHeaders, fetchFromDataService } from "@/lib/api-utils"
import type { DateRange } from "react-day-picker"

interface DataAvailability {
  earliest_date: string | null
  latest_date: string | null
  total_events: number
}

interface IngestionJob {
  job_id: string
  status: string
  start_date: string
  end_date: string
  data_types: string[]
  created_at: string
  started_at?: string
  completed_at?: string
  records_processed?: Record<string, number>
  progress?: Record<string, number>
  error_message?: string
}

interface JobsResponse {
  jobs: IngestionJob[]
  total: number
  limit: number
  offset: number
}

export default function DataManagementPage() {
  const { selectedLocation } = useDashboard()
  const [dataAvailability, setDataAvailability] = useState<DataAvailability | null>(null)
  const [dataBreakdown, setDataBreakdown] = useState<Record<string, Record<string, number>> | null>(null)
  const [loadingAvailability, setLoadingAvailability] = useState(true)
  const [jobs, setJobs] = useState<IngestionJob[]>([])
  const [loadingJobs, setLoadingJobs] = useState(true)
  const [isJobHistoryExpanded, setIsJobHistoryExpanded] = useState(false)
  const [isDataBreakdownExpanded, setIsDataBreakdownExpanded] = useState(false)
  const [currentPage, setCurrentPage] = useState(0)
  const [totalJobs, setTotalJobs] = useState(0)
  const [jobsPerPage] = useState(10)
  
  // Ingestion form state
  const [ingestionDateRange, setIngestionDateRange] = useState<DateRange | undefined>()
  const [selectedDataTypes, setSelectedDataTypes] = useState<string[]>(["events", "users", "locations"])
  const [isSubmittingJob, setIsSubmittingJob] = useState(false)

  // Expanded job details state
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set())

  // Use proxy for data service endpoints to avoid CORS issues
  const dataServiceBaseUrl = '/api/data'
  // Fallback to direct URL if proxy not available
  const directDataUrl = process.env.NEXT_PUBLIC_DATA_API_URL || ''

  const fetchDataAvailability = useCallback(async () => {
    try {
      setLoadingAvailability(true)
      
      // Try proxy first, then fallback to direct URL
      let url = `${dataServiceBaseUrl}/data-availability`
      let response: Response | null = null
      
      try {
        response = await fetch(url, { headers: analyticsHeaders() })
      } catch (error) {
        if (directDataUrl) {
          url = `${directDataUrl}/api/v1/data-availability`
          response = await fetch(url, { headers: analyticsHeaders() })
        } else {
          throw error
        }
      }
      
      if (!response.ok) {
        throw new Error('Failed to fetch data availability')
      }
      
      const data = await response.json()
      
      // API always returns combined response with both summary and breakdown
      if (data.summary && data.breakdown) {
        setDataAvailability(data.summary)
        setDataBreakdown(data.breakdown)
      } else {
        // Fallback for unexpected response format
        setDataAvailability(data)
        setDataBreakdown(null)
      }
    } catch (error) {
      console.error('Error fetching data availability:', error)
      toast.error('Failed to load data availability')
    } finally {
      setLoadingAvailability(false)
    }
  }, [dataServiceBaseUrl, directDataUrl])

  const fetchJobs = useCallback(async (page = 0) => {
    try {
      setLoadingJobs(true)
      const offset = page * jobsPerPage
      
      // Try proxy first, then fallback to direct URL
      let url = `${dataServiceBaseUrl}/jobs?limit=${jobsPerPage}&offset=${offset}`
      let response: Response | null = null
      
      try {
        response = await fetch(url, { headers: analyticsHeaders() })
      } catch (error) {
        if (directDataUrl) {
          url = `${directDataUrl}/api/v1/jobs?limit=${jobsPerPage}&offset=${offset}`
          response = await fetch(url, { headers: analyticsHeaders() })
        } else {
          throw error
        }
      }
      
      if (!response.ok) {
        throw new Error('Failed to fetch jobs')
      }
      
      const data: JobsResponse = await response.json()
      setJobs(data.jobs)
      setTotalJobs(data.total)
      setCurrentPage(page)
    } catch (error) {
      console.error('Error fetching jobs:', error)
      toast.error('Failed to load job history')
    } finally {
      setLoadingJobs(false)
    }
  }, [dataServiceBaseUrl, directDataUrl, jobsPerPage])

  useEffect(() => {
    // PARALLEL API calls - both start simultaneously!
    Promise.all([
      fetchDataAvailability(), // Always gets both summary and breakdown
      fetchJobs()              // Also starts immediately (parallel!)
    ])
  }, [fetchDataAvailability, fetchJobs])

  const handleSubmitIngestion = async () => {
    if (!ingestionDateRange?.from || !ingestionDateRange?.to) {
      toast.error('Please select a date range')
      return
    }

    if (selectedDataTypes.length === 0) {
      toast.error('Please select at least one data type')
      return
    }

    try {
      setIsSubmittingJob(true)
      
      // Try proxy first, then fallback to direct URL
      let url = `${dataServiceBaseUrl}/ingest`
      let response: Response | null = null
      
      const requestBody = {
        start_date: format(ingestionDateRange.from, 'yyyy-MM-dd'),
        end_date: format(ingestionDateRange.to, 'yyyy-MM-dd'),
        data_types: selectedDataTypes
      }
      
      const requestOptions = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...analyticsHeaders()
        },
        body: JSON.stringify(requestBody)
      }
      
      try {
        response = await fetch(url, requestOptions)
      } catch (error) {
        if (directDataUrl) {
          url = `${directDataUrl}/api/v1/ingest`
          response = await fetch(url, requestOptions)
        } else {
          throw error
        }
      }

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create ingestion job')
      }

      const jobData = await response.json()
      toast.success(`Job ${jobData.job_id} has been started and is now in progress!`, {
        description: `Processing ${selectedDataTypes.join(', ')} data from ${format(ingestionDateRange.from, 'MMM d')} to ${format(ingestionDateRange.to, 'MMM d, yyyy')}`
      })
      
      // Refresh job list to show the new job
      await fetchJobs()
      
      // Reset form
      setIngestionDateRange(undefined)
      setSelectedDataTypes(["events", "users", "locations"])
      
    } catch (error) {
      console.error('Error creating ingestion job:', error)
      toast.error(`Failed to create ingestion job: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setIsSubmittingJob(false)
    }
  }

  const handleDataTypeChange = (dataType: string, checked: boolean) => {
    if (checked) {
      setSelectedDataTypes([...selectedDataTypes, dataType])
    } else {
      setSelectedDataTypes(selectedDataTypes.filter(type => type !== dataType))
    }
  }

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
      default:
        return <Badge variant="outline">
          <AlertCircle className="h-3 w-3 mr-1" />
          {status}
        </Badge>
    }
  }

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

  const totalPages = Math.ceil(totalJobs / jobsPerPage)

  const toggleJobExpansion = (jobId: string) => {
    setExpandedJobs(prev => {
      const newSet = new Set(prev)
      if (newSet.has(jobId)) {
        newSet.delete(jobId)
      } else {
        newSet.add(jobId)
      }
      return newSet
    })
  }

  const formatEventBreakdown = (records?: Record<string, number>) => {
    if (!records || Object.keys(records).length === 0) {
      return "No event data"
    }
    
    return Object.entries(records)
      .map(([eventType, count]) => `${eventType}: ${count.toLocaleString()}`)
      .join(', ')
  }

  const toggleDataBreakdownExpansion = () => {
    // No API calls needed - data is already loaded on page load
    setIsDataBreakdownExpanded(!isDataBreakdownExpanded)
  }

  return (
    <div className="space-y-6">
      {/* Data Availability Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Data Availability
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleDataBreakdownExpansion}
              className="flex items-center gap-1"
            >
              {isDataBreakdownExpanded ? (
                <>
                  <ChevronUp className="h-4 w-4" />
                  Hide Calendar
                </>
              ) : (
                <>
                  <ChevronDown className="h-4 w-4" />
                  Show Calendar View
                </>
              )}
            </Button>
          </CardTitle>
          <CardDescription>
            View the range of data currently available in your analytics database
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingAvailability ? (
            <div className="space-y-3">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-4 w-1/4" />
            </div>
          ) : dataAvailability ? (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">Earliest Date</Label>
                  <p className="text-lg font-semibold">
                    {dataAvailability.earliest_date 
                      ? format(new Date(dataAvailability.earliest_date), 'MMM d, yyyy')
                      : 'No data'
                    }
                  </p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">Latest Date</Label>
                  <p className="text-lg font-semibold">
                    {dataAvailability.latest_date 
                      ? format(new Date(dataAvailability.latest_date), 'MMM d, yyyy')
                      : 'No data'
                    }
                  </p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">Total Events</Label>
                  <p className="text-lg font-semibold">
                    {dataAvailability.total_events.toLocaleString()}
                  </p>
                </div>
              </div>
              
              {isDataBreakdownExpanded && (
                <>
                  <Separator className="my-4" />
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-medium">Date-wise Event Breakdown</h4>
                      {loadingAvailability && (
                        <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
                      )}
                    </div>
                    {loadingAvailability ? (
                      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                          <Card key={i} className="animate-pulse">
                            <CardHeader className="pb-3">
                              <Skeleton className="h-4 w-16" />
                              <Skeleton className="h-6 w-8" />
                              <Skeleton className="h-3 w-20" />
                            </CardHeader>
                            <CardContent className="pt-0">
                              <div className="space-y-2">
                                <Skeleton className="h-3 w-full" />
                                <Skeleton className="h-3 w-3/4" />
                                <Skeleton className="h-3 w-1/2" />
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    ) : dataBreakdown ? (
                      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                        {Object.entries(dataBreakdown).slice(0, 20).map(([date, eventTypes]) => {
                          const totalEvents = Object.values(eventTypes).reduce((sum, count) => sum + count, 0)
                          const topEventType = Object.entries(eventTypes).sort(([,a], [,b]) => b - a)[0]
                          
                          return (
                            <Card key={date} className="hover:shadow-md transition-shadow cursor-pointer group">
                              <CardHeader className="pb-3">
                                <div className="flex justify-between items-start">
                                  <div>
                                    <CardTitle className="text-sm font-medium text-muted-foreground">
                                      {format(new Date(date), 'EEE')}
                                    </CardTitle>
                                    <p className="text-xl font-semibold">
                                      {format(new Date(date), 'd')}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                      {format(new Date(date), 'MMM yyyy')}
                                    </p>
                                  </div>
                                  <Badge variant="secondary" className="text-xs">
                                    {totalEvents.toLocaleString()}
                                  </Badge>
                                </div>
                              </CardHeader>
                              <CardContent className="pt-0">
                                <div className="space-y-2">
                                  <div className="flex justify-between items-center">
                                    <span className="text-xs font-medium text-emerald-600 capitalize">
                                      {topEventType?.[0]?.replace('_', ' ')}
                                    </span>
                                    <span className="text-xs font-mono">
                                      {topEventType?.[1]?.toLocaleString()}
                                    </span>
                                  </div>
                                  
                                  {Object.entries(eventTypes)
                                    .sort(([,a], [,b]) => b - a)
                                    .slice(1, 3)
                                    .map(([eventType, count]) => (
                                    <div key={eventType} className="flex justify-between items-center text-xs text-muted-foreground">
                                      <span className="capitalize">{eventType.replace('_', ' ')}</span>
                                      <span className="font-mono">{count.toLocaleString()}</span>
                                    </div>
                                  ))}
                                  
                                  {Object.keys(eventTypes).length > 3 && (
                                    <p className="text-xs text-muted-foreground text-center pt-1">
                                      +{Object.keys(eventTypes).length - 3} more types
                                    </p>
                                  )}
                                </div>
                              </CardContent>
                            </Card>
                          )
                        })}
                        {Object.keys(dataBreakdown).length > 20 && (
                          <Card className="flex items-center justify-center border-dashed">
                            <CardContent className="text-center py-8">
                              <p className="text-muted-foreground text-sm">
                                +{Object.keys(dataBreakdown).length - 20} more dates
                              </p>
                              <p className="text-xs text-muted-foreground mt-1">
                                Showing most recent 20 days
                              </p>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    ) : (
                      <p className="text-muted-foreground">Failed to load breakdown data</p>
                    )}
                  </div>
                </>
              )}
            </>
          ) : (
            <p className="text-muted-foreground">Failed to load data availability</p>
          )}
        </CardContent>
      </Card>

      {/* Data Ingestion Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Data Ingestion
          </CardTitle>
          <CardDescription>
            Ingest new data or update existing data for specific date ranges
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Date Range</Label>
            <DateRangeSelector
              dateRange={ingestionDateRange}
              onDateRangeChange={setIngestionDateRange}
            />
          </div>

          <div className="space-y-3">
            <Label>Data Types to Process</Label>
            <div className="flex flex-wrap gap-4">
              {['events', 'users', 'locations'].map((dataType) => (
                <div key={dataType} className="flex items-center space-x-2">
                  <Checkbox
                    id={dataType}
                    checked={selectedDataTypes.includes(dataType)}
                    onCheckedChange={(checked) => handleDataTypeChange(dataType, !!checked)}
                  />
                  <Label htmlFor={dataType} className="capitalize">
                    {dataType}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <Button 
            onClick={handleSubmitIngestion}
            disabled={isSubmittingJob || !ingestionDateRange?.from || !ingestionDateRange?.to}
            className="w-full"
          >
            {isSubmittingJob ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Creating Job...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Start Ingestion
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Job History Section */}
      <Card>
        <CardHeader 
          className="cursor-pointer hover:bg-muted/50 transition-colors"
          onClick={() => setIsJobHistoryExpanded(!isJobHistoryExpanded)}
        >
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Job History
                <Badge variant="outline" className="ml-2">
                  {totalJobs}
                </Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation()
                    fetchJobs(currentPage)
                  }}
                  className="ml-auto"
                  disabled={loadingJobs}
                >
                  <RefreshCw className={`h-4 w-4 ${loadingJobs ? 'animate-spin' : ''}`} />
                </Button>
              </CardTitle>
              <CardDescription>
                View the status and details of all ingestion jobs
              </CardDescription>
            </div>
            {isJobHistoryExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </div>
        </CardHeader>
        {isJobHistoryExpanded && (
            <CardContent className="pt-0">
              {loadingJobs ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-16" />
                  ))}
                </div>
              ) : jobs.length > 0 ? (
                <>
                  <div className="space-y-3">
                    {jobs.map((job) => (
                      <Card 
                        key={job.job_id}
                        className="cursor-pointer hover:shadow-md transition-all duration-200"
                      >
                        <CardHeader className="pb-3">
                          <div 
                            className="flex items-center justify-between w-full"
                            onClick={() => toggleJobExpansion(job.job_id)}
                          >
                            <div className="flex items-center gap-3">
                              {expandedJobs.has(job.job_id) ? (
                                <ChevronUp className="h-4 w-4 text-muted-foreground" />
                              ) : (
                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              )}
                              <div>
                                <h4 className="font-mono text-sm font-medium">{job.job_id}</h4>
                                <p className="text-xs text-muted-foreground">
                                  {format(new Date(job.start_date), 'MMM d')} - {format(new Date(job.end_date), 'MMM d, yyyy')}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-3">
                              {getStatusBadge(job.status)}
                              <div className="text-right">
                                <p className="text-sm font-medium">
                                  {formatDuration(job.started_at, job.completed_at)}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  {format(new Date(job.created_at), 'MMM d, HH:mm')}
                                </p>
                              </div>
                            </div>
                          </div>
                        </CardHeader>
                        
                        {expandedJobs.has(job.job_id) && (
                          <CardContent className="pt-0 border-t">
                            <div className="space-y-4">
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                  <Label className="text-sm font-medium text-muted-foreground">Data Types</Label>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {job.data_types.map((type) => (
                                      <Badge key={type} variant="outline" className="text-xs">
                                        {type}
                                      </Badge>
                                    ))}
                                  </div>
                                </div>
                                <div>
                                  <Label className="text-sm font-medium text-muted-foreground">Processing Details</Label>
                                  <div className="mt-1 space-y-1">
                                    <p className="text-sm">Started: {job.started_at ? format(new Date(job.started_at), 'MMM d, HH:mm:ss') : 'Not started'}</p>
                                    <p className="text-sm">Completed: {job.completed_at ? format(new Date(job.completed_at), 'MMM d, HH:mm:ss') : 'Not completed'}</p>
                                  </div>
                                </div>
                              </div>
                              
                              {/* Event Breakdown */}
                              {job.records_processed && Object.keys(job.records_processed).length > 0 && (
                                <div>
                                  <Label className="text-sm font-medium text-muted-foreground">Records Processed</Label>
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
                                          {Object.entries(job.records_processed).map(([eventType, count]) => (
                                            <TableRow key={eventType}>
                                              <TableCell className="text-sm capitalize">{eventType.replace('_', ' ')}</TableCell>
                                              <TableCell className="text-sm text-right font-mono">
                                                {count.toLocaleString()}
                                              </TableCell>
                                            </TableRow>
                                          ))}
                                          <TableRow className="bg-muted/50">
                                            <TableCell className="text-sm font-medium">Total</TableCell>
                                            <TableCell className="text-sm text-right font-mono font-medium">
                                              {Object.values(job.records_processed).reduce((sum, count) => sum + count, 0).toLocaleString()}
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
                          </CardContent>
                        )}
                      </Card>
                    ))}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between pt-4">
                      <p className="text-sm text-muted-foreground">
                        Showing {currentPage * jobsPerPage + 1} to {Math.min((currentPage + 1) * jobsPerPage, totalJobs)} of {totalJobs} jobs
                      </p>
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => fetchJobs(currentPage - 1)}
                          disabled={currentPage === 0}
                        >
                          Previous
                        </Button>
                        <span className="text-sm">
                          Page {currentPage + 1} of {totalPages}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => fetchJobs(currentPage + 1)}
                          disabled={currentPage === totalPages - 1}
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
                  <p className="text-muted-foreground">No ingestion jobs found</p>
                </div>
              )}
            </CardContent>
        )}
      </Card>
    </div>
  )
}
