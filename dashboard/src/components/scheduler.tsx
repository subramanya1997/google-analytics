"use client"

import React, { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
import { Clock, RefreshCw, Trash2 } from "lucide-react"
import { toast } from "sonner"
import {
  upsertDataIngestionSchedule,
  upsertEmailSchedule,
  getDataIngestionSchedule,
  getEmailSchedule,
  deleteDataIngestionSchedule,
  deleteEmailSchedule,
} from "@/lib/api-utils"

interface SchedulerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  type: 'data_ingestion' | 'email_reports'
  onSuccess?: () => void
}

const commonCronPresets = [
  { label: "Daily at midnight", value: "0 0 * * *" },
  { label: "Daily at 2 AM", value: "0 2 * * *" },
  { label: "Daily at 8 AM", value: "0 8 * * *" },
  { label: "Daily at 9 AM", value: "0 9 * * *" },
  { label: "Daily at 5 PM", value: "0 17 * * *" },
  { label: "Weekly on Monday at 9 AM", value: "0 9 * * 1" },
]

export function Scheduler({ open, onOpenChange, type, onSuccess }: SchedulerProps) {
  const [cronExpression, setCronExpression] = useState('')
  const [selectedPreset, setSelectedPreset] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingSchedule, setIsLoadingSchedule] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [existingSchedule, setExistingSchedule] = useState<{ cron_expression?: string; status?: string; source?: string } | null>(null)

  // Fetch existing schedule when dialog opens
  useEffect(() => {
    if (open && type) {
      const fetchSchedule = async () => {
        setIsLoadingSchedule(true)
        try {
          const response = type === 'data_ingestion' 
            ? await getDataIngestionSchedule()
            : await getEmailSchedule()
          
          if (response.ok) {
            const data = await response.json()
            
            // New simplified response format: { cron_expression, status, source }
            if (data.cron_expression) {
              const isActive = data.status === 'active' && data.source === 'scheduler'
              setExistingSchedule(isActive ? data : null)

              // Pre-populate the form with the cron expression
              setCronExpression(data.cron_expression)
              
              // Check if it matches any preset
              const matchingPreset = commonCronPresets.find(p => p.value === data.cron_expression)
              if (matchingPreset) {
                setSelectedPreset(matchingPreset.value)
              }
            } else {
              // No schedule at all
              setExistingSchedule(null)
            }
          }
        } catch (error) {
          console.error('Error fetching schedule:', error)
          // Don't show error toast as this is optional data
        } finally {
          setIsLoadingSchedule(false)
        }
      }
      
      fetchSchedule()
    } else if (!open) {
      // Reset form when dialog closes
      setCronExpression('')
      setSelectedPreset('')
      setExistingSchedule(null)
    }
  }, [open, type])

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset)
    setCronExpression(preset)
  }

  const validateCronExpression = (cron: string): boolean => {
    const cronRegex = /^(\*|(\d+|\d+-\d+|(\d+(,\d+)*)|(\*\/\d+))) (\*|(\d+|\d+-\d+|(\d+(,\d+)*)|(\*\/\d+))) (\*|(\d+|\d+-\d+|(\d+(,\d+)*)|(\*\/\d+))) (\*|(\d+|\d+-\d+|(\d+(,\d+)*)|(\*\/\d+))) (\*|(\d+|\d+-\d+|(\d+(,\d+)*)|(\*\/\d+)))$/
    return cronRegex.test(cron.trim())
  }

  const handleSubmit = async () => {
    if (!cronExpression.trim()) {
      toast.error('Please enter a cron expression')
      return
    }
    if (!validateCronExpression(cronExpression)) {
      toast.error('Invalid cron expression')
      return
    }

    try {
      setIsSubmitting(true)

      // Call the appropriate upsert API based on type
      const response = type === 'data_ingestion'
        ? await upsertDataIngestionSchedule({
            cron_expression: cronExpression,
            status: 'active'
          })
        : await upsertEmailSchedule({
            cron_expression: cronExpression,
            status: 'active'
          })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create schedule')
      }

      const result = await response.json()
      const operation = result.operation === 'created' ? 'created' : 'updated'
      
      toast.success(`${type === 'data_ingestion' ? 'Data ingestion' : 'Email report'} schedule ${operation} successfully!`)

      // Reset form
      setCronExpression('')
      setSelectedPreset('')

      // Call success callback if provided
      if (onSuccess) {
        onSuccess()
      }

      onOpenChange(false)
    } catch (error) {
      console.error('Error scheduling task:', error)
      toast.error(error instanceof Error ? error.message : 'Failed to schedule task')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async () => {
    try {
      setIsDeleting(true)

      const response = type === 'data_ingestion'
        ? await deleteDataIngestionSchedule()
        : await deleteEmailSchedule()

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete schedule')
      }

      toast.success(`${type === 'data_ingestion' ? 'Data ingestion' : 'Email report'} schedule deleted successfully!`)

      setCronExpression('')
      setSelectedPreset('')
      setExistingSchedule(null)
      onSuccess?.()
      onOpenChange(false)
    } catch (error) {
      console.error('Error deleting schedule:', error)
      toast.error(error instanceof Error ? error.message : 'Failed to delete schedule')
    } finally {
      setIsDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            {type === 'data_ingestion' ? 'Data Ingestion Scheduler' : 'Email Reports Scheduler'}
          </DialogTitle>
          <DialogDescription className="flex items-center gap-2">
            Create or update scheduled tasks for automated {type === 'data_ingestion' ? 'data ingestion' : 'email reports'}
            {isLoadingSchedule && (
              <RefreshCw className="h-3 w-3 animate-spin ml-2" />
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
            {/* Schedule Status Badge */}
            {!isLoadingSchedule && existingSchedule && (
              <div className="flex items-center justify-between p-3 bg-muted rounded-md">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                    Existing Schedule
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    Updating current schedule
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  onClick={() => setShowDeleteConfirm(true)}
                  disabled={isDeleting}
                >
                  <Trash2 className="h-4 w-4 mr-1.5" />
                  Delete
                </Button>
              </div>
            )}

            <div className="grid gap-4">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="cronExpression">Cron Expression</Label>
                  {isLoadingSchedule ? (
                    <Skeleton className="h-10 w-full" />
                  ) : (
                    <Input
                      id="cronExpression"
                      value={cronExpression}
                      onChange={(e) => {
                        const value = e.target.value
                        setCronExpression(value)
                        // Sync preset: highlight if matches, clear otherwise
                        const match = commonCronPresets.find(p => p.value === value.trim())
                        setSelectedPreset(match ? match.value : '')
                      }}
                      placeholder="0 2 * * *"
                      disabled={isLoadingSchedule}
                    />
                  )}
                  <p className="text-xs text-muted-foreground">
                    Enter a cron expression (e.g., &quot;0 2 * * *&quot; for daily at 2 AM)
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Common Presets</Label>
                  {isLoadingSchedule ? (
                    <div className="grid grid-cols-2 gap-2">
                      {Array.from({ length: 6 }).map((_, i) => (
                        <Skeleton key={i} className="h-8 w-full" />
                      ))}
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-2">
                      {commonCronPresets.map((preset) => (
                        <Button
                          key={preset.value}
                          variant={selectedPreset === preset.value ? "default" : "outline"}
                          size="sm"
                          onClick={() => handlePresetChange(preset.value)}
                          className="justify-start text-xs"
                          disabled={isLoadingSchedule}
                        >
                          {preset.label}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoadingSchedule}>
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={isSubmitting || isLoadingSchedule}>
                {isSubmitting ? 'Saving...' : existingSchedule ? 'Update Schedule' : 'Create Schedule'}
              </Button>
            </DialogFooter>
        </div>
      </DialogContent>

      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Schedule?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove the {type === 'data_ingestion' ? 'data ingestion' : 'email report'} schedule. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Dialog>
  )
}
