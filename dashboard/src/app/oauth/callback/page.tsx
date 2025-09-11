"use client"

import { Suspense, useEffect, useState, useRef } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Loader2, Check, AlertCircle, ShieldAlert, User } from "lucide-react"
import { authenticateWithCode, fetchDataAvailability } from "@/lib/api-utils"
import { useUser } from "@/contexts/user-context"

type Status = "working" | "success" | "error"

export const dynamic = "force-dynamic"

interface AuthResponse {
  success: boolean
  message: string
  tenant_id?: string
  first_name?: string
  username?: string
  access_token?: string
  missing_configs?: string[]
  invalid_configs?: string[]
}

async function checkDataAvailability(): Promise<{ hasData: boolean }> {
  try {
    const resp = await fetchDataAvailability()
    if (!resp.ok) return { hasData: false }
    const data = await resp.json()
    
    // Check if there's any data available (summary should have total_events > 0)
    const hasData = data?.summary?.total_events > 0
    return { hasData: Boolean(hasData) }
  } catch {
    return { hasData: false }
  }
}


function OAuthCallbackContent() {
  const router = useRouter()
  const params = useSearchParams()
  const { setUser } = useUser()
  const [status, setStatus] = useState<Status>("working")
  const [message, setMessage] = useState("Verifying your account…")
  const [tenantId, setTenantId] = useState<string | null>(null)
  const [configOk, setConfigOk] = useState<boolean | null>(null)
  const [configIssues, setConfigIssues] = useState<string[]>([])
  const [hasData, setHasData] = useState<boolean | null>(null)
  const [userInfo, setUserInfo] = useState<{ firstName?: string; username?: string } | null>(null)
  const authRequestMade = useRef(false)

  useEffect(() => {
    // Get values immediately at the start
    const code = params.get("code")
    const error = params.get("error")
    const errorDescription = params.get("error_description")
    const currentRouter = router
    const currentSetUser = setUser

    if (error) {
      setStatus("error")
      setMessage(`${error}: ${errorDescription || "Authorization was denied"}`)
      return
    }
    if (!code) {
      setStatus("error")
      setMessage("Missing authorization code in callback URL")
      return
    }

    // Prevent multiple executions
    if (authRequestMade.current) {
      return
    }
    authRequestMade.current = true
    
    let cancelled = false
    ;(async () => {
      try {
        setMessage("Verifying your account…")
        
        // Call the authentication API
        const response = await authenticateWithCode(code)
        if (cancelled) return
        
        if (!response.ok) {
          let detail = ""
          try { 
            const errorData = await response.json()
            detail = errorData?.detail || errorData?.message || "" 
          } catch {}
          throw new Error(detail || "Authentication failed")
        }
        
        const authResult: AuthResponse = await response.json()
        if (cancelled) return
        
        // Handle authentication response
        if (!authResult.success) {
          // Check if it's a configuration issue (not a hard failure)
          if (authResult.missing_configs || authResult.invalid_configs) {
            setStatus("error")
            const issues = [
              ...(authResult.missing_configs || []).map((config: string) => `Missing: ${config}`),
              ...(authResult.invalid_configs || []).map((config: string) => `Invalid: ${config}`)
            ]
            setConfigIssues(issues)
            setMessage("Verification complete, but setup issues detected")
            setTenantId(authResult.tenant_id || null)
            const userInfo = { firstName: authResult.first_name || undefined, username: authResult.username || undefined }
            setUserInfo(userInfo)
            
            // Store user info in global context even with config issues
            currentSetUser({
              firstName: authResult.first_name,
              username: authResult.username,
              tenantId: authResult.tenant_id
            })
            return
          } else {
            // Hard authentication failure
            throw new Error(authResult.message || "Authentication failed")
          }
        }
        
        // Successful authentication
        const tId = authResult.tenant_id
        setTenantId(tId || null)
        const userInfo = { firstName: authResult.first_name || undefined, username: authResult.username || undefined }
        setUserInfo(userInfo)
        
        // Store user info in global context
        currentSetUser({
          firstName: authResult.first_name,
          username: authResult.username,
          tenantId: tId,
          accessToken: authResult.access_token
        })

        // Since auth service already validated configurations, we can proceed
        if (tId) {
          setConfigOk(true)
          
          // Check data availability
          const dataCheck = await checkDataAvailability()
          setHasData(dataCheck.hasData)

          if (dataCheck.hasData) {
            setStatus("success")
            setMessage("Setup complete. Redirecting to dashboard…")
            setTimeout(() => currentRouter.replace("/"), 1200)
          } else {
            setStatus("success")
            setMessage("Verification complete. Redirecting to data management…")
            setTimeout(() => currentRouter.replace("/data-management"), 1200)
          }
        } else {
          setStatus("success")
          setMessage("Verification complete. Redirecting…")
          setTimeout(() => currentRouter.replace("/"), 1200)
        }
      } catch (err: unknown) {
        if (cancelled) return
        const msg = err instanceof Error ? err.message : "Unexpected error during OAuth"
        setStatus("error")
        setMessage(msg)
      }
    })()

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Empty dependency array to ensure it only runs once

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Account verification & setup</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {status === "working" && (
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>{message}</span>
            </div>
          )}

          {status === "success" && (
            <div className="space-y-3">
              <div className="flex items-center gap-3 text-sm text-green-600">
                <Check className="h-4 w-4" />
                <span>{message}</span>
              </div>

              {userInfo && (
                <div className="rounded-md border p-3">
                  <div className="flex items-center gap-3">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <div className="text-sm">
                      <div className="font-medium">Signed in as {userInfo.firstName || userInfo.username}</div>
                      {userInfo.firstName && userInfo.username && (
                        <div className="text-xs text-muted-foreground">{userInfo.username}</div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Config issues (when configOk === false) */}
              {configOk === false && configIssues.length > 0 && (
                <Alert variant="destructive">
                  <ShieldAlert className="h-4 w-4" />
                  <AlertTitle>Configuration Issues</AlertTitle>
                  <AlertDescription>
                    <p className="mb-2">Please fix the following configuration issues:</p>
                    <ul className="list-disc pl-5 space-y-1">
                      {configIssues.map((issue, i) => (
                        <li key={i}>{issue}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {/* Info message when config is ok but no data available */}
              {configOk && hasData === false && (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    No data found. You'll be redirected to the data management page to set up your initial data sync.
                  </p>
                </div>
              )}
            </div>
          )}

          {status === "error" && (
            <>
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>
                  {configIssues.length > 0 ? "Setup issues" : "Verification failed"}
                </AlertTitle>
                <AlertDescription>
                  {configIssues.length > 0 ? (
                    <div>
                      <p className="mb-2">{message}</p>
                      <p className="mb-2">Please fix the following issues:</p>
                      <ul className="list-disc pl-5 space-y-1">
                        {configIssues.map((issue, i) => (
                          <li key={i}>{issue}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    message
                  )}
                </AlertDescription>
              </Alert>
              {configIssues.length > 0 ? (
                <div className="flex gap-2">
                  <Button onClick={() => router.replace("/")}>Go to dashboard anyway</Button>
                  <Button variant="outline" onClick={() => router.back()}>Back</Button>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground mt-3">
                  Please close this window and try signing in again.
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[60vh] flex items-center justify-center p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>OAuth Callback</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Loading…</span>
              </div>
            </CardContent>
          </Card>
        </div>
      }
    >
      <OAuthCallbackContent />
    </Suspense>
  )
}


