import { auth } from '@clerk/nextjs/server'
import { UserButton } from '@clerk/nextjs'
import Link from 'next/link'

export default async function TestAuth() {
  const { userId } = await auth()
  
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold">Authentication Test</h1>
            <UserButton afterSignOutUrl="/" />
          </div>
          
          <div className="space-y-4">
            <div className="p-4 bg-gray-100 rounded">
              <h2 className="font-semibold mb-2">Authentication Status:</h2>
              <p className={userId ? "text-green-600" : "text-red-600"}>
                {userId ? `✅ Authenticated (User ID: ${userId})` : "❌ Not authenticated"}
              </p>
            </div>
            
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
                  href="/" 
                  className="inline-block bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                >
                  Back to Home
                </Link>
              </div>
            </div>
            
            {userId && (
              <div className="p-4 bg-green-50 rounded">
                <h2 className="font-semibold mb-2">✅ Authentication Working!</h2>
                <p className="text-sm text-gray-600">
                  You are successfully authenticated. The Clerk integration is working correctly.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
