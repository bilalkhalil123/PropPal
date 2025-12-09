'use client'

import { UserButton } from '@clerk/nextjs'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { api } from '@/lib/api-client'
import Link from 'next/link'
import { useState } from 'react'

export default function TestAuth() {
  const { user, loading, error, isAuthenticated, clerkId } = useCurrentUser()
  const [testResponse, setTestResponse] = useState<any>(null)
  const [testing, setTesting] = useState(false)

  const testApiCall = async () => {
    if (!clerkId) return
    
    setTesting(true)
    try {
      // Example API call using the new pattern
      const response = await api.chat.health()
      setTestResponse(response)
    } catch (err) {
      setTestResponse({ error: err instanceof Error ? err.message : 'Failed to call API' })
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading user data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold">Authentication Test</h1>
            <UserButton afterSignOutUrl="/" />
          </div>
          
          <div className="space-y-4">
            {/* Authentication Status */}
            <div className="p-4 bg-gray-100 rounded">
              <h2 className="font-semibold mb-2">Authentication Status:</h2>
              <p className={isAuthenticated ? "text-green-600" : "text-red-600"}>
                {isAuthenticated ? `✅ Authenticated` : "❌ Not authenticated"}
              </p>
            </div>

            {/* Clerk ID */}
            <div className="p-4 bg-blue-50 rounded">
              <h2 className="font-semibold mb-2">Clerk ID:</h2>
              <p className="text-sm text-gray-700 font-mono">{clerkId || 'Not available'}</p>
            </div>

            {/* User Data from Database */}
            {user ? (
              <div className="p-4 bg-green-50 rounded">
                <h2 className="font-semibold mb-2">✅ User Data from Database:</h2>
                <div className="space-y-2 text-sm">
                  <p><strong>Name:</strong> {user.name}</p>
                  <p><strong>Email:</strong> {user.email}</p>
                  <p><strong>Phone:</strong> {user.phone || 'Not provided'}</p>
                  <p><strong>Role:</strong> {user.role}</p>
                  <p><strong>Database ID:</strong> {user.id}</p>
                  <p><strong>Created:</strong> {new Date(user.created_at).toLocaleString()}</p>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-yellow-50 rounded">
                <h2 className="font-semibold mb-2">⚠️ No User Data</h2>
                <p className="text-sm text-gray-600">User data not loaded from database</p>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="p-4 bg-red-50 rounded">
                <h2 className="font-semibold mb-2 text-red-800">❌ Error:</h2>
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            {/* API Test */}
            <div className="p-4 bg-purple-50 rounded">
              <h2 className="font-semibold mb-2">API Test:</h2>
              <button
                onClick={testApiCall}
                disabled={testing || !isAuthenticated}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {testing ? 'Testing...' : 'Test Chat API Health'}
              </button>
              {testResponse && (
                <div className="mt-2 p-2 bg-white rounded text-xs">
                  <pre>{JSON.stringify(testResponse, null, 2)}</pre>
                </div>
              )}
            </div>
            
            {/* Available Actions */}
            <div className="p-4 bg-blue-50 rounded">
              <h2 className="font-semibold mb-2">Available Actions:</h2>
              <div className="space-x-4">
                <Link 
                  href="/dashboard" 
                  className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                >
                  Go to Dashboard
                </Link>
                <Link 
                  href="/profile" 
                  className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                >
                  View Profile
                </Link>
                <Link 
                  href="/" 
                  className="inline-block bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                >
                  Back to Home
                </Link>
              </div>
            </div>
            
            {isAuthenticated && (
              <div className="p-4 bg-green-50 rounded">
                <h2 className="font-semibold mb-2">✅ Authentication Working!</h2>
                <p className="text-sm text-gray-600">
                  The new context-based user management is working correctly. 
                  User data is loaded from your database and ready to use throughout the app.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
