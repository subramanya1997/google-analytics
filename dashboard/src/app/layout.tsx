import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { DashboardProvider } from "@/contexts/dashboard-context"
import { UserProvider } from "@/contexts/user-context"

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
      <head>
        {/* Reduce connection setup to API origin in case proxy is not used */}
        {process.env.NEXT_PUBLIC_ANALYTICS_API_URL ? (
          <>
            <link rel="dns-prefetch" href={process.env.NEXT_PUBLIC_ANALYTICS_API_URL} />
            <link rel="preconnect" href={process.env.NEXT_PUBLIC_ANALYTICS_API_URL} crossOrigin="anonymous" />
          </>
        ) : null}
      </head>
      <body className={inter.className}>
        <UserProvider>
          <DashboardProvider>
            {children}
          </DashboardProvider>
        </UserProvider>
      </body>
    </html>
  )
}
