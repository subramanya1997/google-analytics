"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Clock } from "lucide-react"
import { toast } from "sonner"

interface ScheduledTask {
  id: string
  name: string
  type: 'data_ingestion' | 'email_reports'
  schedule: string
  scheduleType: 'cron' | 'natural'
  isActive: boolean
  createdAt: Date
  lastRun?: Date
  nextRun?: Date
  config: {
    // For data ingestion
    dateRange?: { from: Date; to: Date }
    dataTypes?: string[]
    // For email reports
    reportDate?: Date
    branchCodes?: string[]
  }
}

interface SchedulerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  type: 'data_ingestion' | 'email_reports'
  onSchedule?: (task: Omit<ScheduledTask, 'id' | 'createdAt' | 'lastRun' | 'nextRun'>) => void
}

const commonCronPresets = [
  { label: "Daily at midnight", value: "0 0 * * *" },
  { label: "Daily at 9 AM", value: "0 9 * * *" },
  { label: "Daily at 5 PM", value: "0 17 * * *" },
  { label: "Weekly on Sunday at midnight", value: "0 0 * * 0" },
]


export function Scheduler({ open, onOpenChange, type, onSchedule }: SchedulerProps) {
  const [cronExpression, setCronExpression] = useState('')
  const [selectedPreset, setSelectedPreset] = useState('')


  const [isSubmitting, setIsSubmitting] = useState(false)

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

      const newTask: Omit<ScheduledTask, 'id' | 'createdAt' | 'lastRun' | 'nextRun'> = {
        name: `${type} - ${cronExpression}`,
        type,
        schedule: cronExpression,
        scheduleType: 'cron',
        isActive: true,
        config: {}
      }

      if (onSchedule) {
        await onSchedule(newTask)
      }

      toast.success(`${type === 'data_ingestion' ? 'Data ingestion' : 'Email report'} task scheduled successfully!`)

      // Reset form
      setCronExpression('')
      setSelectedPreset('')

      onOpenChange(false)
    } catch (error) {
      console.error('Error scheduling task:', error)
      toast.error('Failed to schedule task')
    } finally {
      setIsSubmitting(false)
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
          <DialogDescription>
            Create scheduled tasks for automated {type === 'data_ingestion' ? 'data ingestion' : 'email reports'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
            <div className="grid gap-4">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="cronExpression">Cron Expression</Label>
                  <Input
                    id="cronExpression"
                    value={cronExpression}
                    onChange={(e) => setCronExpression(e.target.value)}
                    placeholder="* * * * *"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Common Presets</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {commonCronPresets.map((preset) => (
                      <Button
                        key={preset.value}
                        variant={selectedPreset === preset.value ? "default" : "outline"}
                        size="sm"
                        onClick={() => handlePresetChange(preset.value)}
                        className="justify-start text-xs"
                      >
                        {preset.label}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            </div>


            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={isSubmitting}>
                {isSubmitting ? 'Scheduling...' : 'Schedule Task'}
              </Button>
            </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  )
}
