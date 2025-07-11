"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet"
import {
  LayoutDashboard,
  ShoppingCart,
  Search,
  Users,
  AlertCircle,
  Package,
  BarChart3,
  ShoppingBag,
  Menu,
  X,
} from "lucide-react"

interface NavigationItem {
  name: string
  href: string
  icon: any
}

const navigation: NavigationItem[] = [
  {
    name: "Overview",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    name: "Purchases",
    href: "/purchases",
    icon: ShoppingBag,
  },
  {
    name: "Cart Abandonment",
    href: "/cart-abandonment",
    icon: ShoppingCart,
  },
  {
    name: "Search Analysis",
    href: "/search-analysis",
    icon: Search,
  },
  {
    name: "Repeat Visits",
    href: "/repeat-visits",
    icon: Users,
  },
  {
    name: "Performance",
    href: "/performance",
    icon: AlertCircle,
  },
]

function SidebarContent({ pathname, onItemClick }: { pathname: string; onItemClick?: () => void }) {
  return (
    <nav className="flex-1 space-y-1 p-4">
      {navigation.map((item) => {
        const isActive = pathname === item.href
        return (
          <Link
            key={item.name}
            href={item.href}
            onClick={onItemClick}
            className={cn(
              "flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-primary text-primary-foreground"
                : "hover:bg-accent hover:text-accent-foreground"
            )}
          >
            <div className="flex items-center gap-3">
              <item.icon className="h-4 w-4" />
              <span>{item.name}</span>
            </div>
          </Link>
        )
      })}
    </nav>
  )
}

export function Sidebar() {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <>
      {/* Mobile Sidebar */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetTrigger asChild className="lg:hidden">
          <Button variant="ghost" size="icon" className="fixed top-4 left-4 z-50">
            <Menu className="h-5 w-5" />
            <span className="sr-only">Toggle menu</span>
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 p-0">
          <div className="flex h-16 items-center px-6 border-b">
            <SheetTitle className="text-lg font-semibold">impaqx Analytics</SheetTitle>
          </div>
          <SidebarContent pathname={pathname} onItemClick={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      {/* Desktop Sidebar */}
      <div className="hidden lg:flex h-full w-64 flex-col bg-card border-r">
        <div className="flex h-16 items-center px-6 border-b">
          <h2 className="text-lg font-semibold">impaqx Analytics</h2>
        </div>
        <SidebarContent pathname={pathname} />
      </div>
    </>
  )
} 