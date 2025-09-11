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
  SidebarFooter,
} from "@/components/ui/sidebar"
import { NavUser } from "@/components/nav-user"
import {
  LayoutDashboard,
  ShoppingCart,
  Search,
  Users,
  AlertCircle,
  ShoppingBag,
  Database,
  Mail,
} from "lucide-react"

const data = {
  navApplication: {
    label: "Application",
    items: [
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
  },
  navConfiguration: {
    label: "Configuration",
    items: [
      {
        title: "Data Management",
        url: "/data-management",
        icon: Database,
      },
      {
        title: "Email Management",
        url: "/email-management",
        icon: Mail,
      },
    ],
  }
}


export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname()

  // Get all navigation sections
  const navSections = [data.navApplication, data.navConfiguration]

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <div className="flex items-center justify-between px-2 py-2 group-data-[collapsible=icon]:justify-center">
          <Link href="/" prefetch className="text-xl font-semibold tracking-tight group-data-[collapsible=icon]:hidden">
            Impaqx Analytics
          </Link>
          <SidebarTrigger className="ml-2 group-data-[collapsible=icon]:ml-0 hidden md:flex" />
        </div>
      </SidebarHeader>
      <SidebarContent>
        {(() => {
          const sidebarGroups = []
          
          // Loop through each navigation section
          for (let i = 0; i < navSections.length; i++) {
            const section = navSections[i]
            const menuItems = []
            
            // Loop through each item in the section
            for (let j = 0; j < section.items.length; j++) {
              const item = section.items[j]
              const isActive = pathname === item.url
              
              menuItems.push(
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={isActive}>
                    <Link href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )
            }
            
            sidebarGroups.push(
              <SidebarGroup key={section.label}>
                <SidebarGroupLabel>{section.label}</SidebarGroupLabel>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {menuItems}
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            )
          }
          
          return sidebarGroups
        })()}
      </SidebarContent>
      <SidebarRail />
      <SidebarFooter>
        <NavUser />
      </SidebarFooter>
    </Sidebar>
  )
}
