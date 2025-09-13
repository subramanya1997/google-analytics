"use client"

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { logoutWithToken, getLoginUrl, validateToken } from '@/lib/api-utils'

interface UserInfo {
  firstName?: string
  username?: string
  tenantId?: string
  accessToken?: string
  loginTime?: number  // Timestamp when user logged in
  lastValidated?: number  // Timestamp when token was last validated
}

interface UserContextType {
  user: UserInfo | null
  setUser: (user: UserInfo | null) => void
  isAuthenticated: boolean
  logout: () => Promise<void>
  validateSession: () => Promise<boolean>
  isValidating: boolean
}

const UserContext = createContext<UserContextType | undefined>(undefined)

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<UserInfo | null>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [validationPromise, setValidationPromise] = useState<Promise<boolean> | null>(null)
  const [validationFailureCount, setValidationFailureCount] = useState(0)
  const validateSessionRef = useRef<(() => Promise<boolean>) | null>(null)

  // Session validation function
  const validateSession = useCallback(async (): Promise<boolean> => {
    if (!user?.accessToken) {
      return false
    }

    // If validation has failed too many times, disable it to prevent spam
    if (validationFailureCount >= 3) {
      console.log('Token validation disabled due to repeated failures')
      return true // Assume valid to prevent logout loops
    }

    // If there's already a validation in progress, wait for it
    if (validationPromise) {
      console.log('Validation already in progress, waiting for result...')
      return await validationPromise
    }

    // Check if we need to validate (don't validate too frequently)
    const now = Date.now()
    const lastValidated = user.lastValidated || 0
    const timeSinceValidation = now - lastValidated
    
    // Only validate if it's been more than 15 minutes since last validation
    // or if we've never validated before
    if (timeSinceValidation < 15 * 60 * 1000 && user.lastValidated) {
      return true // Assume still valid if recently validated
    }

    // Create validation promise to prevent concurrent validations
    const validationTask = async (): Promise<boolean> => {
      setIsValidating(true)
      try {
        const response = await validateToken(user.accessToken!)
        
        if (!response.ok) {
          console.error('Token validation request failed:', response.status)
          
          // Don't immediately log out on validation failures - the token might still be valid
          // Only log out on 401 (unauthorized) errors
          if (response.status === 401) {
            console.warn('Token is unauthorized, logging out user')
            setUser(null)
            return false
          }
          
          // For other errors (network issues, service unavailable), assume token is still valid
          // but don't update the lastValidated timestamp and increment failure count
          console.warn('Token validation failed but keeping user logged in due to potential network/service issues')
          setValidationFailureCount(prev => prev + 1)
          return true
        }

        const data = await response.json()
        
        if (data.valid) {
          // Update user info with fresh data and validation timestamp
          const updatedUser = {
            ...user,
            firstName: data.first_name || user.firstName,
            username: data.username || user.username,
            tenantId: data.tenant_id || user.tenantId,
            lastValidated: now
          }
          setUserState(updatedUser)
          
          // Update localStorage
          try {
            localStorage.setItem('user_info', JSON.stringify(updatedUser))
          } catch (error) {
            console.error('Error saving updated user info to localStorage:', error)
          }
          
          // Reset failure count on successful validation
          setValidationFailureCount(0)
          return true
        } else {
          console.warn('Token is invalid:', data.message)
          // Only log out if the validation explicitly says the token is invalid
          if (data.message && data.message.toLowerCase().includes('invalid')) {
            setUser(null)
            return false
          }
          
          // For other validation failures, keep user logged in but don't update timestamp
          console.warn('Token validation uncertain, keeping user logged in')
          setValidationFailureCount(prev => prev + 1)
          return true
        }
      } catch (error) {
        console.error('Session validation error:', error)
        // Don't clear session on network errors, just return false
        return false
      } finally {
        setIsValidating(false)
        setValidationPromise(null) // Clear the promise when done
      }
    }

    // Set the promise and execute validation
    const promise = validationTask()
    setValidationPromise(promise)
    return await promise
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.accessToken, user?.lastValidated, validationPromise, validationFailureCount])
  // Note: We intentionally don't include 'user' in dependencies to avoid infinite re-renders
  // since user is an object that changes on every render. We only depend on specific properties.

  // Update the ref whenever validateSession changes
  useEffect(() => {
    validateSessionRef.current = validateSession
  }, [validateSession])

  // Load user info from localStorage on mount
  useEffect(() => {
    const loadUser = () => {
      try {
        const storedUser = localStorage.getItem('user_info')
        if (storedUser) {
          const parsedUser: UserInfo = JSON.parse(storedUser)
          setUserState(parsedUser)
        }
      } catch (error) {
        console.error('Error loading user info from localStorage:', error)
        localStorage.removeItem('user_info') // Clear corrupted data
      }
    }

    loadUser()
  }, []) // Only run on mount

  // Separate effect to validate session after user is loaded
  useEffect(() => {
    if (!user?.accessToken || !user?.loginTime) return

    // Check if session should be considered expired
    const now = Date.now()
    const sessionAge = now - user.loginTime
    
    // If session is older than 2 hours, validate the token
    if (sessionAge > 2 * 60 * 60 * 1000) {
      console.log('Session older than 2 hours, validating token...')
      // Validate with a delay to prevent race conditions
      const timeoutId = setTimeout(async () => {
        if (validateSessionRef.current) {
          const isValid = await validateSessionRef.current()
          if (!isValid) {
            console.log('Session validation failed, user will be logged out')
          }
        }
      }, 2000)
      
      return () => clearTimeout(timeoutId)
    }
  }, [user?.accessToken, user?.loginTime]) // Removed validateSession dependency

  // Periodic token validation (every 15 minutes)
  useEffect(() => {
    if (!user?.accessToken) return

    const interval = setInterval(async () => {
      console.log('Performing periodic token validation...')
      if (validateSessionRef.current) {
        const isValid = await validateSessionRef.current()
        if (!isValid) {
          console.log('Periodic validation failed, session will be cleared')
        }
      }
    }, 30 * 60 * 1000) // 30 minutes - less frequent to reduce load

    return () => clearInterval(interval)
  }, [user?.accessToken]) // Removed validateSession dependency

  // Save user info to localStorage when it changes
  const setUser = (userInfo: UserInfo | null) => {
    // Add login timestamp when setting new user info
    if (userInfo && !userInfo.loginTime) {
      userInfo = {
        ...userInfo,
        loginTime: Date.now(),
        lastValidated: Date.now()
      }
    }
    
    setUserState(userInfo)
    try {
      if (userInfo) {
        localStorage.setItem('user_info', JSON.stringify(userInfo))
      } else {
        localStorage.removeItem('user_info')
      }
    } catch (error) {
      console.error('Error saving user info to localStorage:', error)
    }
  }

  const isAuthenticated = !!user?.tenantId && !!user?.accessToken

  const logout = async () => {
    if (user?.accessToken) {
      try {
        const response = await logoutWithToken(user.accessToken)

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ message: 'Unknown error' }))
          console.warn('Logout API failed:', response.status, errorData.message || response.statusText)
        }
      } catch (error) {
        console.warn('Logout API error:', error)
      }
    }
    
    // Clear user data regardless of logout API success
    setUser(null)
    
    // Redirect to login URL from backend
    if (typeof window !== 'undefined') {
      try {
        const response = await getLoginUrl()
        if (response.ok) {
          const data = await response.json()
          window.location.href = data.login_url
        } else {
          // Fallback: redirect to local login page which will fetch the URL
          window.location.href = '/oauth/login'
        }
      } catch (error) {
        console.error('Error getting login URL:', error)
        // Fallback: redirect to local login page
        window.location.href = '/oauth/login'
      }
    }
  }

  return (
    <UserContext.Provider 
      value={{ 
        user, 
        setUser,
        isAuthenticated,
        logout,
        validateSession,
        isValidating
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
