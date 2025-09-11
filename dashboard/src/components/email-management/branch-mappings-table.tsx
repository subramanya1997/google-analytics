"use client"

import React from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Users,
  Edit,
  Trash2,
  CheckCircle,
  XCircle
} from "lucide-react"
import { BranchEmailMapping } from "@/types"

interface BranchMappingsTableProps {
  branchMappings: BranchEmailMapping[]
  loadingMappings: boolean
  onEditMapping: (mapping: BranchEmailMapping) => void
  onDeleteMapping: (mapping: BranchEmailMapping) => void
}

export function BranchMappingsTable({
  branchMappings,
  loadingMappings,
  onEditMapping,
  onDeleteMapping
}: BranchMappingsTableProps) {
  return (
    <div>
      <div className="mb-4">
        <h3 className="flex items-center gap-2 text-lg font-semibold">
          <Users className="h-5 w-5" />
          Branch Members
        </h3>
      </div>
      
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
                  <TableHead>Branch</TableHead>
                  <TableHead>Recipient</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-20"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {branchMappings.map((mapping) => (
                  <TableRow 
                    key={mapping.id || `${mapping.branch_code}-${mapping.sales_rep_email}`}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="font-medium">{mapping.branch_name || 'N/A'}</div>
                        <Badge variant="outline" className="font-mono text-xs">
                          {mapping.branch_code}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <div className="font-medium">{mapping.sales_rep_name || 'N/A'}</div>
                        <div className="text-sm text-muted-foreground font-mono">
                          {mapping.sales_rep_email}
                        </div>
                      </div>
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
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            onEditMapping(mapping)
                          }}
                          title="Edit mapping"
                        >
                          <Edit className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            onDeleteMapping(mapping)
                          }}
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
            <p className="text-muted-foreground">No branch mappings configured</p>
            <p className="text-sm text-muted-foreground mt-2">Use the &quot;Add Mapping&quot; button in the header to create your first mapping.</p>
          </div>
        )}
    </div>
  )
}
