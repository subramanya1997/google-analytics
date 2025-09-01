"use client"

import { LayoutWrapper } from "@/components/layout-wrapper"

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return <LayoutWrapper>{children}</LayoutWrapper>
}


