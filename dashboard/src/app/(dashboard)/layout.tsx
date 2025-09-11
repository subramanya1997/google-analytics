"use client"

import { LayoutWrapper } from "@/components/layout-wrapper"
import { AuthGuard } from "@/components/auth-guard"

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <AuthGuard>
      <LayoutWrapper>{children}</LayoutWrapper>
    </AuthGuard>
  )
}


