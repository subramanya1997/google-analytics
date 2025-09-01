"use client"

import { Suspense, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Loader2, Check, AlertCircle, Play, ShieldAlert } from "lucide-react"

type Status = "working" | "success" | "error"

export const dynamic = "force-dynamic"

async function exchangeOAuthCode(code: string, state?: string | null) {
  const authBase = process.env.NEXT_PUBLIC_AUTH_API_URL || ""
  const redirectUri = typeof window !== "undefined" ? `${window.location.origin}/oauth/callback` : ""
  const url = `${authBase}/v1/oauth/callback`

  const response = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, state, redirect_uri: redirectUri }),
  })

  if (!response.ok) {
    let detail = ""
    try { detail = (await response.json())?.message || "" } catch {}
    throw new Error(detail || "OAuth exchange failed")
  }

  // Response may set cookies; body content is optional
  try { return await response.json() } catch { return {} }
}

async function verifySession() {
  const authBase = process.env.NEXT_PUBLIC_AUTH_API_URL || ""
  const profileResp = await fetch(`${authBase}/v1/auth/me`, { credentials: "include" })
  if (!profileResp.ok) throw new Error("Session verification failed")
  return profileResp.json().catch(() => null)
}

// (Reserved) tenant status shape if we persist this state in the future

async function checkTenantConfig(tenantId: string): Promise<{ ok: boolean; issues: string[] }> {
  const authBase = process.env.NEXT_PUBLIC_AUTH_API_URL || ""
  try {
    const resp = await fetch(`${authBase}/v1/tenant/config/check?tenant_id=${encodeURIComponent(tenantId)}`, {
      credentials: "include",
    })
    if (!resp.ok) return { ok: false, issues: ["Configuration check failed"] }
    const data = await resp.json()
    const ok = (data && (data.ok ?? data.configured))
    return { ok: Boolean(ok), issues: Array.isArray(data?.issues) ? data.issues : [] }
  } catch {
    // Endpoint may not exist yet
    console.log("[oauth] config check endpoint unavailable; assuming ok for now")
    return { ok: true, issues: [] }
  }
}

async function getSyncStatus(tenantId: string): Promise<{ started: boolean }> {
  const authBase = process.env.NEXT_PUBLIC_AUTH_API_URL || ""
  try {
    const resp = await fetch(`${authBase}/v1/tenant/sync/status?tenant_id=${encodeURIComponent(tenantId)}`, {
      credentials: "include",
    })
    if (!resp.ok) return { started: false }
    const data = await resp.json()
    const started = (data && (data.started ?? data.syncStarted))
    return { started: Boolean(started) }
  } catch {
    console.log("[oauth] sync status endpoint unavailable; assuming not started")
    return { started: false }
  }
}

async function startSync(tenantId: string): Promise<boolean> {
  const authBase = process.env.NEXT_PUBLIC_AUTH_API_URL || ""
  try {
    const resp = await fetch(`${authBase}/v1/tenant/sync/start`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant_id: tenantId }),
    })
    return resp.ok
  } catch {
    console.log("[oauth] sync start endpoint unavailable")
    return false
  }
}

function OAuthCallbackContent() {
  const router = useRouter()
  const params = useSearchParams()
  const [status, setStatus] = useState<Status>("working")
  const [message, setMessage] = useState("Connecting your account…")
  const [tenantId, setTenantId] = useState<string | null>(null)
  const [configOk, setConfigOk] = useState<boolean | null>(null)
  const [configIssues, setConfigIssues] = useState<string[]>([])
  const [syncStarted, setSyncStarted] = useState<boolean | null>(null)
  const [startingSync, setStartingSync] = useState(false)

  useEffect(() => {
    const code = params.get("code")
    const state = params.get("state")
    const error = params.get("error")
    const errorDescription = params.get("error_description")

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

    let cancelled = false
    ;(async () => {
      try {
        setMessage("Finalizing sign-in…")
        await exchangeOAuthCode(code, state)
        const profile = await verifySession().catch(() => null)
        if (cancelled) return
        const tId = profile?.tenant_id || profile?.tenantId
        setTenantId(tId || null)
        console.log("[oauth] verified profile:", profile)

        // Config checks first
        if (tId) {
          const cfg = await checkTenantConfig(tId)
          setConfigOk(cfg.ok)
          setConfigIssues(cfg.issues)

          if (!cfg.ok) {
            setStatus("error")
            setMessage("Tenant configuration issues detected")
            return
          }

          // Sync status
          const sync = await getSyncStatus(tId)
          setSyncStarted(sync.started)

          if (sync.started) {
            setStatus("success")
            setMessage("Setup complete. Redirecting to dashboard…")
            setTimeout(() => router.replace("/"), 1200)
          } else {
            setStatus("success")
            setMessage("Configuration valid. You can start the initial data sync.")
          }
        } else {
          setStatus("success")
          setMessage("Connected. Redirecting…")
          setTimeout(() => router.replace("/"), 1200)
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
  }, [params, router])

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>OAuth Callback</CardTitle>
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

              {/* Config issues (when configOk === false) */}
              {configOk === false && (
                <Alert variant="destructive">
                  <ShieldAlert className="h-4 w-4" />
                  <AlertTitle>Configuration required</AlertTitle>
                  <AlertDescription>
                    {configIssues.length > 0 ? (
                      <ul className="list-disc pl-5 space-y-1">
                        {configIssues.map((issue, i) => (
                          <li key={i}>{issue}</li>
                        ))}
                      </ul>
                    ) : (
                      <span>We found issues with your tenant configuration.</span>
                    )}
                  </AlertDescription>
                </Alert>
              )}

              {/* Sync controls when config is ok but sync not started */}
              {configOk && syncStarted === false && (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    We will initiate your first data sync. This can take a few minutes. Please check back shortly.
                  </p>
                  <div className="flex gap-2">
                    <Button
                      onClick={async () => {
                        if (!tenantId) return
                        setStartingSync(true)
                        const ok = await startSync(tenantId)
                        setStartingSync(false)
                        if (ok) {
                          console.log("[oauth] sync started for", tenantId)
                          setSyncStarted(true)
                          setMessage("Sync initiated. Redirecting to dashboard…")
                          setTimeout(() => router.replace("/"), 1500)
                        } else {
                          setStatus("error")
                          setMessage("Failed to start sync. Please try again or contact support.")
                        }
                      }}
                      disabled={startingSync}
                    >
                      {startingSync ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin mr-2" /> Starting…
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4 mr-2" /> Start Sync
                        </>
                      )}
                    </Button>
                    <Button variant="outline" onClick={() => router.replace("/")}>Skip for now</Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {status === "error" && (
            <>
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Authentication failed</AlertTitle>
                <AlertDescription>{message}</AlertDescription>
              </Alert>
              <div className="flex gap-2">
                <Button onClick={() => router.replace("/")}>Go to dashboard</Button>
                <Button variant="outline" onClick={() => router.back()}>Back</Button>
              </div>
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


