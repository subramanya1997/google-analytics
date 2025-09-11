"use client"

import React, { createContext, useContext, useState, useEffect } from 'react'

interface UserInfo {
  firstName?: string
  username?: string
  tenantId?: string
}

interface UserContextType {
  user: UserInfo | null
  setUser: (user: UserInfo | null) => void
  isAuthenticated: boolean
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

  const isAuthenticated = !!user?.tenantId

  return (
    <UserContext.Provider 
      value={{ 
        user, 
        setUser,
        isAuthenticated
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
