import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { DashboardProvider } from "@/contexts/dashboard-context"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Impaqx Analytics Dashboard",
  description: "E-commerce analytics and customer engagement platform",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <DashboardProvider>
          {children}
        </DashboardProvider>
      </body>
    </html>
  )
}
