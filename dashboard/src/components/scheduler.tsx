"use client"

import React, { useState, useEffect, useMemo, useCallback } from "react"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Clock, RefreshCw, Trash2, Globe, ChevronDown, ChevronUp } from "lucide-react"
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

type Frequency = 'daily' | 'weekly'
type DayOfWeek = '0' | '1' | '2' | '3' | '4' | '5' | '6'

const DAYS_OF_WEEK: { value: DayOfWeek; label: string }[] = [
  { value: '0', label: 'Sunday' },
  { value: '1', label: 'Monday' },
  { value: '2', label: 'Tuesday' },
  { value: '3', label: 'Wednesday' },
  { value: '4', label: 'Thursday' },
  { value: '5', label: 'Friday' },
  { value: '6', label: 'Saturday' },
]

function getBrowserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch {
    return 'UTC'
  }
}

function getUtcOffsetMinutes(): number {
  return new Date().getTimezoneOffset()
}

/**
 * Convert local hour:minute to UTC hour:minute, accounting for day wrap.
 * Returns { utcHour, utcMinute, dayShift } where dayShift is -1, 0, or +1.
 */
function localToUtc(localHour: number, localMinute: number): { utcHour: number; utcMinute: number; dayShift: number } {
  const offsetMin = getUtcOffsetMinutes()
  let totalMinutesUtc = localHour * 60 + localMinute + offsetMin
  let dayShift = 0

  if (totalMinutesUtc < 0) {
    totalMinutesUtc += 1440
    dayShift = -1
  } else if (totalMinutesUtc >= 1440) {
    totalMinutesUtc -= 1440
    dayShift = 1
  }

  return {
    utcHour: Math.floor(totalMinutesUtc / 60),
    utcMinute: totalMinutesUtc % 60,
    dayShift,
  }
}

/**
 * Convert UTC hour:minute to local hour:minute, accounting for day wrap.
 * Returns { localHour, localMinute, dayShift }.
 */
function utcToLocal(utcHour: number, utcMinute: number): { localHour: number; localMinute: number; dayShift: number } {
  const offsetMin = getUtcOffsetMinutes()
  let totalMinutesLocal = utcHour * 60 + utcMinute - offsetMin
  let dayShift = 0

  if (totalMinutesLocal < 0) {
    totalMinutesLocal += 1440
    dayShift = -1
  } else if (totalMinutesLocal >= 1440) {
    totalMinutesLocal -= 1440
    dayShift = 1
  }

  return {
    localHour: Math.floor(totalMinutesLocal / 60),
    localMinute: totalMinutesLocal % 60,
    dayShift,
  }
}

function buildCronFromLocal(
  localHour: number,
  localMinute: number,
  frequency: Frequency,
  dayOfWeek: DayOfWeek,
): string {
  const { utcHour, utcMinute, dayShift } = localToUtc(localHour, localMinute)

  let dowField = '*'
  if (frequency === 'weekly') {
    let adjustedDay = (parseInt(dayOfWeek, 10) + dayShift + 7) % 7
    if (adjustedDay < 0) adjustedDay += 7
    dowField = String(adjustedDay)
  }

  return `${utcMinute} ${utcHour} * * ${dowField}`
}

/**
 * Parse a UTC cron expression into local time components.
 * Returns null if the cron is too complex for the simple picker.
 */
function parseCronToLocal(cron: string): {
  localHour: number
  localMinute: number
  frequency: Frequency
  dayOfWeek: DayOfWeek
} | null {
  const parts = cron.trim().split(/\s+/)
  if (parts.length !== 5) return null

  const [minStr, hourStr, dayOfMonth, month, dowStr] = parts

  if (dayOfMonth !== '*' || month !== '*') return null

  const utcMinute = parseInt(minStr, 10)
  const utcHour = parseInt(hourStr, 10)
  if (isNaN(utcMinute) || isNaN(utcHour)) return null
  if (utcMinute < 0 || utcMinute > 59 || utcHour < 0 || utcHour > 23) return null

  const { localHour, localMinute, dayShift } = utcToLocal(utcHour, utcMinute)

  let frequency: Frequency = 'daily'
  let dayOfWeek: DayOfWeek = '1'

  if (dowStr !== '*') {
    const dow = parseInt(dowStr, 10)
    if (isNaN(dow) || dow < 0 || dow > 6) return null
    frequency = 'weekly'
    let adjustedDay = (dow - dayShift + 7) % 7
    if (adjustedDay < 0) adjustedDay += 7
    dayOfWeek = String(adjustedDay) as DayOfWeek
  }

  return { localHour, localMinute, frequency, dayOfWeek }
}

function formatTime12h(hour: number, minute: number): string {
  const period = hour >= 12 ? 'PM' : 'AM'
  const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour
  return `${displayHour}:${String(minute).padStart(2, '0')} ${period}`
}

function formatTimezoneShort(): string {
  try {
    const formatter = new Intl.DateTimeFormat(undefined, { timeZoneName: 'short' })
    const parts = formatter.formatToParts(new Date())
    const tzPart = parts.find(p => p.type === 'timeZoneName')
    return tzPart?.value ?? getBrowserTimezone()
  } catch {
    return getBrowserTimezone()
  }
}

export function Scheduler({ open, onOpenChange, type, onSuccess }: SchedulerProps) {
  const [cronExpression, setCronExpression] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingSchedule, setIsLoadingSchedule] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [existingSchedule, setExistingSchedule] = useState<{ cron_expression?: string; status?: string; source?: string } | null>(null)

  const [selectedHour, setSelectedHour] = useState('9')
  const [selectedMinute, setSelectedMinute] = useState('0')
  const [selectedFrequency, setSelectedFrequency] = useState<Frequency>('daily')
  const [selectedDay, setSelectedDay] = useState<DayOfWeek>('1')

  const browserTimezone = useMemo(() => getBrowserTimezone(), [])
  const timezoneShort = useMemo(() => formatTimezoneShort(), [])

  const hours = useMemo(() =>
    Array.from({ length: 24 }, (_, i) => ({
      value: String(i),
      label: formatTime12h(i, 0).replace(/:00/, '').trim(),
    })),
    []
  )

  const minutes = useMemo(() =>
    [0, 15, 30, 45].map(m => ({
      value: String(m),
      label: String(m).padStart(2, '0'),
    })),
    []
  )

  const syncCronFromPicker = useCallback((hour: string, minute: string, freq: Frequency, day: DayOfWeek) => {
    const cron = buildCronFromLocal(parseInt(hour, 10), parseInt(minute, 10), freq, day)
    setCronExpression(cron)
  }, [])

  const syncPickerFromCron = useCallback((cron: string) => {
    const parsed = parseCronToLocal(cron)
    if (parsed) {
      setSelectedHour(String(parsed.localHour))
      setSelectedMinute(String(parsed.localMinute))
      setSelectedFrequency(parsed.frequency)
      setSelectedDay(parsed.dayOfWeek)
    }
  }, [])

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

            if (data.cron_expression) {
              const isActive = data.status === 'active' && data.source === 'scheduler'
              setExistingSchedule(isActive ? data : null)

              setCronExpression(data.cron_expression)
              syncPickerFromCron(data.cron_expression)

              const parsed = parseCronToLocal(data.cron_expression)
              if (!parsed) {
                setShowAdvanced(true)
              }
            } else {
              setExistingSchedule(null)
            }
          }
        } catch (error) {
          console.error('Error fetching schedule:', error)
        } finally {
          setIsLoadingSchedule(false)
        }
      }

      fetchSchedule()
    } else if (!open) {
      setCronExpression('')
      setSelectedHour('9')
      setSelectedMinute('0')
      setSelectedFrequency('daily')
      setSelectedDay('1')
      setExistingSchedule(null)
      setShowAdvanced(false)
    }
  }, [open, type, syncPickerFromCron])

  const handleHourChange = (hour: string) => {
    setSelectedHour(hour)
    syncCronFromPicker(hour, selectedMinute, selectedFrequency, selectedDay)
  }

  const handleMinuteChange = (minute: string) => {
    setSelectedMinute(minute)
    syncCronFromPicker(selectedHour, minute, selectedFrequency, selectedDay)
  }

  const handleFrequencyChange = (freq: Frequency) => {
    setSelectedFrequency(freq)
    syncCronFromPicker(selectedHour, selectedMinute, freq, selectedDay)
  }

  const handleDayChange = (day: DayOfWeek) => {
    setSelectedDay(day)
    syncCronFromPicker(selectedHour, selectedMinute, selectedFrequency, day)
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

      setCronExpression('')
      setSelectedHour('9')
      setSelectedMinute('0')
      setSelectedFrequency('daily')
      setSelectedDay('1')

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
      setSelectedHour('9')
      setSelectedMinute('0')
      setSelectedFrequency('daily')
      setSelectedDay('1')
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

  const scheduleSummary = useMemo(() => {
    const h = parseInt(selectedHour, 10)
    const m = parseInt(selectedMinute, 10)
    const timeStr = formatTime12h(h, m)

    if (selectedFrequency === 'weekly') {
      const dayLabel = DAYS_OF_WEEK.find(d => d.value === selectedDay)?.label ?? ''
      return `Every ${dayLabel} at ${timeStr} (${timezoneShort})`
    }
    return `Daily at ${timeStr} (${timezoneShort})`
  }, [selectedHour, selectedMinute, selectedFrequency, selectedDay, timezoneShort])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
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

        <div className="space-y-5">
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

          {/* Timezone indicator */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground rounded-md border px-3 py-2">
            <Globe className="h-4 w-4 shrink-0" />
            <span>Timezone: <span className="font-medium text-foreground">{browserTimezone}</span> ({timezoneShort})</span>
          </div>

          {/* Time picker section */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Frequency</Label>
              {isLoadingSchedule ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <Select value={selectedFrequency} onValueChange={(v) => handleFrequencyChange(v as Frequency)}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                  </SelectContent>
                </Select>
              )}
            </div>

            {selectedFrequency === 'weekly' && (
              <div className="space-y-2">
                <Label>Day of Week</Label>
                {isLoadingSchedule ? (
                  <Skeleton className="h-9 w-full" />
                ) : (
                  <Select value={selectedDay} onValueChange={(v) => handleDayChange(v as DayOfWeek)}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {DAYS_OF_WEEK.map(d => (
                        <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            )}

            <div className="space-y-2">
              <Label>Time</Label>
              {isLoadingSchedule ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <div className="flex items-center gap-2">
                  <Select value={selectedHour} onValueChange={handleHourChange}>
                    <SelectTrigger className="w-[120px]">
                      <SelectValue placeholder="Hour" />
                    </SelectTrigger>
                    <SelectContent>
                      {hours.map(h => (
                        <SelectItem key={h.value} value={h.value}>
                          {formatTime12h(parseInt(h.value, 10), 0).replace(/:00\s/, ' ')}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <span className="text-muted-foreground font-medium">:</span>
                  <Select value={selectedMinute} onValueChange={handleMinuteChange}>
                    <SelectTrigger className="w-[90px]">
                      <SelectValue placeholder="Min" />
                    </SelectTrigger>
                    <SelectContent>
                      {minutes.map(m => (
                        <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <span className="text-xs text-muted-foreground ml-1">{timezoneShort}</span>
                </div>
              )}
            </div>

            {/* Schedule summary */}
            {!isLoadingSchedule && (
              <div className="rounded-md bg-muted/50 px-3 py-2 text-sm">
                {scheduleSummary}
              </div>
            )}
          </div>

          {/* Advanced cron input (collapsible) */}
          <div className="space-y-2">
            <button
              type="button"
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              {showAdvanced ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              Advanced: Edit cron expression
            </button>
            {showAdvanced && (
              <div className="space-y-2 pt-1">
                <Input
                  id="cronExpression"
                  value={cronExpression}
                  onChange={(e) => {
                    const value = e.target.value
                    setCronExpression(value)
                    syncPickerFromCron(value)
                  }}
                  placeholder="0 2 * * *"
                  disabled={isLoadingSchedule}
                />
                <p className="text-xs text-muted-foreground">
                  Cron expression in UTC (e.g., &quot;0 2 * * *&quot; for daily at 2 AM UTC).
                  Editing this will update the time picker above.
                </p>
              </div>
            )}
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
