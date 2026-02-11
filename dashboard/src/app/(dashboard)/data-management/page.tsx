"use client"

import { useEffect, useState, useCallback } from "react"
import { DEFAULT_PAGE_SIZE } from "@/hooks/use-pagination"
import { toast } from "sonner"
import { fetchDataAvailability, fetchJobs } from "@/lib/api-utils"
import { Scheduler } from "@/components/scheduler"
import {
  DataAvailabilityCard,
  DataIngestionCard,
  JobHistoryTable,
} from "@/components/data-management"
import type { DataAvailability, IngestionJob, JobsResponse } from "@/types"

export default function DataManagementPage() {
  // Data availability state
  const [dataAvailability, setDataAvailability] = useState<DataAvailability | null>(null)
  const [loadingAvailability, setLoadingAvailability] = useState(true)

  // Job history state
  const [jobs, setJobs] = useState<IngestionJob[]>([])
  const [loadingJobs, setLoadingJobs] = useState(true)
  const [currentPage, setCurrentPage] = useState(0)
  const [totalJobs, setTotalJobs] = useState(0)
  const [jobsPerPage, setJobsPerPage] = useState(DEFAULT_PAGE_SIZE)

  // Scheduler state
  const [schedulerOpen, setSchedulerOpen] = useState(false)

  // ---- Data fetching ----

  const fetchDataAvailabilityData = useCallback(async () => {
    try {
      setLoadingAvailability(true)
      const response = await fetchDataAvailability()

      if (!response.ok) {
        throw new Error("Failed to fetch data availability")
      }

      const data = await response.json()
      // API returns response with summary data
      setDataAvailability(data.summary ?? data)
    } catch (error) {
      console.error("Error fetching data availability:", error)
      toast.error("Failed to load data availability")
    } finally {
      setLoadingAvailability(false)
    }
  }, [])

  const fetchJobsData = useCallback(
    async (page = 0) => {
      try {
        setLoadingJobs(true)
        const offset = page * jobsPerPage

        const response = await fetchJobs({ limit: jobsPerPage, offset })

        if (!response.ok) {
          throw new Error("Failed to fetch jobs")
        }

        const data: JobsResponse = await response.json()
        setJobs(data.jobs)
        setTotalJobs(data.total)
        setCurrentPage(page)
      } catch (error) {
        console.error("Error fetching jobs:", error)
        toast.error("Failed to load job history")
      } finally {
        setLoadingJobs(false)
      }
    },
    [jobsPerPage]
  )

  const handleJobsPerPageChange = useCallback((value: string) => {
    setJobsPerPage(Number(value))
    setCurrentPage(0)
  }, [])

  // ---- Initial load (parallel) ----

  useEffect(() => {
    Promise.all([fetchDataAvailabilityData(), fetchJobsData()])
  }, [fetchDataAvailabilityData, fetchJobsData])

  // ---- Event listeners (scheduler + refresh) ----

  useEffect(() => {
    const handleOpenScheduler = () => setSchedulerOpen(true)

    const handleRefreshData = () => {
      fetchDataAvailabilityData()
      fetchJobsData()
      toast.success("Data management data refreshed")
    }

    window.addEventListener("openDataIngestionScheduler", handleOpenScheduler)
    window.addEventListener("refreshDataManagement", handleRefreshData)

    return () => {
      window.removeEventListener("openDataIngestionScheduler", handleOpenScheduler)
      window.removeEventListener("refreshDataManagement", handleRefreshData)
    }
  }, [fetchDataAvailabilityData, fetchJobsData])

  // ---- Render ----

  return (
    <div className="space-y-6">
      {/* Data Availability & Ingestion */}
      <div className="grid gap-6 lg:grid-cols-2">
        <DataAvailabilityCard loading={loadingAvailability} data={dataAvailability} />
        <DataIngestionCard onJobCreated={() => fetchJobsData()} />
      </div>

      {/* Job History */}
      <div className="space-y-4">
        <JobHistoryTable
          jobs={jobs}
          loading={loadingJobs}
          totalJobs={totalJobs}
          currentPage={currentPage}
          jobsPerPage={jobsPerPage}
          onPageChange={fetchJobsData}
          onPageSizeChange={handleJobsPerPageChange}
        />
      </div>

      {/* Scheduler Dialog */}
      <Scheduler open={schedulerOpen} onOpenChange={setSchedulerOpen} type="data_ingestion" />
    </div>
  )
}
