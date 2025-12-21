"use client"

import React, { useEffect, useState, useCallback } from "react"
import { format } from "date-fns"
import { toast } from "sonner"
import {
  fetchEmailConfig,
  fetchBranchEmailMappings,
  updateBranchEmailMapping,
  createBranchEmailMapping,
  deleteBranchEmailMapping,
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
  EmailHistoryResponse,
  SendReportsRequest
} from "@/types"
import {
  BranchMappingsTable,
  SendReportsDialog,
  EmailActivitySection,
  BranchMappingDialog
} from "@/components/email-management"
import { Scheduler } from "@/components/scheduler"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

export default function EmailManagementPage() {
  // Email Configuration State
  const [emailConfig, setEmailConfig] = useState<EmailConfigResponse | null>(null)
  
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

  // Send Reports Dialog State
  const [sendReportsDialogOpen, setSendReportsDialogOpen] = useState(false)

  // Delete Confirmation Dialog State
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [mappingToDelete, setMappingToDelete] = useState<BranchEmailMapping | null>(null)

  // Scheduler State
  const [schedulerOpen, setSchedulerOpen] = useState(false)

  // Fetch Email Configuration
  const fetchEmailConfigData = useCallback(async () => {
    try {
      const response = await fetchEmailConfig()
      
      if (!response.ok) {
        throw new Error('Failed to fetch email configuration')
      }
      
      const data: EmailConfigResponse = await response.json()
      setEmailConfig(data)
    } catch (error) {
      console.error('Error fetching email config:', error)
      toast.error('Failed to load email configuration')
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

  // Listen for the custom events from layout wrapper
  useEffect(() => {
    const handleOpenMappingDialog = () => {
      openMappingDialog()
    }

    const handleOpenSendReportsDialog = () => {
      setSendReportsDialogOpen(true)
    }

    const handleOpenScheduler = () => {
      setSchedulerOpen(true)
    }

    const handleRefreshEmail = () => {
      // Refresh all email management data
      fetchEmailConfigData()
      fetchMappingsData()
      fetchLocationsData()
      fetchJobsData(currentJobsPage)
      fetchHistoryData(currentHistoryPage)
      toast.success('Email management data refreshed')
    }

    window.addEventListener('openMappingDialog', handleOpenMappingDialog)
    window.addEventListener('openSendReportsDialog', handleOpenSendReportsDialog)
    window.addEventListener('openEmailReportsScheduler', handleOpenScheduler)
    window.addEventListener('refreshEmailManagement', handleRefreshEmail)

    return () => {
      window.removeEventListener('openMappingDialog', handleOpenMappingDialog)
      window.removeEventListener('openSendReportsDialog', handleOpenSendReportsDialog)
      window.removeEventListener('openEmailReportsScheduler', handleOpenScheduler)
      window.removeEventListener('refreshEmailManagement', handleRefreshEmail)
    }
  }, [currentJobsPage, currentHistoryPage, fetchEmailConfigData, fetchHistoryData, fetchJobsData, fetchLocationsData, fetchMappingsData])

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
      
      const requestData: SendReportsRequest = {
        report_date: format(sendDate, 'yyyy-MM-dd'),
        branch_codes: selectedBranches.length > 0 ? selectedBranches : undefined
      }

      const response = await sendEmailReports(requestData)

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
      
      let response: Response
      
      if (editingMapping && editingMapping.id) {
        // Update existing mapping
        response = await updateBranchEmailMapping(editingMapping.id, mappingForm)
      } else {
        // Create new mapping
        response = await createBranchEmailMapping(mappingForm)
      }

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
    setMappingToDelete(mapping)
    setDeleteDialogOpen(true)
  }

  const confirmDeleteMapping = async () => {
    if (!mappingToDelete) return

    if (!mappingToDelete.id) {
      toast.error('Cannot delete mapping: missing ID')
      setDeleteDialogOpen(false)
      return
    }

    try {
      const response = await deleteBranchEmailMapping(mappingToDelete.id)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to delete mapping')
      }

      toast.success('Mapping deleted successfully')
      await fetchMappingsData()
      setDeleteDialogOpen(false)
      setMappingToDelete(null)
      
    } catch (error) {
      console.error('Error deleting mapping:', error)
      toast.error(`Failed to delete mapping: ${error instanceof Error ? error.message : String(error)}`)
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


  return (
    <div className="space-y-4">
      {/* Branch Email Mappings Section */}
      <BranchMappingsTable
        branchMappings={branchMappings}
        loadingMappings={loadingMappings}
        onEditMapping={openMappingDialog}
        onDeleteMapping={handleDeleteMapping}
      />


      {/* Email Activity Section */}
      <EmailActivitySection
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        jobs={jobs}
        loadingJobs={loadingJobs}
        currentJobsPage={currentJobsPage}
        totalJobs={totalJobs}
        itemsPerPage={itemsPerPage}
        fetchJobsData={fetchJobsData}
        emailHistory={emailHistory}
        loadingHistory={loadingHistory}
        currentHistoryPage={currentHistoryPage}
        totalHistory={totalHistory}
        fetchHistoryData={fetchHistoryData}
        expandedJobs={expandedJobs}
        expandedHistory={expandedHistory}
        toggleJobExpansion={toggleJobExpansion}
        toggleHistoryExpansion={toggleHistoryExpansion}
      />

      {/* Send Reports Dialog */}
      <SendReportsDialog
        open={sendReportsDialogOpen}
        onOpenChange={setSendReportsDialogOpen}
        sendDate={sendDate}
        setSendDate={setSendDate}
        selectedBranches={selectedBranches}
        setSelectedBranches={setSelectedBranches}
        locations={locations}
        loadingLocations={loadingLocations}
        emailConfig={emailConfig}
        isSendingReports={isSendingReports}
        onSendReports={handleSendReports}
        onBranchSelectionChange={handleBranchSelectionChange}
      />

      {/* Branch Mapping Management Dialog */}
      <BranchMappingDialog
        open={mappingDialogOpen}
        onOpenChange={setMappingDialogOpen}
        editingMapping={editingMapping}
        mappingForm={mappingForm}
        setMappingForm={setMappingForm}
        locations={locations}
        savingMapping={savingMapping}
        onSaveMapping={handleSaveMapping}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Branch Mapping</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the mapping for <strong>{mappingToDelete?.branch_code}</strong>? 
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={confirmDeleteMapping}
              className="bg-destructive text-white hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Email Reports Scheduler */}
      <Scheduler
        open={schedulerOpen}
        onOpenChange={setSchedulerOpen}
        type="email_reports"
      />
    </div>
  )
}
