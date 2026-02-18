"use client"

import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Task, TaskDetailSheetProps, UserHistory, PurchaseHistoryItem } from "@/types"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  User, 
  Mail, 
  Phone, 
  MonitorSmartphone,
  Package,
  Search,
  ShoppingCart,
  TrendingUp,
  AlertCircle,
  Loader2,
  Calendar
} from "lucide-react"
import { useState, useMemo } from "react"
import { cn } from "@/lib/utils"
import { fetchUserHistory } from "@/lib/api-utils"

// Skeleton loading components
const TabSkeleton = () => (
  <div className="space-y-3">
    {[...Array(3)].map((_, i) => (
      <div key={i} className="p-4 rounded-lg bg-muted/30 animate-pulse">
        <div className="h-4 bg-muted rounded w-3/4 mb-2"></div>
        <div className="h-3 bg-muted rounded w-1/2"></div>
      </div>
    ))}
  </div>
)

const PurchaseSkeleton = () => (
  <div className="space-y-3">
    {[...Array(3)].map((_, i) => (
      <div key={i} className="p-4 rounded-lg bg-muted/30 animate-pulse">
        <div className="flex justify-between items-start mb-2">
          <div className="space-y-2">
            <div className="h-3 bg-muted rounded w-20"></div>
            <div className="h-3 bg-muted rounded w-24"></div>
          </div>
          <div className="h-4 bg-muted rounded w-16"></div>
        </div>
        <div className="space-y-2">
          <div className="h-3 bg-muted rounded w-full"></div>
          <div className="h-3 bg-muted rounded w-3/4"></div>
        </div>
      </div>
    ))}
  </div>
)

// Type alias for the actual task structure used in this component
type ActualTask = Task

export function TaskDetailSheet({ task, children }: TaskDetailSheetProps) {
  const [userHistory, setUserHistory] = useState<UserHistory>({
    user: null,
    purchaseHistory: [],
    searchHistory: [],
    cartHistory: [],
    viewedProductsHistory: []
  })
  const [loading, setLoading] = useState(false)
  
  // Add lazy loading state for tabs
  const [activeTab, setActiveTab] = useState<string>('')
  const [loadedTabs, setLoadedTabs] = useState<Set<string>>(new Set())
  const [tabLoadingStates, setTabLoadingStates] = useState<Record<string, boolean>>({})
  
  // Cast task to actual structure
  const actualTask = task as unknown as ActualTask

  const fetchUserHistoryData = async () => {
    // Check if we already have data cached
    if (userHistory.user || userHistory.purchaseHistory.length > 0) {
      return
    }
    
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
    
    const sessionId = actualTask.sessionId || null
    
    try {
      let response: Response | null = null
      
      // First try to fetch by userId if available
      if (userId || sessionId) {
        response = await fetchUserHistory(userId || undefined, sessionId || undefined)
      }

      if (response && response.ok) {
          const historyEvents = await response.json()
          // Process the flat event list into categorized history
          const purchaseHistory: PurchaseHistoryItem[] = []
          const searchHistory: Array<{
            term: string
            date: string
            results: number
          }> = []
          const cartHistory: Array<{
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
          }> = []
          const viewedProductsHistory: Array<{
            sku: string
            name: string
            category: string
            price: number
            view_count: number
            last_viewed_date: string
            last_viewed_timestamp: string
          }> = []

          // Handle both array and single object response
          const eventsArray = Array.isArray(historyEvents) ? historyEvents : (historyEvents.data || [])

          eventsArray.forEach((event: {
            event_type: string
            param_ga_session_id?: string
            event_timestamp: number
            details: {
              transaction_id?: string
              revenue?: string
              items?: string
              search_term?: string
              page_location?: string
              page_title?: string
              item_name?: string
              item_id?: string
              category?: string
              price?: number
              quantity?: number
            }
          }) => {
            switch (event.event_type) {
              case 'purchase':
                purchaseHistory.push({
                  transaction_id: event.details.transaction_id || 'unknown',
                  event_date: new Date(event.event_timestamp / 1000).toISOString().split('T')[0].replace(/-/g, ''),
                  event_timestamp: event.event_timestamp.toString(),
                  order_value: event.details.revenue || '0',
                  items: JSON.parse(event.details.items || '[]')
                })
                break
              case 'add_to_cart':
                cartHistory.push({
                  session_id: event.param_ga_session_id || 'unknown',
                  event_date: new Date(event.event_timestamp / 1000).toISOString().split('T')[0].replace(/-/g, ''),
                  event_timestamp: event.event_timestamp.toString(),
                  cart_value: (event.details.price || 0) * (event.details.quantity || 0),
                  items: [{
                    name: event.details.item_name || 'Unknown Item',
                    sku: event.details.item_id || 'unknown',
                    quantity: event.details.quantity || 0,
                    price: event.details.price || 0
                  }]
                })
                break
              case 'view_search_results':
                searchHistory.push({
                  term: event.details.search_term || 'unknown',
                  date: new Date(event.event_timestamp / 1000).toISOString().split('T')[0].replace(/-/g, ''),
                  results: 1 // Placeholder
                })
                break
              case 'no_search_results':
                searchHistory.push({
                  term: event.details.search_term || 'unknown',
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
                     last_viewed_timestamp: event.event_timestamp.toString(),
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
                   last_viewed_timestamp: event.event_timestamp.toString(),
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
    } catch (error) {
      console.error('Error fetching user history:', error)
    }
    
    setLoading(false)
  }

  // Handle tab change with lazy loading
  const handleTabChange = (tab: string) => {
    setActiveTab(tab)
    
    // If this tab hasn't been loaded yet, mark it as loading
    if (!loadedTabs.has(tab)) {
      setTabLoadingStates(prev => ({ ...prev, [tab]: true }))
      
      // Simulate loading delay for better UX
      setTimeout(() => {
        setLoadedTabs(prev => new Set([...prev, tab]))
        setTabLoadingStates(prev => ({ ...prev, [tab]: false }))
      }, 100)
    }
  }

  // Handle open change
  const handleOpenChange = (open: boolean) => {
    if (open) {
      // Set initial active tab based on task type
      const initialTab = actualTask.type === 'cart' ? 'purchases' : 'searches'
      setActiveTab(initialTab)
      setLoadedTabs(new Set([initialTab]))
      
      fetchUserHistoryData()
    }
  }

  const getTaskIcon = () => {
    switch (actualTask.type) {
      case 'purchase': return TrendingUp
      case 'cart': return ShoppingCart
      case 'search': return Search
      case 'repeat_visit': return User
      case 'performance': return AlertCircle
      default: return Package
    }
  }

  const TaskIcon = getTaskIcon()

  const formatCurrency = (value: number): string => {
    try {
      return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
    } catch {
      return `$${(value ?? 0).toFixed(2)}`
    }
  }

  // Memoize processed data to avoid recalculating on every render
  const processedPurchaseHistory = useMemo(() => {
    return userHistory.purchaseHistory.slice(0, 5)
  }, [userHistory.purchaseHistory])

  const processedCartHistory = useMemo(() => {
    return userHistory.cartHistory.slice(0, 5)
  }, [userHistory.cartHistory])

  const processedSearchHistory = useMemo(() => {
    return userHistory.searchHistory.slice(0, 10)
  }, [userHistory.searchHistory])

  const processedViewedProducts = useMemo(() => {
    return userHistory.viewedProductsHistory.slice(0, 10)
  }, [userHistory.viewedProductsHistory])

  return (
    <Sheet onOpenChange={handleOpenChange}>
      <SheetTrigger asChild>
        {children}
      </SheetTrigger>
      <SheetContent className="w-full sm:w-[600px] sm:max-w-[600px] overflow-y-auto p-0">
        <SheetHeader className="p-6 pb-3 border-b">
          <div className="space-y-2">
            {/* Task icon and Customer name */}
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-muted">
                <TaskIcon className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <SheetTitle className="text-lg font-semibold">{actualTask.customer.name}</SheetTitle>
                  <Badge variant={
                    actualTask.priority === 'high' ? 'destructive' : 
                    actualTask.priority === 'medium' ? 'default' : 'secondary'
                  } className="px-2 py-0.5 text-xs rounded-full capitalize">
                    {actualTask.priority}
                  </Badge>
                </div>
                {actualTask.customer.company && (
                  <span className="text-sm text-muted-foreground">{actualTask.customer.company}</span>
                )}
              </div>
            </div>
            
            {/* Contact details and task info */}
            <div className="space-y-1">
              <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center text-sm gap-y-1 sm:gap-y-1">
                {actualTask.customer.email && (
                  <a 
                    href={`mailto:${actualTask.customer.email}`} 
                    className="text-muted-foreground hover:text-foreground hover:underline flex items-center gap-1 sm:before:mx-3 sm:first:before:hidden max-w-full sm:max-w-[260px] truncate"
                  >
                    <Mail className="h-3 w-3" />
                    {actualTask.customer.email}
                  </a>
                )}
                
                {actualTask.customer.phone && actualTask.customer.phone.trim() && (
                  <a 
                    href={`tel:${actualTask.customer.phone}`} 
                    className="text-muted-foreground hover:text-foreground hover:underline flex items-center gap-1 sm:before:mx-3 sm:first:before:hidden whitespace-nowrap"
                  >
                    <Phone className="h-3 w-3" />
                    {actualTask.customer.phone}
                  </a>
                )}

                {actualTask.customer.office_phone && actualTask.customer.office_phone.trim() && (
                  <a 
                    href={`tel:${actualTask.customer.office_phone}`} 
                    className="text-muted-foreground hover:text-foreground hover:underline flex items-center gap-1 sm:before:content-['•'] sm:before:mx-3 sm:first:before:hidden whitespace-nowrap"
                  >
                    <MonitorSmartphone className="h-3 w-3" />
                    {actualTask.customer.office_phone}
                  </a>
                )}
              </div>
              
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-sm font-medium text-muted-foreground">{actualTask.title}</span>
                {typeof actualTask.customer.orderValue === 'number' && (
                  <span className="text-sm font-semibold text-green-600">
                    {formatCurrency(actualTask.customer.orderValue)}
                  </span>
                )}
                {actualTask.createdAt && (
                  <span className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Calendar className="h-3 w-3" />
                    {new Date(actualTask.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </span>
                )}
              </div>
            </div>
          </div>
        </SheetHeader>

        <div className="p-6 space-y-4">
          {/* Current order details for purchase tasks */}
          {actualTask.type === 'purchase' && actualTask.productDetails && actualTask.productDetails.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-semibold">Current Order Details</h3>
              <div className="space-y-2 p-3 bg-muted/30 rounded-lg">
                {actualTask.productDetails.map((product, idx) => (
                  <div key={idx} className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1 sm:gap-0">
                    <div className="flex-1">
                      <p className="font-medium text-sm">{product.name}</p>
                      {product.sku && (
                        <p className="text-xs text-muted-foreground">SKU: {product.sku}</p>
                      )}
                    </div>
                    <div className="text-left sm:text-right">
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
            <div className="space-y-3">
              <h3 className="font-semibold">Current Search Terms</h3>
              <div className="space-y-2 p-3 bg-muted/30 rounded-lg">
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
            <div className="space-y-3">
              <h3 className="font-semibold">Abandoned Cart Items</h3>
              <div className="space-y-2 p-3 bg-muted/30 rounded-lg">
                {actualTask.productDetails.map((product, idx) => (
                  <div key={idx} className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1 sm:gap-0">
                    <div className="flex-1">
                      <p className="font-medium text-sm">{product.name}</p>
                      {product.sku && (
                        <p className="text-xs text-muted-foreground">SKU: {product.sku}</p>
                      )}
                    </div>
                    <div className="text-left sm:text-right">
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
            <div className="flex items-center justify-between">
              {loading && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Loading data...
                </div>
              )}
            </div>
            <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
              <TabsList className={cn(
                "grid w-full h-9 text-xs sm:text-sm",
                actualTask.type === 'purchase' && "grid-cols-3",
                actualTask.type === 'cart' && "grid-cols-3"
              )}>
                {actualTask.type === 'purchase' && (
                  <>
                    <TabsTrigger value="searches" className="text-xs sm:text-sm px-2 sm:px-3">Searches</TabsTrigger>
                    <TabsTrigger value="carts" className="text-xs sm:text-sm px-2 sm:px-3">Carts</TabsTrigger>
                    <TabsTrigger value="products" className="text-xs sm:text-sm px-2 sm:px-3">Products</TabsTrigger>
                  </>
                )}
                {actualTask.type === 'cart' && (
                  <>
                    <TabsTrigger value="purchases" className="text-xs sm:text-sm px-2 sm:px-3">Purchases</TabsTrigger>
                    <TabsTrigger value="searches" className="text-xs sm:text-sm px-2 sm:px-3">Searches</TabsTrigger>
                    <TabsTrigger value="products" className="text-xs sm:text-sm px-2 sm:px-3">Products</TabsTrigger>
                  </>
                )}
              </TabsList>

              <div className="mt-4 min-h-[200px]">
                {actualTask.type === 'cart' && (
                  <TabsContent value="purchases" className="mt-0">
                    {!loadedTabs.has('purchases') || tabLoadingStates['purchases'] ? (
                      <PurchaseSkeleton />
                    ) : loading ? (
                      <div className="text-center py-8">
                        <p className="text-sm text-muted-foreground">Loading...</p>
                      </div>
                    ) : processedPurchaseHistory.length > 0 ? (
                      <div className="space-y-3">
                        {processedPurchaseHistory.map((purchase, i) => (
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
                    {!loadedTabs.has('searches') || tabLoadingStates['searches'] ? (
                      <TabSkeleton />
                    ) : loading ? (
                      <div className="text-center py-8">
                        <p className="text-sm text-muted-foreground">Loading...</p>
                      </div>
                    ) : processedSearchHistory.length > 0 ? (
                      <div className="space-y-2">
                        {processedSearchHistory.map((search, i) => (
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
                    {!loadedTabs.has('carts') || tabLoadingStates['carts'] ? (
                      <PurchaseSkeleton />
                    ) : loading ? (
                      <div className="text-center py-8">
                        <p className="text-sm text-muted-foreground">Loading...</p>
                      </div>
                    ) : processedCartHistory.length > 0 ? (
                      <div className="space-y-3">
                        {processedCartHistory.map((cart, i) => (
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
                  {!loadedTabs.has('products') || tabLoadingStates['products'] ? (
                    <TabSkeleton />
                  ) : loading ? (
                    <div className="text-center py-8">
                      <p className="text-sm text-muted-foreground">Loading...</p>
                    </div>
                  ) : processedViewedProducts.length > 0 ? (
                    <div className="space-y-2">
                      {processedViewedProducts.map((product, i) => (
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