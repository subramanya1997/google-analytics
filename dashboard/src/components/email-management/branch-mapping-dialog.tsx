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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { RefreshCw } from "lucide-react"
import { BranchEmailMapping, Location } from "@/types"

interface MappingForm {
  branch_code: string
  branch_name: string
  sales_rep_email: string
  sales_rep_name: string
  is_enabled: boolean
}

interface BranchMappingDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  editingMapping: BranchEmailMapping | null
  mappingForm: MappingForm
  setMappingForm: (form: MappingForm) => void
  locations: Location[]
  savingMapping: boolean
  onSaveMapping: () => void
}

export function BranchMappingDialog({
  open,
  onOpenChange,
  editingMapping,
  mappingForm,
  setMappingForm,
  locations,
  savingMapping,
  onSaveMapping
}: BranchMappingDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {editingMapping ? 'Edit Branch Mapping' : 'Add Branch Mapping'}
          </DialogTitle>
          <DialogDescription>
            {editingMapping ? 'Update the branch email mapping details.' : 'Create a new branch to recipient email mapping.'}
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="branch_code">Branch *</Label>
            <Select
              value={mappingForm.branch_code}
              onValueChange={(value) => {
                // Auto-fill branch name from location data
                const location = locations.find(l => l.locationId === value)
                setMappingForm({ 
                  ...mappingForm, 
                  branch_code: value,
                  branch_name: location?.locationName || ''
                })
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

          <div className="grid gap-2">
            <Label htmlFor="sales_rep_name">Recipient Name</Label>
            <Input
              id="sales_rep_name"
              value={mappingForm.sales_rep_name}
              onChange={(e) => setMappingForm({ ...mappingForm, sales_rep_name: e.target.value })}
              placeholder="Recipient full name"
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="sales_rep_email">Recipient Email *</Label>
            <Input
              id="sales_rep_email"
              type="email"
              value={mappingForm.sales_rep_email}
              onChange={(e) => setMappingForm({ ...mappingForm, sales_rep_email: e.target.value })}
              placeholder="recipient@company.com"
            />
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="is_enabled"
              checked={mappingForm.is_enabled}
              onCheckedChange={(checked) => setMappingForm({ ...mappingForm, is_enabled: !!checked })}
            />
            <Label htmlFor="is_enabled" className="text-sm font-normal">
              Enable this mapping
            </Label>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={savingMapping}
          >
            Cancel
          </Button>
          <Button
            onClick={onSaveMapping}
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
  )
}
