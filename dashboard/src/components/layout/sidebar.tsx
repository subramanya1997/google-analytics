"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  ShoppingCart,
  Search,
  Users,
  AlertCircle,
  Package,
  BarChart3,
  ShoppingBag,
} from "lucide-react"

interface NavigationItem {
  name: string
  href: string
  icon: any
}

export function Sidebar() {
  const pathname = usePathname()

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

  return (
    <div className="flex h-full w-64 flex-col bg-card border-r">
      <div className="flex h-16 items-center px-6 border-b">
        <h2 className="text-lg font-semibold">Impax Analytics</h2>
      </div>
      <nav className="flex-1 space-y-1 p-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
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
    </div>
  )
} 