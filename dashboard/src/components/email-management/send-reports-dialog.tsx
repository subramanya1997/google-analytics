"use client"

import React from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Calendar } from "@/components/ui/calendar"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Send,
  RefreshCw,
  MapPin,
  Calendar as CalendarIcon
} from "lucide-react"
import { format } from "date-fns"
import { EmailConfigResponse, Location } from "@/types"

interface SendReportsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sendDate: Date
  setSendDate: (date: Date) => void
  selectedBranches: string[]
  setSelectedBranches: (branches: string[]) => void
  locations: Location[]
  loadingLocations: boolean
  emailConfig: EmailConfigResponse | null
  isSendingReports: boolean
  onSendReports: () => void
  onBranchSelectionChange: (branchId: string, checked: boolean) => void
}

export function SendReportsDialog({
  open,
  onOpenChange,
  sendDate,
  setSendDate,
  selectedBranches,
  setSelectedBranches,
  locations,
  loadingLocations,
  emailConfig,
  isSendingReports,
  onSendReports,
  onBranchSelectionChange
}: SendReportsDialogProps) {
  const handleSendReports = async () => {
    try {
      await onSendReports()
      // Close dialog after successful send (onSendReports handles the success state)
      onOpenChange(false)
    } catch {
      // Error is already handled in onSendReports, just keep dialog open
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" />
            Send Email Reports
          </DialogTitle>
          <DialogDescription>
            Configure and send branch reports via email to sales representatives.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
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
              <div className="max-h-40 overflow-y-auto border rounded-md p-2 space-y-1">
                {locations.map((location) => (
                  <div key={location.locationId} className="flex items-center space-x-2">
                    <Checkbox
                      id={location.locationId}
                      checked={selectedBranches.includes(location.locationId)}
                      onCheckedChange={(checked) => 
                        onBranchSelectionChange(location.locationId, !!checked)
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

          {!emailConfig?.configured && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
              <p className="text-sm text-destructive">
                Please configure SMTP settings in the authentication service first
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSendingReports}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleSendReports}
            disabled={isSendingReports || !sendDate || !emailConfig?.configured}
          >
            {isSendingReports ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Sending Reports...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Send
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
