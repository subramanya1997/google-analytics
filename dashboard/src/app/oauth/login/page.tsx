"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ShieldAlert, ExternalLink, Loader2 } from "lucide-react"
import { getLoginUrl } from "@/lib/api-utils"

export default function LoginPage() {
  const [loginUrl, setLoginUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchLoginUrl = async () => {
      try {
        setLoading(true)
        const response = await getLoginUrl()
        
        if (!response.ok) {
          throw new Error('Failed to fetch login URL')
        }
        
        const data = await response.json()
        setLoginUrl(data.login_url)
        
        // Auto-redirect after getting the URL
        setTimeout(() => {
          if (data.login_url) {
            window.location.href = data.login_url
          }
        }, 2000)
        
      } catch (err) {
        console.error('Error fetching login URL:', err)
        setError('Failed to get login URL')
        // Fallback to environment variable or default
        const fallbackUrl = process.env.NEXT_PUBLIC_OAUTH_LOGIN_URL || "/manage/auth/login"
        setLoginUrl(fallbackUrl)
        setTimeout(() => {
          window.location.href = fallbackUrl
        }, 2000)
      } finally {
        setLoading(false)
      }
    }

    fetchLoginUrl()
  }, [])

  const handleManualLogin = () => {
    if (loginUrl) {
      window.location.href = loginUrl
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
            <ShieldAlert className="h-6 w-6 text-blue-600" />
          </div>
          <CardTitle>Authentication Required</CardTitle>
          <CardDescription>
            You need to log in to access the analytics dashboard
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="text-center">
              <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">
                Getting login URL...
              </p>
            </div>
          ) : error ? (
            <div className="text-center">
              <p className="text-sm text-red-600 mb-4">{error}</p>
              <p className="text-sm text-muted-foreground">
                Redirecting to fallback login...
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center">
              Redirecting you to the login page...
            </p>
          )}
          
          <Button 
            onClick={handleManualLogin} 
            className="w-full"
            variant="default"
            disabled={!loginUrl}
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Continue to Login
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
