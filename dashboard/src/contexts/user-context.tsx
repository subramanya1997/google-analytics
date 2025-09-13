"use client"

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { logoutWithToken, getLoginUrl, validateToken } from '@/lib/api-utils'

// ============================================================================
// Constants
// ============================================================================

const SESSION_TIMEOUTS = {
  MAX_AGE: 24 * 60 * 60 * 1000,           // 24 hours - maximum session age
  VALIDATE_ON_LOAD: 60 * 60 * 1000,      // 1 hour - validate on load if older
  VALIDATE_IF_OLDER: 2 * 60 * 60 * 1000, // 2 hours - validate periodically if older
  MIN_VALIDATE_GAP: 15 * 60 * 1000,      // 15 minutes - minimum gap between validations
  PERIODIC_CHECK: 30 * 60 * 1000,        // 30 minutes - periodic check interval
  COOKIE_EXPIRY_HOURS: 7 * 24,          // 7 days - cookie expiry
  LOAD_DELAY: 1000,                      // 1 second - delay for background validation
  MAX_VALIDATION_FAILURES: 3             // Maximum validation failures before disabling
}

// ============================================================================
// Cookie Utilities
// ============================================================================

const setCookie = (name: string, value: string, hours: number = SESSION_TIMEOUTS.COOKIE_EXPIRY_HOURS) => {
  if (typeof window === 'undefined') return
  const expires = new Date()
  expires.setTime(expires.getTime() + (hours * 60 * 60 * 1000))
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Strict`
}

const getCookie = (name: string): string | null => {
  if (typeof window === 'undefined') return null
  const nameEQ = name + "="
  const ca = document.cookie.split(';')
  for(let i = 0; i < ca.length; i++) {
    let c = ca[i]
    while (c.charAt(0) === ' ') c = c.substring(1, c.length)
    if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length)
  }
  return null
}

const deleteCookie = (name: string) => {
  if (typeof window === 'undefined') return
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`
}

// ============================================================================
// Types
// ============================================================================

interface UserInfo {
  firstName?: string
  username?: string
  businessName?: string
  tenantId?: string
  accessToken?: string
  loginTime?: number
  lastValidated?: number
}

interface UserContextType {
  user: UserInfo | null
  setUser: (user: UserInfo | null) => void
  isAuthenticated: boolean
  logout: () => Promise<void>
  validateSession: () => Promise<boolean>
  isValidating: boolean
  isLoading: boolean
}

// ============================================================================
// Context
// ============================================================================

const UserContext = createContext<UserContextType | undefined>(undefined)

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<UserInfo | null>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [validationFailureCount, setValidationFailureCount] = useState(0)
  
  // Use ref to prevent multiple concurrent validations
  const validationInProgress = useRef(false)
  const validateSessionRef = useRef<(() => Promise<boolean>) | null>(null)

  // ============================================================================
  // Storage Operations
  // ============================================================================
  
  const persistUserData = useCallback((userData: UserInfo | null) => {
    try {
      if (userData) {
        const dataString = JSON.stringify(userData)
        localStorage.setItem('user_info', dataString)
        setCookie('session_backup', dataString)
      } else {
        localStorage.removeItem('user_info')
        deleteCookie('session_backup')
      }
    } catch (error) {
      console.error('Error persisting user data:', error)
    }
  }, [])

  // ============================================================================
  // Session Validation
  // ============================================================================

  const validateSession = useCallback(async (): Promise<boolean> => {
    // Early returns for invalid states
    if (!user?.accessToken || validationInProgress.current) {
      return false
    }

    // Check if validation is disabled due to repeated failures
    if (validationFailureCount >= SESSION_TIMEOUTS.MAX_VALIDATION_FAILURES) {
      console.log('Token validation disabled due to repeated failures')
      return true
    }

    // Check if we should skip validation (too recent)
    const now = Date.now()
    const timeSinceLastValidation = now - (user.lastValidated || 0)
    if (user.lastValidated && timeSinceLastValidation < SESSION_TIMEOUTS.MIN_VALIDATE_GAP) {
      return true
    }

    // Perform validation
    validationInProgress.current = true
    setIsValidating(true)

    try {
      const response = await validateToken(user.accessToken)
      
      if (!response.ok) {
        // Only logout on explicit 401 unauthorized
        if (response.status === 401) {
          console.warn('Token is unauthorized, logging out user')
          setUser(null)
          return false
        }
        
        // For other errors, increment failure count but keep user logged in
        setValidationFailureCount(prev => prev + 1)
        console.warn('Token validation failed but keeping user logged in')
        return true
      }

      const data = await response.json()
      
      if (data.valid) {
        // Update user info with fresh data
        const updatedUser: UserInfo = {
          ...user,
          firstName: data.first_name || user.firstName,
          username: data.username || user.username,
          businessName: data.business_name || user.businessName,
          tenantId: data.tenant_id || user.tenantId,
          lastValidated: now
        }
        
        setUserState(updatedUser)
        persistUserData(updatedUser)
        setValidationFailureCount(0)
        return true
      } else {
        // Token explicitly invalid
        if (data.message?.toLowerCase().includes('invalid')) {
          setUser(null)
          return false
        }
        
        // Uncertain validation result
        setValidationFailureCount(prev => prev + 1)
        return true
      }
    } catch (error) {
      console.error('Session validation error:', error)
      // Don't logout on network errors
      return true
    } finally {
      setIsValidating(false)
      validationInProgress.current = false
    }
  }, [user, validationFailureCount, persistUserData])

  // Update ref when validateSession changes
  useEffect(() => {
    validateSessionRef.current = validateSession
  }, [validateSession])

  // ============================================================================
  // Session Loading (runs once on mount)
  // ============================================================================

  useEffect(() => {
    const loadSession = async () => {
      setIsLoading(true)
      
      try {
        // Try localStorage first
        let storedUser = localStorage.getItem('user_info')
        
        // Fallback to cookie if localStorage is empty
        if (!storedUser) {
          const cookieSession = getCookie('session_backup')
          if (cookieSession) {
            console.log('Restoring session from cookie backup')
            storedUser = cookieSession
            // Restore to localStorage
            localStorage.setItem('user_info', storedUser)
          }
        }
        
        if (!storedUser) {
          console.log('No session found')
          return
        }

        const parsedUser: UserInfo = JSON.parse(storedUser)
        const sessionAge = Date.now() - (parsedUser.loginTime || 0)
        
        // Check if session is too old
        if (sessionAge > SESSION_TIMEOUTS.MAX_AGE) {
          console.log('Session expired (>24 hours)')
          persistUserData(null)
          return
        }
        
        // Restore session
        setUserState(parsedUser)
        console.log('Session restored', {
          age: Math.round(sessionAge / 1000 / 60) + ' minutes',
          needsValidation: sessionAge > SESSION_TIMEOUTS.VALIDATE_ON_LOAD
        })
        
        // Validate in background if session is old
        if (parsedUser.accessToken && sessionAge > SESSION_TIMEOUTS.VALIDATE_ON_LOAD) {
          setTimeout(() => {
            validateSessionRef.current?.()
          }, SESSION_TIMEOUTS.LOAD_DELAY)
        }
      } catch (error) {
        console.error('Error loading session:', error)
        persistUserData(null)
      } finally {
        setIsLoading(false)
      }
    }

    loadSession()
  }, [persistUserData])

  // ============================================================================
  // Periodic Validation
  // ============================================================================

  useEffect(() => {
    if (!user?.accessToken) return

    const interval = setInterval(() => {
      const sessionAge = Date.now() - (user.loginTime || 0)
      const timeSinceValidation = Date.now() - (user.lastValidated || 0)
      
      // Only validate old sessions that haven't been validated recently
      if (sessionAge > SESSION_TIMEOUTS.VALIDATE_IF_OLDER && 
          timeSinceValidation > SESSION_TIMEOUTS.MIN_VALIDATE_GAP) {
        console.log('Periodic validation check')
        validateSessionRef.current?.()
      }
    }, SESSION_TIMEOUTS.PERIODIC_CHECK)

    return () => clearInterval(interval)
  }, [user?.accessToken, user?.loginTime, user?.lastValidated])

  // ============================================================================
  // User Management
  // ============================================================================

  const setUser = useCallback((userInfo: UserInfo | null) => {
    // Add timestamps for new sessions
    if (userInfo && !userInfo.loginTime) {
      userInfo = {
        ...userInfo,
        loginTime: Date.now(),
        lastValidated: Date.now()
      }
    }
    
    setUserState(userInfo)
    persistUserData(userInfo)
  }, [persistUserData])

  const logout = useCallback(async () => {
    // Attempt to logout from backend
    if (user?.accessToken) {
      try {
        const response = await logoutWithToken(user.accessToken)
        if (!response.ok) {
          console.warn('Backend logout failed:', response.status)
        }
      } catch (error) {
        console.warn('Logout error:', error)
      }
    }
    
    // Clear local session
    setUser(null)
    
    // Redirect to login
    if (typeof window !== 'undefined') {
      try {
        const response = await getLoginUrl()
        if (response.ok) {
          const data = await response.json()
          window.location.href = data.login_url
        } else {
          window.location.href = '/oauth/login'
        }
      } catch {
        window.location.href = '/oauth/login'
      }
    }
  }, [user?.accessToken, setUser])

  // ============================================================================
  // Context Value
  // ============================================================================

  const isAuthenticated = !!(user?.tenantId && user?.accessToken)

  return (
    <UserContext.Provider 
      value={{ 
        user, 
        setUser,
        isAuthenticated,
        logout,
        validateSession,
        isValidating,
        isLoading
      }}
    >
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  const context = useContext(UserContext)
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider')
  }
  return context
}