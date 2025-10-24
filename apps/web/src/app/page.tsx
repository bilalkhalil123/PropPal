import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/nextjs'
import Link from 'next/link'

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">PropPal</h1>
            </div>
            <div className="flex items-center space-x-4">
              <SignedOut>
                <SignInButton mode="modal">
                  <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
                    Sign In
                  </button>
                </SignInButton>
              </SignedOut>
              <SignedIn>
                <UserButton fallbackRedirectUrl="/" />
              </SignedIn>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center">
          <h2 className="text-4xl font-extrabold text-gray-900 sm:text-5xl md:text-6xl">
            AI-Powered Real Estate Platform
          </h2>
          <p className="mt-3 max-w-md mx-auto text-base text-gray-500 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
            Find your dream property with conversational search, AI-assisted listings, and intelligent visit booking.
          </p>
          
          <SignedIn>
            <div className="mt-8 space-x-4">
              <Link 
                href="/dashboard"
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Go to Dashboard
              </Link>
              <Link 
                href="/test-auth"
                className="inline-flex items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Test Auth
              </Link>
            </div>
          </SignedIn>
          
          <SignedOut>
            <div className="mt-8">
              <SignInButton mode="modal">
                <button className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
                  Get Started
                </button>
              </SignInButton>
            </div>
          </SignedOut>
        </div>

        {/* Features */}
        <div className="mt-16">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="text-blue-600 text-3xl mb-4">🏠</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Conversational Search</h3>
              <p className="text-gray-500">Search properties using natural language queries like "3-bedroom apartment near a school"</p>
            </div>
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="text-blue-600 text-3xl mb-4">🤖</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">AI-Assisted Listings</h3>
              <p className="text-gray-500">Create property listings easily with AI-powered assistance and smart forms</p>
            </div>
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="text-blue-600 text-3xl mb-4">📅</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Smart Visit Booking</h3>
              <p className="text-gray-500">Automated scheduling, rescheduling, and reminders for property visits</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
