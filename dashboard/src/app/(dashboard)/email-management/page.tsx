"use client"

import React, { useEffect, useState, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { DateRangeSelector } from "@/components/ui/date-range-selector"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Calendar } from "@/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { 
  Mail, 
  Send, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  ChevronRight,
  RefreshCw,
  Settings,
  Users,
  MapPin,
  Plus,
  Edit,
  Trash2,
  Calendar as CalendarIcon
} from "lucide-react"
import { format } from "date-fns"
import { toast } from "sonner"
import { 
  fetchEmailConfig,
  fetchBranchEmailMappings,
  updateBranchEmailMappings,
  fetchLocations,
  sendEmailReports,
  fetchEmailJobs,
  fetchEmailHistory,
} from "@/lib/api-utils"
import { 
  EmailConfigResponse,
  BranchEmailMapping,
  Location,
  EmailJob,
  EmailJobsResponse,
  EmailHistory,
  EmailHistoryResponse
} from "@/types"
import type { DateRange } from "react-day-picker"

export default function EmailManagementPage() {
  // Email Configuration State
  const [emailConfig, setEmailConfig] = useState<EmailConfigResponse | null>(null)
  const [loadingConfig, setLoadingConfig] = useState(true)
  
  // Branch Mappings State
  const [branchMappings, setBranchMappings] = useState<BranchEmailMapping[]>([])
  const [loadingMappings, setLoadingMappings] = useState(true)
  
  // Locations State
  const [locations, setLocations] = useState<Location[]>([])
  const [loadingLocations, setLoadingLocations] = useState(true)
  
  // Job History State
  const [jobs, setJobs] = useState<EmailJob[]>([])
  const [loadingJobs, setLoadingJobs] = useState(true)
  const [currentJobsPage, setCurrentJobsPage] = useState(0)
  const [totalJobs, setTotalJobs] = useState(0)
  
  // Email History State
  const [emailHistory, setEmailHistory] = useState<EmailHistory[]>([])
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [currentHistoryPage, setCurrentHistoryPage] = useState(0)
  const [totalHistory, setTotalHistory] = useState(0)
  
  const [itemsPerPage] = useState(10)
  
  // Send Report Form State
  const [sendDate, setSendDate] = useState<Date>(() => {
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    return yesterday
  })
  const [selectedBranches, setSelectedBranches] = useState<string[]>([])
  const [isSendingReports, setIsSendingReports] = useState(false)
  
  // Tab state for viewing jobs vs history
  const [activeTab, setActiveTab] = useState<'jobs' | 'history'>('jobs')
  
  // Expanded rows state
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set())
  const [expandedHistory, setExpandedHistory] = useState<Set<string>>(new Set())
  
  // Branch Mappings Management State
  const [mappingDialogOpen, setMappingDialogOpen] = useState(false)
  const [editingMapping, setEditingMapping] = useState<BranchEmailMapping | null>(null)
  const [mappingForm, setMappingForm] = useState({
    branch_code: '',
    branch_name: '',
    sales_rep_email: '',
    sales_rep_name: '',
    is_enabled: true
  })
  const [savingMapping, setSavingMapping] = useState(false)

  // Fetch Email Configuration
  const fetchEmailConfigData = useCallback(async () => {
    try {
      setLoadingConfig(true)
      const response = await fetchEmailConfig()
      
      if (!response.ok) {
        throw new Error('Failed to fetch email configuration')
      }
      
      const data: EmailConfigResponse = await response.json()
      setEmailConfig(data)
    } catch (error) {
      console.error('Error fetching email config:', error)
      toast.error('Failed to load email configuration')
    } finally {
      setLoadingConfig(false)
    }
  }, [])

  // Fetch Branch Email Mappings
  const fetchMappingsData = useCallback(async () => {
    try {
      setLoadingMappings(true)
      const response = await fetchBranchEmailMappings()
      
      if (!response.ok) {
        throw new Error('Failed to fetch branch mappings')
      }
      
      const data: BranchEmailMapping[] = await response.json()
      console.log('Fetched branch mappings:', data)
      setBranchMappings(data)
    } catch (error) {
      console.error('Error fetching branch mappings:', error)
      toast.error('Failed to load branch email mappings')
    } finally {
      setLoadingMappings(false)
    }
  }, [])

  // Fetch Locations
  const fetchLocationsData = useCallback(async () => {
    try {
      setLoadingLocations(true)
      const response = await fetchLocations()
      
      if (!response.ok) {
        throw new Error('Failed to fetch locations')
      }
      
      const data: Location[] = await response.json()
      setLocations(data)
    } catch (error) {
      console.error('Error fetching locations:', error)
      toast.error('Failed to load locations')
    } finally {
      setLoadingLocations(false)
    }
  }, [])

  // Fetch Email Jobs
  const fetchJobsData = useCallback(async (page = 0) => {
    try {
      setLoadingJobs(true)
      
      const response = await fetchEmailJobs({
        page: page + 1,
        limit: itemsPerPage
      })
      
      if (!response.ok) {
        throw new Error('Failed to fetch email jobs')
      }
      
      const data: EmailJobsResponse = await response.json()
      setJobs(data.data)
      setTotalJobs(data.total)
      setCurrentJobsPage(page)
    } catch (error) {
      console.error('Error fetching email jobs:', error)
      toast.error('Failed to load email job history')
    } finally {
      setLoadingJobs(false)
    }
  }, [itemsPerPage])

  // Fetch Email History
  const fetchHistoryData = useCallback(async (page = 0) => {
    try {
      setLoadingHistory(true)
      
      const response = await fetchEmailHistory({
        page: page + 1,
        limit: itemsPerPage
      })
      
      if (!response.ok) {
        throw new Error('Failed to fetch email history')
      }
      
      const data: EmailHistoryResponse = await response.json()
      setEmailHistory(data.data)
      setTotalHistory(data.total)
      setCurrentHistoryPage(page)
    } catch (error) {
      console.error('Error fetching email history:', error)
      toast.error('Failed to load email history')
    } finally {
      setLoadingHistory(false)
    }
  }, [itemsPerPage])

  useEffect(() => {
    // Load all data in parallel
    Promise.all([
      fetchEmailConfigData(),
      fetchMappingsData(),
      fetchLocationsData(),
      fetchJobsData(),
      fetchHistoryData()
    ])
  }, [fetchEmailConfigData, fetchMappingsData, fetchLocationsData, fetchJobsData, fetchHistoryData])

  // Handle Send Reports
  const handleSendReports = async () => {
    if (!sendDate) {
      toast.error('Please select a report date')
      return
    }

    if (!emailConfig?.configured) {
      toast.error('Email configuration is not set up. Please configure SMTP settings first.')
      return
    }

    try {
      setIsSendingReports(true)
      
      const response = await sendEmailReports({
        report_date: format(sendDate, 'yyyy-MM-dd'),
        branch_codes: selectedBranches.length > 0 ? selectedBranches : undefined
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to send email reports')
      }

      const jobData = await response.json()
      toast.success(`Email job ${jobData.job_id} has been started!`, {
        description: `Processing reports for ${selectedBranches.length > 0 ? selectedBranches.length + ' selected branches' : 'all branches'} on ${format(sendDate, 'MMM d, yyyy')}`
      })
      
      // Refresh job list
      await fetchJobsData(currentJobsPage)
      
    } catch (error) {
      console.error('Error sending reports:', error)
      toast.error(`Failed to send reports: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setIsSendingReports(false)
    }
  }

  // Handle branch selection change
  const handleBranchSelectionChange = (branchId: string, checked: boolean) => {
    if (checked) {
      setSelectedBranches([...selectedBranches, branchId])
    } else {
      setSelectedBranches(selectedBranches.filter(id => id !== branchId))
    }
  }

  // Handle branch mapping management
  const openMappingDialog = (mapping?: BranchEmailMapping) => {
    if (mapping) {
      setEditingMapping(mapping)
      setMappingForm({
        branch_code: mapping.branch_code,
        branch_name: mapping.branch_name || '',
        sales_rep_email: mapping.sales_rep_email,
        sales_rep_name: mapping.sales_rep_name || '',
        is_enabled: mapping.is_enabled
      })
    } else {
      setEditingMapping(null)
      setMappingForm({
        branch_code: '',
        branch_name: '',
        sales_rep_email: '',
        sales_rep_name: '',
        is_enabled: true
      })
    }
    setMappingDialogOpen(true)
  }

  const handleSaveMapping = async () => {
    if (!mappingForm.branch_code || !mappingForm.sales_rep_email) {
      toast.error('Branch code and sales rep email are required')
      return
    }

    try {
      setSavingMapping(true)
      
      // For updates, we need to send the full list with the updated mapping
      // For now, we'll add the new mapping to existing ones
      let updatedMappings: BranchEmailMapping[]
      
      if (editingMapping) {
        // Update existing mapping
        updatedMappings = branchMappings.map(mapping => 
          mapping.id === editingMapping.id 
            ? { ...mappingForm, id: mapping.id }
            : mapping
        )
      } else {
        // Add new mapping
        updatedMappings = [...branchMappings, mappingForm]
      }

      const response = await updateBranchEmailMappings(updatedMappings)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to save mapping')
      }

      const result = await response.json()
      toast.success(editingMapping ? 'Mapping updated successfully' : 'Mapping added successfully', {
        description: result.message
      })

      // Refresh mappings
      await fetchMappingsData()
      setMappingDialogOpen(false)
      
    } catch (error) {
      console.error('Error saving mapping:', error)
      toast.error(`Failed to save mapping: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setSavingMapping(false)
    }
  }

  const handleDeleteMapping = async (mapping: BranchEmailMapping) => {
    if (!confirm(`Are you sure you want to delete the mapping for ${mapping.branch_code}?`)) {
      return
    }

    try {
      const updatedMappings = branchMappings
        .filter(m => m.id !== mapping.id)
        .map(m => ({ ...m, is_enabled: m.id === mapping.id ? false : m.is_enabled }))

      const response = await updateBranchEmailMappings(updatedMappings)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to delete mapping')
      }

      toast.success('Mapping deleted successfully')
      await fetchMappingsData()
      
    } catch (error) {
      console.error('Error deleting mapping:', error)
      toast.error(`Failed to delete mapping: ${error instanceof Error ? error.message : String(error)}`)
    }
  }


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

  // Toggle expansion
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

  const toggleHistoryExpansion = (historyId: string) => {
    setExpandedHistory(prev => {
      const newSet = new Set(prev)
      if (newSet.has(historyId)) {
        newSet.delete(historyId)
      } else {
        newSet.add(historyId)
      }
      return newSet
    })
  }

  // Pagination calculations
  const totalJobPages = Math.ceil(totalJobs / itemsPerPage)
  const totalHistoryPages = Math.ceil(totalHistory / itemsPerPage)

  return (
    <div className="space-y-4">
      {/* Branch Email Mappings Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Users className="h-5 w-5" />
                Branch Email Mappings
              </CardTitle>
            </div>
            <Button onClick={() => openMappingDialog()} size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Add Mapping
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loadingMappings ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : branchMappings.length > 0 ? (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Branch Code</TableHead>
                    <TableHead>Branch Name</TableHead>
                    <TableHead>Sales Rep</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-20">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {branchMappings.map((mapping) => (
                    <TableRow 
                      key={mapping.id || `${mapping.branch_code}-${mapping.sales_rep_email}`}
                      className={!mapping.is_enabled ? 'opacity-60' : ''}
                    >
                      <TableCell>
                        <Badge variant="outline" className="font-mono">
                          {mapping.branch_code}
                        </Badge>
                      </TableCell>
                      <TableCell>{mapping.branch_name || 'N/A'}</TableCell>
                      <TableCell>{mapping.sales_rep_name || 'N/A'}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {mapping.sales_rep_email}
                      </TableCell>
                      <TableCell>
                        {mapping.is_enabled ? (
                          <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Active
                          </Badge>
                        ) : (
                          <Badge variant="secondary">
                            <XCircle className="h-3 w-3 mr-1" />
                            Inactive
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openMappingDialog(mapping)}
                            title="Edit mapping"
                          >
                            <Edit className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteMapping(mapping)}
                            className="text-destructive hover:text-destructive"
                            title="Delete mapping"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8">
              <Users className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground mb-4">No branch mappings configured</p>
              <Button onClick={() => openMappingDialog()}>
                <Plus className="h-4 w-4 mr-2" />
                Add First Mapping
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Email Configuration and Send Reports Section */}
      <div className="grid gap-4 lg:grid-cols-4">
        {/* Email Configuration Status - Compact */}
        <Card className="lg:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Settings className="h-4 w-4" />
              Config
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {loadingConfig ? (
              <div className="space-y-2">
                <Skeleton className="h-3 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ) : emailConfig ? (
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">SMTP</span>
                  {emailConfig.configured ? (
                    <Badge variant="default" className="bg-green-100 text-green-800 border-green-200 text-xs">
                      <CheckCircle className="h-2.5 w-2.5 mr-1" />
                      Ready
                    </Badge>
                  ) : (
                    <Badge variant="destructive" className="text-xs">
                      <XCircle className="h-2.5 w-2.5 mr-1" />
                      Setup Required
                    </Badge>
                  )}
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Mappings</span>
                  <Badge variant="outline" className="text-xs">
                    <Users className="h-2.5 w-2.5 mr-1" />
                    {branchMappings.filter(m => m.is_enabled).length}/{branchMappings.length}
                  </Badge>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">Configuration error</p>
            )}
          </CardContent>
        </Card>

        {/* Send Reports Section */}
        <Card className="lg:col-span-3">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Send className="h-5 w-5" />
              Send Email Reports
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label>Report Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-left font-normal"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {sendDate ? format(sendDate, 'PPP') : 'Select date'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={sendDate}
                    onSelect={(date) => date && setSendDate(date)}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Target Branches</Label>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => {
                    if (selectedBranches.length === locations.length) {
                      setSelectedBranches([])
                    } else {
                      setSelectedBranches(locations.map(l => l.locationId))
                    }
                  }}
                >
                  {selectedBranches.length === locations.length ? 'Deselect All' : 'Select All'}
                </Button>
              </div>
              
              {loadingLocations ? (
                <div className="space-y-2">
                  {[1, 2, 3].map(i => (
                    <Skeleton key={i} className="h-8" />
                  ))}
                </div>
              ) : (
                <div className="max-h-32 overflow-y-auto border rounded-md p-2 space-y-1">
                  {locations.map((location) => (
                    <div key={location.locationId} className="flex items-center space-x-2">
                      <Checkbox
                        id={location.locationId}
                        checked={selectedBranches.includes(location.locationId)}
                        onCheckedChange={(checked) => 
                          handleBranchSelectionChange(location.locationId, !!checked)
                        }
                      />
                      <Label htmlFor={location.locationId} className="flex items-center gap-1 text-sm cursor-pointer">
                        <MapPin className="h-3 w-3" />
                        <span className="font-mono text-xs">{location.locationId}</span>
                        <span>{location.locationName}</span>
                      </Label>
                    </div>
                  ))}
                </div>
              )}
              
              <p className="text-xs text-muted-foreground">
                {selectedBranches.length === 0 
                  ? 'None selected - will send to all branches'
                  : `${selectedBranches.length} of ${locations.length} selected`
                }
              </p>
            </div>

            <Button 
              onClick={handleSendReports}
              disabled={isSendingReports || !sendDate || !emailConfig?.configured}
              className="w-full"
            >
              {isSendingReports ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Sending Reports...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Send Email Reports
                </>
              )}
            </Button>
            
            {!emailConfig?.configured && (
              <p className="text-xs text-destructive">
                Please configure SMTP settings in the authentication service first
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Email Activity Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Mail className="h-5 w-5" />
                Email Activity
              </CardTitle>
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
                className="flex items-center gap-1"
              >
                <RefreshCw className="h-3 w-3" />
                Refresh
              </Button>
              <div className="h-4 w-px bg-border" />
              <Button
                variant={activeTab === 'jobs' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveTab('jobs')}
              >
                <Users className="h-4 w-4 mr-2" />
                Jobs
              </Button>
              <Button
                variant={activeTab === 'history' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveTab('history')}
              >
                <Mail className="h-4 w-4 mr-2" />
                History
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
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
        </CardContent>
      </Card>

      {/* Branch Mapping Management Dialog */}
      <Dialog open={mappingDialogOpen} onOpenChange={setMappingDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingMapping ? 'Edit Branch Mapping' : 'Add Branch Mapping'}
            </DialogTitle>
            <DialogDescription>
              {editingMapping ? 'Update the branch email mapping details.' : 'Create a new branch to sales representative mapping.'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label htmlFor="branch_code">Branch Code *</Label>
              <Select
                value={mappingForm.branch_code}
                onValueChange={(value) => {
                  setMappingForm({ ...mappingForm, branch_code: value })
                  // Auto-fill branch name if location exists
                  const location = locations.find(l => l.locationId === value)
                  if (location && !mappingForm.branch_name) {
                    setMappingForm(prev => ({ 
                      ...prev, 
                      branch_code: value,
                      branch_name: location.locationName 
                    }))
                  }
                }}
                disabled={!!editingMapping}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select branch" />
                </SelectTrigger>
                <SelectContent>
                  {locations.map((location) => (
                    <SelectItem key={location.locationId} value={location.locationId}>
                      {location.locationId} - {location.locationName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="branch_name">Branch Name</Label>
              <Input
                id="branch_name"
                value={mappingForm.branch_name}
                onChange={(e) => setMappingForm({ ...mappingForm, branch_name: e.target.value })}
                placeholder="Branch display name"
              />
            </div>

            <div>
              <Label htmlFor="sales_rep_email">Sales Rep Email *</Label>
              <Input
                id="sales_rep_email"
                type="email"
                value={mappingForm.sales_rep_email}
                onChange={(e) => setMappingForm({ ...mappingForm, sales_rep_email: e.target.value })}
                placeholder="sales@company.com"
              />
            </div>

            <div>
              <Label htmlFor="sales_rep_name">Sales Rep Name</Label>
              <Input
                id="sales_rep_name"
                value={mappingForm.sales_rep_name}
                onChange={(e) => setMappingForm({ ...mappingForm, sales_rep_name: e.target.value })}
                placeholder="Sales representative name"
              />
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="is_enabled"
                checked={mappingForm.is_enabled}
                onCheckedChange={(checked) => setMappingForm({ ...mappingForm, is_enabled: !!checked })}
              />
              <Label htmlFor="is_enabled" className="text-sm">
                Enable this mapping
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setMappingDialogOpen(false)}
              disabled={savingMapping}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveMapping}
              disabled={savingMapping || !mappingForm.branch_code || !mappingForm.sales_rep_email}
            >
              {savingMapping ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  {editingMapping ? 'Update' : 'Add'} Mapping
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
