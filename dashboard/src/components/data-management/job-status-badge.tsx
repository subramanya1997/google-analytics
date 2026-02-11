import { Badge } from "@/components/ui/badge"
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  RefreshCw,
} from "lucide-react"

export function getStatusBadge(status: string) {
  switch (status) {
    case "completed":
      return (
        <Badge
          variant="default"
          className="bg-green-100 text-green-800 border-green-200"
        >
          <CheckCircle className="h-3 w-3 mr-1" />
          Completed
        </Badge>
      )
    case "failed":
      return (
        <Badge variant="destructive">
          <XCircle className="h-3 w-3 mr-1" />
          Failed
        </Badge>
      )
    case "processing":
      return (
        <Badge
          variant="secondary"
          className="bg-blue-100 text-blue-800 border-blue-200"
        >
          <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
          Processing
        </Badge>
      )
    case "queued":
      return (
        <Badge variant="outline">
          <Clock className="h-3 w-3 mr-1" />
          Queued
        </Badge>
      )
    default:
      return (
        <Badge variant="outline">
          <AlertCircle className="h-3 w-3 mr-1" />
          {status}
        </Badge>
      )
  }
}

