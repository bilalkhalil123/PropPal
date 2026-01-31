'use client'

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useUser as useClerkUser } from '@clerk/nextjs'
import { UserResponse } from '@/lib/types/user'

interface UserContextType {
  user: UserResponse | null
  loading: boolean
  error: string | null
  refreshUser: () => Promise<void>
  isAuthenticated: boolean
  clerkId: string | null | undefined
}

const UserContext = createContext<UserContextType | undefined>(undefined)

interface UserProviderProps {
  children: React.ReactNode
}

export function UserProvider({ children }: UserProviderProps) {
  const { user: clerkUser, isLoaded: isClerkLoaded } = useClerkUser()
  const [user, setUser] = useState<UserResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSynced, setIsSynced] = useState(false)

  const fetchUser = useCallback(async () => {
    if (!clerkUser?.id) {
      setUser(null)
      setLoading(false)
      setIsSynced(false)
      return
    }

    try {
      setError(null)
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      
      if (!apiUrl) {
        throw new Error('NEXT_PUBLIC_API_URL environment variable is not set')
      }

      // Enhanced logging for browser console visibility
      console.log('='.repeat(60))
      console.log('🔐 [AUTHENTICATION EVENT] User Login/Signup Detected')
      console.log('='.repeat(60))
      console.log('📧 Email:', clerkUser.emailAddresses[0]?.emailAddress)
      console.log('👤 Name:', clerkUser.fullName || clerkUser.firstName || 'Not provided')
      console.log('🆔 Clerk ID:', clerkUser.id)
      console.log('📱 Phone:', clerkUser.phoneNumbers[0]?.phoneNumber || 'Not provided')
      console.log('🖼️  Profile Image:', clerkUser.imageUrl || 'Not provided')
      console.log('📅 Created At:', clerkUser.createdAt)
      console.log('🔄 Last Sign In:', clerkUser.lastSignInAt)
      
      // Detect authentication method
      const authMethods = clerkUser.externalAccounts?.map(account => account.provider) || []
      const hasPassword = clerkUser.passwordEnabled
      console.log('🔑 Auth Methods:', authMethods.length > 0 ? authMethods.join(', ') : (hasPassword ? 'Email/Password' : 'Unknown'))
      
      console.log('🌐 API URL:', apiUrl)
      console.log('⏰ Sync Time:', new Date().toISOString())
      console.log('-'.repeat(60))

      // First, ensure user is synced to your database
      const userData = {
        clerk_id: clerkUser.id,
        name: clerkUser.fullName || clerkUser.firstName || clerkUser.emailAddresses[0]?.emailAddress?.split('@')[0] || 'User',
        email: clerkUser.emailAddresses[0]?.emailAddress || '',
        phone: clerkUser.phoneNumbers[0]?.phoneNumber || null,
        role: 'buyer',
        profile_image: clerkUser.imageUrl || null,
      }

      console.log('📤 Sending user data to backend:', userData)

      const syncResponse = await fetch(`${apiUrl}/api/users/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      })

      console.log('📡 Response status:', syncResponse.status)
      console.log('✅ Response ok:', syncResponse.ok)

      if (!syncResponse.ok) {
        const errorText = await syncResponse.text()
        console.error('❌ Error response:', errorText)
        throw new Error(`Failed to sync user: ${syncResponse.status} ${syncResponse.statusText} - ${errorText}`)
      }

      const syncResult = await syncResponse.json()
      console.log('🎉 User synced successfully!')
      console.log('📊 Database Response:', syncResult)
      console.log('🆔 Database ID:', syncResult._id)
      console.log('⏰ Created At:', syncResult.created_at)

      // Then fetch the user from your database
      const response = await fetch(`${apiUrl}/api/users/me?clerk_id=${clerkUser.id}`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch user: ${response.status}`)
      }

      const userDataFromDb = await response.json()
      setUser(userDataFromDb)
      setIsSynced(true)
      console.log('='.repeat(60))
      console.log('✅ [AUTHENTICATION EVENT] User Sync Complete')
      console.log('='.repeat(60))
    } catch (err) {
      console.log('='.repeat(60))
      console.log('❌ [AUTHENTICATION EVENT] User Sync Failed')
      console.log('='.repeat(60))
      console.error('🚨 Error syncing user:', err)
      console.log('📧 User Email:', clerkUser.emailAddresses[0]?.emailAddress)
      console.log('🆔 Clerk ID:', clerkUser.id)
      console.log('⏰ Error Time:', new Date().toISOString())
      console.log('='.repeat(60))
      
      setError(err instanceof Error ? err.message : 'Failed to sync user')
      setUser(null)
      
      // Even if sync fails, allow user to continue using the app
      console.log('⚠️  Continuing despite sync error to allow app usage')
      // Don't set isSynced(true) on error so it can retry on next render if needed
    } finally {
      setLoading(false)
    }
  }, [clerkUser])

  // Reset sync state when user changes
  useEffect(() => {
    if (clerkUser) {
      console.log('👤 [USER PROVIDER] User detected, resetting sync state')
      setIsSynced(false)
      setError(null)
    }
  }, [clerkUser])

  useEffect(() => {
    if (isClerkLoaded && clerkUser && !isSynced) {
      console.log('🚀 [USER PROVIDER] Starting sync for user:', clerkUser.id)
      fetchUser()
    } else if (isClerkLoaded && !clerkUser) {
      // User logged out
      setUser(null)
      setLoading(false)
      setIsSynced(false)
    }
  }, [isClerkLoaded, clerkUser, isSynced, fetchUser])

  const refreshUser = useCallback(async () => {
    setLoading(true)
    setIsSynced(false) // Reset sync state to force fresh sync
    await fetchUser()
  }, [fetchUser])

  const value: UserContextType = {
    user,
    loading: loading || !isClerkLoaded,
    error,
    refreshUser,
    isAuthenticated: !!user && !!clerkUser,
    clerkId: clerkUser?.id,
  }

  // Show sync status during development (optional - for debugging)
  if (process.env.NODE_ENV === 'development' && clerkUser && loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Syncing user to database...</p>
          {error && (
            <p className="text-red-600 mt-2">Error: {error}</p>
          )}
        </div>
      </div>
    )
  }

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>
}

export function useUser() {
  const context = useContext(UserContext)
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider')
  }
  return context
}

