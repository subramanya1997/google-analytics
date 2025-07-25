"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TaskDetailSheet } from "./task-detail-sheet"
import { 
  ShoppingCart, 
  TrendingUp,
  DollarSign,
  MapPin
} from "lucide-react"

interface ProductDetail {
  name: string
  quantity: number
  price: number
  sku?: string
}

interface PurchaseCartTask {
  id: string
  type: 'purchase' | 'cart'
  priority: 'high' | 'medium' | 'low'
  title: string
  description: string
  customer: {
    name: string
    email: string
    phone?: string
    company?: string
    orderValue?: number
    lastOrder?: string
  }
  productDetails?: ProductDetail[]
  metadata?: {
    products?: string[]
    cartValue?: number
    visitCount?: number
    location?: string
    branchId?: string
  }
  createdAt: string
  status?: string
}

interface TaskCardProps {
  task: PurchaseCartTask
}

const taskIcons = {
  purchase: TrendingUp,
  cart: ShoppingCart,
}

const priorityColors = {
  high: "destructive",
  medium: "default",
  low: "secondary",
} as const

export function TaskCard({ task }: TaskCardProps) {
  const Icon = taskIcons[task.type]
  
  // Get the order/cart value
  const orderValue = task.customer?.orderValue || task.metadata?.cartValue || 0
  
  return (
    <TaskDetailSheet task={task as any}>
      <Card className="hover:shadow-md transition-all duration-200 cursor-pointer group">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-base">{task.title}</CardTitle>
            </div>
            <Badge variant={priorityColors[task.priority]} className="text-xs">
              {task.priority}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 pb-3">
          {/* Customer Info with Order Value */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{task.customer.name}</span>
                {task.customer.company && (
                  <span className="text-xs text-muted-foreground">• {task.customer.company}</span>
                )}
              </div>
              {orderValue > 0 && (
                <div className="flex items-center gap-1">
                  <DollarSign className="h-3 w-3 text-muted-foreground" />
                  <span className="text-sm font-semibold">{orderValue.toFixed(2)}</span>
                </div>
              )}
            </div>
            
            {/* Contact info */}
            {task.customer.email && (
              <div className="text-xs text-muted-foreground truncate">
                {task.customer.email}
              </div>
            )}
            
            {/* Location info */}
            {task.metadata?.location && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <MapPin className="h-3 w-3" />
                <span>{task.metadata.location}</span>
              </div>
            )}
          </div>
          
          {/* Product Details - show up to 3 items */}
          {task.productDetails && task.productDetails.length > 0 && (
            <div className="space-y-1.5 pt-2 border-t">
              {task.productDetails.slice(0, 3).map((product, i) => (
                <div key={i} className="flex justify-between items-center text-sm">
                  <span className="flex-1 truncate pr-2">{product.name}</span>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {product.quantity} × ${product.price.toFixed(2)}
                  </span>
                </div>
              ))}
              {task.productDetails.length > 3 && (
                <div className="text-xs text-muted-foreground">
                  +{task.productDetails.length - 3} more items
                </div>
              )}
            </div>
          )}
          
          {/* Fallback if no productDetails but has products in metadata */}
          {!task.productDetails && task.metadata?.products && task.metadata.products.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-2 border-t">
              {task.metadata.products.slice(0, 3).map((product, i) => (
                <Badge key={i} variant="outline" className="text-xs">
                  {product}
                </Badge>
              ))}
              {task.metadata.products.length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{task.metadata.products.length - 3} more
                </Badge>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </TaskDetailSheet>
  )
} 