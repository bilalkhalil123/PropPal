'use client'

import { useEffect, useState } from 'react'
import { useUser } from '@clerk/nextjs'

export default function UserSyncProvider({ children }: { children: React.ReactNode }) {
  const { user: clerkUser, isLoaded } = useUser()
  const [isSynced, setIsSynced] = useState(false)
  const [syncError, setSyncError] = useState<string | null>(null)

  useEffect(() => {
    console.log('🔄 [USER SYNC PROVIDER] useEffect triggered:', {
      isLoaded,
      hasUser: !!clerkUser,
      userId: clerkUser?.id,
      isSynced,
      userEmail: clerkUser?.emailAddresses[0]?.emailAddress
    })
    
    if (isLoaded && clerkUser && !isSynced) {
      console.log('🚀 [USER SYNC PROVIDER] Starting sync for user:', clerkUser.id)
      console.log('📧 User Email:', clerkUser.emailAddresses[0]?.emailAddress)
      console.log('👤 User Name:', clerkUser.fullName || clerkUser.firstName || 'Not provided')
      console.log('🔑 Auth Method:', clerkUser.externalAccounts?.length > 0 ? 
        clerkUser.externalAccounts.map(acc => acc.provider).join(', ') : 
        (clerkUser.passwordEnabled ? 'Email/Password' : 'Unknown'))
      syncUserToDatabase()
    }
  }, [isLoaded, clerkUser, isSynced])

  // Reset sync state when user changes
  useEffect(() => {
    if (clerkUser) {
      console.log('👤 [USER SYNC PROVIDER] User detected, resetting sync state')
      setIsSynced(false)
      setSyncError(null)
    }
  }, [clerkUser?.id])

  const syncUserToDatabase = async () => {
    if (!clerkUser) return

    try {
      setSyncError(null)
      
      // Get API URL from environment variable
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      if (!apiUrl) {
        throw new Error('NEXT_PUBLIC_API_URL environment variable is not set')
      }
      
      // Enhanced logging for terminal visibility
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
      
      // Create user in our database
      const userData = {
        clerk_id: clerkUser.id,
        name: clerkUser.fullName || clerkUser.firstName || clerkUser.emailAddresses[0]?.emailAddress?.split('@')[0] || 'User',
        email: clerkUser.emailAddresses[0]?.emailAddress || '',
        phone: clerkUser.phoneNumbers[0]?.phoneNumber || null,
        role: 'buyer', // Default role
        profile_image: clerkUser.imageUrl || null,
      }

      console.log('📤 Sending user data to backend:', userData)

      // Call our backend API to create user
      const response = await fetch(`${apiUrl}/api/users/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      })

      console.log('📡 Response status:', response.status)
      console.log('✅ Response ok:', response.ok)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Error response:', errorText)
        throw new Error(`Failed to sync user: ${response.status} ${response.statusText} - ${errorText}`)
      }

      const result = await response.json()
      console.log('🎉 User synced successfully!')
      console.log('📊 Database Response:', result)
      console.log('🆔 Database ID:', result._id)
      console.log('⏰ Created At:', result.created_at)
      console.log('='.repeat(60))
      console.log('✅ [AUTHENTICATION EVENT] User Sync Complete')
      console.log('='.repeat(60))
      setIsSynced(true)

    } catch (error) {
      console.log('='.repeat(60))
      console.log('❌ [AUTHENTICATION EVENT] User Sync Failed')
      console.log('='.repeat(60))
      console.error('🚨 Error syncing user:', error)
      console.log('📧 User Email:', clerkUser.emailAddresses[0]?.emailAddress)
      console.log('🆔 Clerk ID:', clerkUser.id)
      console.log('⏰ Error Time:', new Date().toISOString())
      console.log('='.repeat(60))
      
      setSyncError(error instanceof Error ? error.message : 'Failed to sync user')
      
      // Even if sync fails, mark as synced so user can continue using the app
      // The user can be synced later manually
      console.log('⚠️  Marking user as synced despite error to allow app usage')
      setIsSynced(true)
    }
  }

  // Show sync status (optional - for debugging)
  if (process.env.NODE_ENV === 'development' && clerkUser && !isSynced) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Syncing user to database...</p>
          {syncError && (
            <p className="text-red-600 mt-2">Error: {syncError}</p>
          )}
        </div>
      </div>
    )
  }

  return <>{children}</>
}
