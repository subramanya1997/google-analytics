"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useUser } from "@/contexts/user-context"
import { Loader2 } from "lucide-react"

interface AuthGuardProps {
  children: React.ReactNode
  redirectTo?: string
}

export function AuthGuard({ children, redirectTo = "/oauth/login" }: AuthGuardProps) {
  const { user, isAuthenticated, isValidating, isLoading } = useUser()
  const router = useRouter()

  useEffect(() => {
    // Check if we're on the client side
    if (typeof window === 'undefined') return

    // Don't redirect while loading initial session or validating
    if (isLoading || isValidating) return

    // If no user data at all after loading is complete, redirect to login
    if (!user) {
      console.log('No user found after loading, redirecting to login')
      router.replace(redirectTo)
      return
    }

    // If user exists but is not properly authenticated (missing token or tenant), redirect to login
    if (!isAuthenticated) {
      console.log('User not authenticated, redirecting to login')
      router.replace(redirectTo)
      return
    }
  }, [user, isAuthenticated, isValidating, isLoading, router, redirectTo])

  // Show loading while loading initial session or validating
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading session...</p>
        </div>
      </div>
    )
  }

  // Show loading while validating session
  if (isValidating) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Validating session...</p>
        </div>
      </div>
    )
  }

  // Show loading while checking authentication (after loading is complete but no user)
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Redirecting to login...</p>
        </div>
      </div>
    )
  }

  // Show loading if user exists but not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Redirecting to login...</p>
        </div>
      </div>
    )
  }

  // User is authenticated, render the children
  return <>{children}</>
}
