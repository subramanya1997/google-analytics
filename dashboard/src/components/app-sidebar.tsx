"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import {
  LayoutDashboard,
  ShoppingCart,
  Search,
  Users,
  AlertCircle,
  ShoppingBag,
} from "lucide-react"

const data = {
  navMain: [
    {
      title: "Overview",
      url: "/",
      icon: LayoutDashboard,
    },
    {
      title: "Purchases",
      url: "/purchases",
      icon: ShoppingBag,
    },
    {
      title: "Cart Abandonment",
      url: "/cart-abandonment",
      icon: ShoppingCart,
    },
    {
      title: "Search Analysis",
      url: "/search-analysis",
      icon: Search,
    },
    {
      title: "Repeat Visits",
      url: "/repeat-visits",
      icon: Users,
    },
    {
      title: "Performance",
      url: "/performance",
      icon: AlertCircle,
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname()

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <div className="flex items-center justify-between px-2 py-2 group-data-[collapsible=icon]:justify-center">
          <Link href="/" prefetch className="text-xl font-semibold tracking-tight group-data-[collapsible=icon]:hidden">
            Impaqx Analytics
          </Link>
          <SidebarTrigger className="ml-2 group-data-[collapsible=icon]:ml-0" />
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Application</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {data.navMain.map((item) => {
                const isActive = pathname === item.url
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild isActive={isActive}>
                      <Link href={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  )
}
