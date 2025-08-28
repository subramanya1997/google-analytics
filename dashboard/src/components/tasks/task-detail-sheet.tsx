"use client"

import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Task } from "@/types/tasks"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
// Temporarily removed textarea import due to TypeScript cache issue
import { 
  User, 
  Mail, 
  Phone, 
  Calendar,
  DollarSign,
  Package,
  Search,
  ShoppingCart,
  TrendingUp,
  AlertCircle,
  Check,
  Loader2
} from "lucide-react"
import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"

// Actual task structure that includes purchase and cart types
interface ActualTask {
  id: string
  type: 'purchase' | 'cart' | 'search' | 'visit' | 'performance' | 'repeat_visit'
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
  productDetails?: Array<{
    name: string
    quantity: number
    price: number
    sku?: string
  }>
  metadata?: {
    searchTerms?: string[]
    visitCount?: number
    cartValue?: number
    products?: string[]
  }
  createdAt: string
  status?: string
  userId?: string | number
  sessionId?: string
}

interface TaskDetailSheetProps {
  task: Task
  children: React.ReactNode
}

interface PurchaseHistoryItem {
  transaction_id: string
  event_date: string
  event_timestamp: string
  order_value: string
  items: Array<{
    name: string
    sku: string
    quantity: number
    price: number
  }>
}

interface UserHistory {
  user: any
  purchaseHistory: PurchaseHistoryItem[]
  searchHistory: any[]
  cartHistory: Array<{
    session_id: string
    event_date: string
    event_timestamp: string
    cart_value: number
    items: Array<{
      name: string
      sku: string
      quantity: number
      price: number
    }>
  }>
  viewedProductsHistory: Array<{
    sku: string
    name: string
    category: string
    price: number
    view_count: number
    last_viewed_date: string
    last_viewed_timestamp: string
  }>
}

export function TaskDetailSheet({ task, children }: TaskDetailSheetProps) {
  const [userHistory, setUserHistory] = useState<UserHistory>({
    user: null,
    purchaseHistory: [],
    searchHistory: [],
    cartHistory: [],
    viewedProductsHistory: []
  })
  const [loading, setLoading] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [notes, setNotes] = useState('')
  const [savingStatus, setSavingStatus] = useState(false)
  const [hasStatusChanges, setHasStatusChanges] = useState(false)
  const [initialStatusLoaded, setInitialStatusLoaded] = useState(false)
  
  // Cast task to actual structure
  const actualTask = task as unknown as ActualTask

  // Fetch task status
  const fetchTaskStatus = async () => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
      const tenantId = '550e8400-e29b-41d4-a716-446655440000' // Example tenant_id
      const url = `${baseUrl}/tasks/status?task_id=${actualTask.id}&task_type=${actualTask.type}&tenant_id=${tenantId}`
      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setCompleted(data.completed || false)
        setNotes(data.notes || '')
      }
    } catch (error) {
      console.error('Error fetching task status:', error)
    } finally {
      setInitialStatusLoaded(true)
    }
  }

  // Save task status
  const saveTaskStatus = async () => {
    setSavingStatus(true)
    try {
      const baseUrl = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
      const url = `${baseUrl}/tasks/status`
      const response = await fetch(url, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tenant_id: '550e8400-e29b-41d4-a716-446655440000', // Example tenant_id
          task_id: actualTask.id,
          task_type: actualTask.type,
          completed,
          notes,
          completedBy: 'Current User'
        }),
      })

      if (response.ok) {
        setHasStatusChanges(false)
      } else {
        throw new Error('Failed to update task status')
      }
    } catch (error) {
      console.error('Error updating task status:', error)
    } finally {
      setSavingStatus(false)
    }
  }

  const fetchUserHistory = async () => {
    setLoading(true)
    
    let userId = null
    if (actualTask.userId) {
      userId = actualTask.userId
    } else if (actualTask.customer?.name?.includes('Customer #')) {
      const match = actualTask.customer.name.match(/#(\d+)/)
      if (match) {
        userId = match[1]
      }
    }
    
    let sessionId = actualTask.sessionId || null
    
    console.log('Fetching history for:', { 
      userId, 
      sessionId, 
      taskType: actualTask.type, 
      taskId: actualTask.id,
      customer: actualTask.customer 
    })
    
    try {
      const baseUrl = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || ''
      const tenantId = '550e8400-e29b-41d4-a716-446655440000' // Example tenant_id
      let url = ''
      
      // First try to fetch by userId if available
      if (userId) {
        url = `${baseUrl}/users/${userId}/history?tenant_id=${tenantId}`
      } else if (sessionId) {
        // If no userId or failed, try by sessionId
        url = `${baseUrl}/sessions/${sessionId}/history?tenant_id=${tenantId}`
      }

      console.log('History API URL:', url)

      if (url) {
        const response = await fetch(url)
        if (response.ok) {
          const historyEvents = await response.json()
          
          console.log('History events response:', historyEvents)
          
          // Process the flat event list into categorized history
          const purchaseHistory: any[] = []
          const searchHistory: any[] = []
          const cartHistory: any[] = []
          const viewedProductsHistory: any[] = [] // This might not be available directly

          // Handle both array and single object response
          const eventsArray = Array.isArray(historyEvents) ? historyEvents : (historyEvents.data || [])
          
          console.log('Events array length:', eventsArray.length)
          
          eventsArray.forEach((event: any) => {
            switch (event.event_type) {
              case 'purchase':
                purchaseHistory.push({
                  transaction_id: event.details.transaction_id,
                  event_date: new Date(event.event_timestamp / 1000).toISOString().split('T')[0].replace(/-/g, ''),
                  event_timestamp: event.event_timestamp,
                  order_value: event.details.revenue,
                  items: JSON.parse(event.details.items || '[]')
                })
                break
              case 'add_to_cart':
                cartHistory.push({
                  session_id: event.param_ga_session_id,
                  event_date: new Date(event.event_timestamp / 1000).toISOString().split('T')[0].replace(/-/g, ''),
                  event_timestamp: event.event_timestamp,
                  cart_value: (event.details.price || 0) * (event.details.quantity || 0),
                  items: [{
                    name: event.details.item_name,
                    sku: event.details.item_id,
                    quantity: event.details.quantity || 0,
                    price: event.details.price || 0
                  }]
                })
                break
              case 'view_search_results':
                searchHistory.push({
                  term: event.details.search_term,
                  date: new Date(event.event_timestamp / 1000).toISOString().split('T')[0].replace(/-/g, ''),
                  results: 1 // Placeholder
                })
                break
              case 'no_search_results':
                searchHistory.push({
                  term: event.details.search_term,
                  date: new Date(event.event_timestamp / 1000).toISOString().split('T')[0].replace(/-/g, ''),
                  results: 0
                })
                break
                             case 'page_view':
                 // Add to viewed products if it's a product page
                 if (event.details.page_location && event.details.page_location.includes('/product/')) {
                   viewedProductsHistory.push({
                     sku: event.details.page_location.split('/').pop() || 'unknown',
                     name: event.details.page_title || 'Unknown Product',
                     category: 'Product',
                     price: 0,
                     view_count: 1,
                     last_viewed_timestamp: event.event_timestamp,
                     last_viewed_date: new Date(event.event_timestamp / 1000).toISOString().split('T')[0].replace(/-/g, '')
                   })
                 }
                 break
               case 'view_item':
                 // Add product views from view_item events
                 viewedProductsHistory.push({
                   sku: event.details.item_id || 'unknown',
                   name: event.details.item_name || 'Unknown Product',
                   category: event.details.category || 'Product',
                   price: event.details.price || 0,
                   view_count: 1,
                   last_viewed_timestamp: event.event_timestamp,
                   last_viewed_date: new Date(event.event_timestamp / 1000).toISOString().split('T')[0].replace(/-/g, '')
                 })
                 break
            }
          })

          setUserHistory({
            user: null, // User info is not in this response
            purchaseHistory,
            searchHistory,
            cartHistory, // This will be empty for now
            viewedProductsHistory
          })
        }
      }
    } catch (error) {
      console.error('Error fetching user history:', error)
    }
    
    setLoading(false)
  }

  // Handle open change
  const handleOpenChange = (open: boolean) => {
    if (open) {
      fetchUserHistory()
      fetchTaskStatus()
    }
  }

  // Handle completed change
  const handleCompletedChange = (checked: boolean) => {
    setCompleted(checked)
    setHasStatusChanges(true)
  }

  // Handle notes change
  const handleNotesChange = (value: string) => {
    setNotes(value)
    setHasStatusChanges(true)
  }

  const getTaskIcon = () => {
    switch (actualTask.type) {
      case 'purchase': return TrendingUp
      case 'cart': return ShoppingCart
      case 'search': return Search
      case 'visit': return User
      case 'performance': return AlertCircle
      default: return Package
    }
  }

  const TaskIcon = getTaskIcon()

  return (
    <Sheet onOpenChange={handleOpenChange}>
      <SheetTrigger asChild>
        {children}
      </SheetTrigger>
      <SheetContent className="w-[600px] sm:max-w-[600px] overflow-y-auto p-0">
        <SheetHeader className="p-6 pb-4 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-muted">
                <TaskIcon className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <SheetTitle className="text-xl">{actualTask.title}</SheetTitle>
                <SheetDescription className="mt-1">{actualTask.description}</SheetDescription>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={
                actualTask.priority === 'high' ? 'destructive' : 
                actualTask.priority === 'medium' ? 'default' : 'secondary'
              } className="ml-3">
                {actualTask.priority}
              </Badge>
              <Button
                size="sm"
                variant={completed ? "secondary" : "default"}
                onClick={() => handleCompletedChange(!completed)}
                disabled={savingStatus}
                className="gap-2"
              >
                {savingStatus ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : completed ? (
                  <Check className="h-4 w-4" />
                ) : null}
                {completed ? "Completed" : "Mark Complete"}
              </Button>
            </div>
          </div>
        </SheetHeader>

        <div className="p-6 space-y-6">
          {/* Customer Information Card */}
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Customer Information</h3>
            <Card className="border-0 shadow-none bg-muted/50">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-full bg-background">
                    <User className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{actualTask.customer.name}</p>
                    {actualTask.customer.company && (
                      <p className="text-xs text-muted-foreground">{actualTask.customer.company}</p>
                    )}
                  </div>
                </div>

                <div className="grid gap-2 ml-9">
                  {actualTask.customer.email && (
                    <a href={`mailto:${actualTask.customer.email}`} className="text-xs hover:underline text-muted-foreground flex items-center gap-2">
                      <Mail className="h-3 w-3" />
                      {actualTask.customer.email}
                    </a>
                  )}

                  {actualTask.customer.phone && (
                    <a href={`tel:${actualTask.customer.phone}`} className="text-xs hover:underline text-muted-foreground flex items-center gap-2">
                      <Phone className="h-3 w-3" />
                      {actualTask.customer.phone}
                    </a>
                  )}

                  {actualTask.customer.lastOrder && (
                    <div className="text-xs text-muted-foreground flex items-center gap-2">
                      <Calendar className="h-3 w-3" />
                      Last order: {actualTask.customer.lastOrder}
                    </div>
                  )}

                  {actualTask.customer.orderValue !== undefined && (
                    <div className="text-xs text-muted-foreground flex items-center gap-2">
                      <DollarSign className="h-3 w-3" />
                      Order value: ${actualTask.customer.orderValue.toFixed(2)}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Task Notes Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Task Notes</h3>
              {hasStatusChanges && (
                <Button
                  size="sm"
                  onClick={saveTaskStatus}
                  disabled={savingStatus}
                  className="h-7 px-2"
                >
                  {savingStatus ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <>
                      <Check className="h-3 w-3 mr-1" />
                      Save
                    </>
                  )}
                </Button>
              )}
            </div>
            <textarea
              placeholder="Add notes about this task, customer interactions, or follow-up actions..."
              value={notes}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleNotesChange(e.target.value)}
              className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
              disabled={savingStatus}
            />
            {completed && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="h-4 w-4 text-green-600" />
                <span>This task has been marked as completed</span>
              </div>
            )}
          </div>

          {/* Task-specific recommendations */}
          {actualTask.type === 'purchase' && (
            <div className="space-y-4 border-t pt-4">
              <h3 className="font-semibold text-lg">Recommended Actions</h3>
              <div className="space-y-3">
                <div className="p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Thank You Email</h4>
                  <p className="text-sm text-muted-foreground">
                    Send a personalized thank you email acknowledging their purchase. Include order details and expected delivery information.
                  </p>
                </div>
                
                {parseFloat(actualTask.customer.orderValue?.toString() || '0') > 2000 && (
                  <div className="p-4 bg-purple-50 dark:bg-purple-950/20 rounded-lg space-y-2">
                    <h4 className="font-medium text-sm">VIP Customer Outreach</h4>
                    <p className="text-sm text-muted-foreground">
                      This is a high-value customer. Consider a personal phone call to ensure satisfaction and discuss bulk ordering options or exclusive deals.
                    </p>
                  </div>
                )}
                
                <div className="p-4 bg-green-50 dark:bg-green-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Cross-sell Opportunities</h4>
                  <p className="text-sm text-muted-foreground">
                    Based on their purchase, recommend complementary products or accessories. Consider offering a discount on their next purchase.
                  </p>
                </div>
              </div>
            </div>
          )}

          {actualTask.type === 'cart' && (
            <div className="space-y-4 border-t pt-4">
              <h3 className="font-semibold text-lg">Recommended Actions</h3>
              <div className="space-y-3">
                <div className="p-4 bg-orange-50 dark:bg-orange-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Cart Recovery Email</h4>
                  <p className="text-sm text-muted-foreground">
                    Send a friendly reminder about their abandoned cart. Include images of the products and a direct link to complete their purchase.
                  </p>
                </div>
                
                <div className="p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Limited-time Discount</h4>
                  <p className="text-sm text-muted-foreground">
                    Offer a time-limited discount (10-15%) to encourage purchase completion. Create urgency with a 48-hour expiration.
                  </p>
                </div>
                
                <div className="p-4 bg-purple-50 dark:bg-purple-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Customer Support Outreach</h4>
                  <p className="text-sm text-muted-foreground">
                    Reach out to ask if they encountered any issues during checkout or have questions about the products.
                  </p>
                </div>
              </div>
            </div>
          )}

          {actualTask.type === 'search' && (
            <div className="space-y-4 border-t pt-4">
              <h3 className="font-semibold text-lg">Recommended Actions</h3>
              <div className="space-y-3">
                <div className="p-4 bg-yellow-50 dark:bg-yellow-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Product Catalog Review</h4>
                  <p className="text-sm text-muted-foreground">
                    Review if the searched products exist in your catalog. If not, consider adding them or creating a notification system for when they become available.
                  </p>
                </div>
                
                <div className="p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Search Optimization</h4>
                  <p className="text-sm text-muted-foreground">
                    Improve search results by adding synonyms, related terms, and better product descriptions to help customers find what they're looking for.
                  </p>
                </div>
                
                <div className="p-4 bg-green-50 dark:bg-green-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Personal Outreach</h4>
                  <p className="text-sm text-muted-foreground">
                    Contact the customer directly to help them find the products they were searching for or suggest alternatives.
                  </p>
                </div>
              </div>
            </div>
          )}

          {actualTask.type === 'visit' && (
            <div className="space-y-4 border-t pt-4">
              <h3 className="font-semibold text-lg">Recommended Actions</h3>
              <div className="space-y-3">
                <div className="p-4 bg-purple-50 dark:bg-purple-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Engagement Email</h4>
                  <p className="text-sm text-muted-foreground">
                    Send a personalized email highlighting products they viewed or categories they browsed, with special offers to encourage conversion.
                  </p>
                </div>
                
                <div className="p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Loyalty Program Invitation</h4>
                  <p className="text-sm text-muted-foreground">
                    Invite frequent visitors to join your loyalty program with exclusive benefits and early access to new products.
                  </p>
                </div>
                
                <div className="p-4 bg-green-50 dark:bg-green-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Personal Shopping Assistant</h4>
                  <p className="text-sm text-muted-foreground">
                    Offer personal shopping assistance via chat or phone to help them find exactly what they need.
                  </p>
                </div>
              </div>
            </div>
          )}

          {actualTask.type === 'performance' && (
            <div className="space-y-4 border-t pt-4">
              <h3 className="font-semibold text-lg">Recommended Actions</h3>
              <div className="space-y-3">
                <div className="p-4 bg-red-50 dark:bg-red-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Technical Investigation</h4>
                  <p className="text-sm text-muted-foreground">
                    Investigate the technical issues causing poor performance. Check page load times, form validation errors, and mobile responsiveness.
                  </p>
                </div>
                
                <div className="p-4 bg-orange-50 dark:bg-orange-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">User Experience Audit</h4>
                  <p className="text-sm text-muted-foreground">
                    Conduct a UX audit of the problematic pages. Simplify forms, improve navigation, and ensure clear calls-to-action.
                  </p>
                </div>
                
                <div className="p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg space-y-2">
                  <h4 className="font-medium text-sm">Follow-up Communication</h4>
                  <p className="text-sm text-muted-foreground">
                    Reach out to affected users with an apology and assistance, possibly offering a discount for the inconvenience.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Current order details for purchase tasks */}
          {actualTask.type === 'purchase' && actualTask.productDetails && actualTask.productDetails.length > 0 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Current Order Details</h3>
              <div className="space-y-2 p-4 bg-muted/30 rounded-lg">
                {actualTask.productDetails.map((product, idx) => (
                  <div key={idx} className="flex justify-between items-center">
                    <div className="flex-1">
                      <p className="font-medium text-sm">{product.name}</p>
                      {product.sku && (
                        <p className="text-xs text-muted-foreground">SKU: {product.sku}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="text-sm">{product.quantity} × ${(product.price || 0).toFixed(2)}</p>
                      <p className="text-xs font-medium">${((product.quantity || 0) * (product.price || 0)).toFixed(2)}</p>
                    </div>
                  </div>
                ))}
                <div className="pt-2 mt-2 border-t flex justify-between">
                  <span className="font-semibold">Total</span>
                  <span className="font-semibold">${actualTask.customer.orderValue?.toFixed(2)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Current search terms for search tasks */}
          {actualTask.type === 'search' && actualTask.metadata?.searchTerms && actualTask.metadata.searchTerms.length > 0 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Current Search Terms</h3>
              <div className="space-y-2 p-4 bg-muted/30 rounded-lg">
                {actualTask.metadata.searchTerms.map((term, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <Search className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium text-sm">{term}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Current cart items for cart abandonment tasks */}
          {actualTask.type === 'cart' && actualTask.productDetails && actualTask.productDetails.length > 0 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Abandoned Cart Items</h3>
              <div className="space-y-2 p-4 bg-muted/30 rounded-lg">
                {actualTask.productDetails.map((product, idx) => (
                  <div key={idx} className="flex justify-between items-center">
                    <div className="flex-1">
                      <p className="font-medium text-sm">{product.name}</p>
                      {product.sku && (
                        <p className="text-xs text-muted-foreground">SKU: {product.sku}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="text-sm">{product.quantity} × ${(product.price || 0).toFixed(2)}</p>
                      <p className="text-xs font-medium">${((product.quantity || 0) * (product.price || 0)).toFixed(2)}</p>
                    </div>
                  </div>
                ))}
                <div className="pt-2 mt-2 border-t flex justify-between">
                  <span className="font-semibold">Cart Total</span>
                  <span className="font-semibold">${(actualTask.metadata?.cartValue || actualTask.customer.orderValue || 0).toFixed(2)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Customer History - Real data only */}
          <div className="space-y-3">
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Customer Activity History</h3>
              <p className="text-xs text-muted-foreground mt-1">Showing activity for {actualTask.customer.name}</p>
            </div>
            <Tabs defaultValue={actualTask.type === 'cart' ? 'purchases' : 'searches'} className="w-full">
              <TabsList className={cn(
                "grid w-full h-9",
                actualTask.type === 'purchase' && "grid-cols-3",
                actualTask.type === 'cart' && "grid-cols-3"
              )}>
                {actualTask.type === 'purchase' && (
                  <>
                    <TabsTrigger value="searches" className="text-xs">Searches</TabsTrigger>
                    <TabsTrigger value="carts" className="text-xs">Carts</TabsTrigger>
                    <TabsTrigger value="products" className="text-xs">Products</TabsTrigger>
                  </>
                )}
                {actualTask.type === 'cart' && (
                  <>
                    <TabsTrigger value="purchases" className="text-xs">Purchases</TabsTrigger>
                    <TabsTrigger value="searches" className="text-xs">Searches</TabsTrigger>
                    <TabsTrigger value="products" className="text-xs">Products</TabsTrigger>
                  </>
                )}
              </TabsList>

              <div className="mt-4 min-h-[200px]">
                {actualTask.type === 'cart' && (
                  <TabsContent value="purchases" className="mt-0">
                    {loading ? (
                      <div className="text-center py-8">
                        <p className="text-sm text-muted-foreground">Loading...</p>
                      </div>
                    ) : userHistory.purchaseHistory.length > 0 ? (
                      <div className="space-y-3">
                        {userHistory.purchaseHistory.slice(0, 5).map((purchase, i) => (
                          <div key={i} className="p-4 rounded-lg bg-muted/30 space-y-2">
                            <div className="flex justify-between items-start mb-2">
                              <div>
                                <p className="text-xs text-muted-foreground">
                                  {purchase.event_date ? new Date(
                                    purchase.event_date.slice(0, 4) + '-' + 
                                    purchase.event_date.slice(4, 6) + '-' + 
                                    purchase.event_date.slice(6, 8)
                                  ).toLocaleDateString('en-US', { 
                                    month: 'short', 
                                    day: 'numeric',
                                    year: 'numeric'
                                  }) : 'Unknown date'}
                                </p>
                                <p className="text-xs text-muted-foreground">Order #{purchase.transaction_id}</p>
                              </div>
                              <span className="text-sm font-semibold">${parseFloat(purchase.order_value).toFixed(2)}</span>
                            </div>
                            <div className="space-y-1">
                              {Array.isArray(purchase.items) ? (
                                purchase.items.slice(0, 3).map((item, idx) => (
                                  <div key={idx} className="flex justify-between items-start text-sm">
                                    <div className="flex-1">
                                      <p className="font-medium">{item.name}</p>
                                    </div>
                                    <div className="text-right">
                                      <p className="text-xs">{item.quantity} × ${(item.price || 0).toFixed(2)}</p>
                                    </div>
                                  </div>
                                ))
                              ) : typeof purchase.items === 'string' ? (
                                <p className="text-sm text-muted-foreground">{purchase.items}</p>
                              ) : null}
                              {Array.isArray(purchase.items) && purchase.items.length > 3 && (
                                <p className="text-xs text-muted-foreground">+{purchase.items.length - 3} more items</p>
                              )}
                            </div>
                          </div>
                        ))}
                        {userHistory.purchaseHistory.length > 5 && (
                          <p className="text-xs text-muted-foreground text-center">
                            Showing 5 of {userHistory.purchaseHistory.length} purchases
                          </p>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <p className="text-sm text-muted-foreground">No purchase history</p>
                      </div>
                    )}
                  </TabsContent>
                )}

                {(actualTask.type === 'purchase' || actualTask.type === 'cart') && (
                  <TabsContent value="searches" className="mt-0">
                    {loading ? (
                      <div className="text-center py-8">
                        <p className="text-sm text-muted-foreground">Loading...</p>
                      </div>
                    ) : userHistory.searchHistory.length > 0 ? (
                      <div className="space-y-2">
                        {userHistory.searchHistory.map((search, i) => (
                          <div key={i} className="p-3 rounded-lg bg-muted/30">
                            <div className="flex justify-between items-center gap-3">
                              <div className="flex-1">
                                <p className="text-sm font-medium">{search.term}</p>
                                <p className="text-xs text-muted-foreground mt-1">
                                  {search.date ? new Date(
                                    search.date.slice(0, 4) + '-' + 
                                    search.date.slice(4, 6) + '-' + 
                                    search.date.slice(6, 8)
                                  ).toLocaleDateString('en-US', { 
                                    month: 'short', 
                                    day: 'numeric',
                                    year: 'numeric'
                                  }) : 'Unknown date'}
                                </p>
                              </div>
                              <Badge 
                                variant={search.results > 0 ? "secondary" : "outline"} 
                                className={cn(
                                  "text-xs whitespace-nowrap",
                                  search.results === 0 && "text-muted-foreground"
                                )}
                              >
                                {search.results === 0 ? 'No results' : `${search.results} result${search.results !== 1 ? 's' : ''}`}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <p className="text-sm text-muted-foreground">No search history</p>
                      </div>
                    )}
                  </TabsContent>
                )}

                {actualTask.type === 'purchase' && (
                  <TabsContent value="carts" className="mt-0">
                    {loading ? (
                      <div className="text-center py-8">
                        <p className="text-sm text-muted-foreground">Loading...</p>
                      </div>
                    ) : userHistory.cartHistory.length > 0 ? (
                      <div className="space-y-3">
                        {userHistory.cartHistory.map((cart, i) => (
                          <div key={i} className="p-4 rounded-lg bg-muted/30 space-y-2">
                            <div className="flex justify-between items-start mb-2">
                              <p className="text-xs text-muted-foreground">
                                {cart.event_date ? new Date(
                                  cart.event_date.slice(0, 4) + '-' + 
                                  cart.event_date.slice(4, 6) + '-' + 
                                  cart.event_date.slice(6, 8)
                                ).toLocaleDateString('en-US', { 
                                  month: 'short', 
                                  day: 'numeric',
                                  year: 'numeric'
                                }) : 'Unknown date'}
                              </p>
                              <span className="text-sm font-semibold">${(cart.cart_value || 0).toFixed(2)}</span>
                            </div>
                            <div className="space-y-1">
                              {Array.isArray(cart.items) ? (
                                cart.items.map((item, idx) => (
                                  <div key={idx} className="flex justify-between items-start text-sm">
                                    <div className="flex-1">
                                      <p className="font-medium">{item.name}</p>
                                    </div>
                                    <div className="text-right">
                                      <p>{item.quantity} × ${(item.price || 0).toFixed(2)}</p>
                                      <p className="text-xs text-muted-foreground">${((item.quantity || 0) * (item.price || 0)).toFixed(2)}</p>
                                    </div>
                                  </div>
                                ))
                              ) : (
                                <p className="text-sm text-muted-foreground">Cart items</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <p className="text-sm text-muted-foreground">No cart history</p>
                      </div>
                    )}
                  </TabsContent>
                )}

                <TabsContent value="products" className="mt-0">
                  {loading ? (
                    <div className="text-center py-8">
                      <p className="text-sm text-muted-foreground">Loading...</p>
                    </div>
                  ) : userHistory.viewedProductsHistory.length > 0 ? (
                    <div className="space-y-2">
                      {userHistory.viewedProductsHistory.map((product, i) => (
                        <div key={i} className="p-3 rounded-lg bg-muted/30">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <p className="font-medium text-sm">{product.name}</p>
                              {product.category && (
                                <p className="text-xs text-muted-foreground">{product.category}</p>
                              )}
                              {product.sku && (
                                <p className="text-xs text-muted-foreground">SKU: {product.sku}</p>
                              )}
                            </div>
                            <div className="text-right">
                              <Badge variant="outline" className="text-xs">
                                {product.view_count} view{product.view_count !== 1 ? 's' : ''}
                              </Badge>
                              {product.price > 0 && (
                                <p className="text-xs text-muted-foreground mt-1">${(product.price || 0).toFixed(2)}</p>
                              )}
                            </div>
                          </div>
                                                     <p className="text-xs text-muted-foreground mt-2">
                             Last viewed: {product.last_viewed_date ? new Date(
                               product.last_viewed_date.slice(0, 4) + '-' + 
                               product.last_viewed_date.slice(4, 6) + '-' + 
                               product.last_viewed_date.slice(6, 8)
                             ).toLocaleDateString('en-US', { 
                               year: 'numeric', 
                               month: 'short', 
                               day: 'numeric' 
                             }) : 'Unknown date'}
                           </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <p className="text-sm text-muted-foreground">No product view history</p>
                    </div>
                  )}
                </TabsContent>
              </div>
            </Tabs>
          </div>
        </div>


      </SheetContent>
    </Sheet>
  )
} 