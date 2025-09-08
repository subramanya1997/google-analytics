"use client"

import React, { useEffect, useState, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { DateRangeSelector } from "@/components/ui/date-range-selector"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
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
  Play, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  ChevronRight,
  RefreshCw,
  Download
} from "lucide-react"
import { format } from "date-fns"
import { toast } from "sonner"
import { fetchDataAvailability, fetchJobs, createIngestionJob } from "@/lib/api-utils"
import { DataAvailability, IngestionJob, JobsResponse } from "@/types"
import type { DateRange } from "react-day-picker"

export default function DataManagementPage() {
  const [dataAvailability, setDataAvailability] = useState<DataAvailability | null>(null)
  const [loadingAvailability, setLoadingAvailability] = useState(true)
  const [jobs, setJobs] = useState<IngestionJob[]>([])
  const [loadingJobs, setLoadingJobs] = useState(true)
  const [currentPage, setCurrentPage] = useState(0)
  const [totalJobs, setTotalJobs] = useState(0)
  const [jobsPerPage] = useState(10)
  
  // Ingestion form state
  const [ingestionDateRange, setIngestionDateRange] = useState<DateRange | undefined>(() => {
    const today = new Date()
    const sevenDaysAgo = new Date()
    sevenDaysAgo.setDate(today.getDate() - 7)
    return {
      from: sevenDaysAgo,
      to: today
    }
  })
  const [selectedDataTypes, setSelectedDataTypes] = useState<string[]>(["events", "users", "locations"])
  const [isSubmittingJob, setIsSubmittingJob] = useState(false)

  // Expanded job details state
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set())


  const fetchDataAvailabilityData = useCallback(async () => {
    try {
      setLoadingAvailability(true)
      
      const response = await fetchDataAvailability()
      
      if (!response.ok) {
        throw new Error('Failed to fetch data availability')
      }
      
      const data = await response.json()
      
      // API always returns combined response with both summary and breakdown
      if (data.summary && data.breakdown) {
        setDataAvailability(data.summary)
      } else {
        // Fallback for unexpected response format
        setDataAvailability(data)
      }
    } catch (error) {
      console.error('Error fetching data availability:', error)
      toast.error('Failed to load data availability')
    } finally {
      setLoadingAvailability(false)
    }
  }, [])

  const fetchJobsData = useCallback(async (page = 0) => {
    try {
      setLoadingJobs(true)
      const offset = page * jobsPerPage
      
      const response = await fetchJobs({
        limit: jobsPerPage,
        offset
      })
      
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
  }, [jobsPerPage])

  useEffect(() => {
    // PARALLEL API calls - both start simultaneously!
    Promise.all([
      fetchDataAvailabilityData(), // Always gets both summary and breakdown
      fetchJobsData()              // Also starts immediately (parallel!)
    ])
  }, [fetchDataAvailabilityData, fetchJobsData])

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
      
      const response = await createIngestionJob({
        start_date: format(ingestionDateRange.from, 'yyyy-MM-dd'),
        end_date: format(ingestionDateRange.to, 'yyyy-MM-dd'),
        data_types: selectedDataTypes
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create ingestion job')
      }

      const jobData = await response.json()
      toast.success(`Job ${jobData.job_id} has been started and is now in progress!`, {
        description: `Processing ${selectedDataTypes.join(', ')} data from ${format(ingestionDateRange.from, 'MMM d')} to ${format(ingestionDateRange.to, 'MMM d, yyyy')}`
      })
      
      // Refresh job list to show the new job
      await fetchJobsData()
      
      // Reset form to default values
      const today = new Date()
      const sevenDaysAgo = new Date()
      sevenDaysAgo.setDate(today.getDate() - 7)
      setIngestionDateRange({
        from: sevenDaysAgo,
        to: today
      })
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


  return (
    <div className="space-y-6">
      {/* Data Availability and Data Ingestion Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Data Availability Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Data Availability
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
                <div className="grid gap-4">
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
      </div>

      {/* Job History Section */}
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
                    <TableHead>Date Range</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Data Types</TableHead>
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
                            {format(new Date(job.start_date), 'MMM d')} - {format(new Date(job.end_date), 'MMM d, yyyy')}
                          </div>
                        </TableCell>
                        <TableCell>
                          {getStatusBadge(job.status)}
                        </TableCell>
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
                          <TableCell colSpan={7} className="bg-muted/30 p-0">
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
                                </div>
                                
                                {/* Records Processed */}
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
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
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
                    onClick={() => fetchJobsData(currentPage - 1)}
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
                    onClick={() => fetchJobsData(currentPage + 1)}
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
      </div>
    </div>
  )
}
