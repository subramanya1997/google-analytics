"use client"

import React, { createContext, useContext, useState, useEffect } from 'react'
import { logoutWithToken, getLoginUrl } from '@/lib/api-utils'

interface UserInfo {
  firstName?: string
  username?: string
  tenantId?: string
  accessToken?: string
}

interface UserContextType {
  user: UserInfo | null
  setUser: (user: UserInfo | null) => void
  isAuthenticated: boolean
  logout: () => Promise<void>
}

const UserContext = createContext<UserContextType | undefined>(undefined)

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<UserInfo | null>(null)

  // Load user info from localStorage on mount
  useEffect(() => {
    try {
      const storedUser = localStorage.getItem('user_info')
      if (storedUser) {
        setUserState(JSON.parse(storedUser))
      }
    } catch (error) {
      console.error('Error loading user info from localStorage:', error)
    }
  }, [])

  // Save user info to localStorage when it changes
  const setUser = (userInfo: UserInfo | null) => {
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
        logout
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
