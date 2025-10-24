import { UserButton } from '@clerk/nextjs'
import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import Link from 'next/link'

export default async function Dashboard() {
  const { userId } = await auth()
  
  if (!userId) {
    redirect('/sign-in')
  }
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Link href="/" className="text-2xl font-bold text-gray-900">
                PropPal
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/profile" className="text-gray-600 hover:text-gray-900">
                Profile
              </Link>
                <UserButton fallbackRedirectUrl="/" />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">Welcome to your PropPal dashboard</p>
        </div>

        {/* Dashboard Cards */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="text-2xl">🏠</div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Properties
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      Browse & Search
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
            <div className="bg-gray-50 px-5 py-3">
              <div className="text-sm">
                <Link href="/properties" className="font-medium text-blue-600 hover:text-blue-500">
                  View Properties
                </Link>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="text-2xl">🏗️</div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Builders
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      Find & Connect
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
            <div className="bg-gray-50 px-5 py-3">
              <div className="text-sm">
                <Link href="/builders" className="font-medium text-blue-600 hover:text-blue-500">
                  View Builders
                </Link>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="text-2xl">📅</div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Visits
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      Schedule & Manage
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
            <div className="bg-gray-50 px-5 py-3">
              <div className="text-sm">
                <Link href="/visits" className="font-medium text-blue-600 hover:text-blue-500">
                  View Visits
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Link
              href="/properties/search"
              className="relative group bg-white p-6 focus-within:ring-2 focus-within:ring-inset focus-within:ring-blue-500 rounded-lg shadow hover:shadow-md transition-shadow"
            >
              <div>
                <span className="rounded-lg inline-flex p-3 bg-blue-50 text-blue-700 ring-4 ring-white">
                  🔍
                </span>
              </div>
              <div className="mt-4">
                <h3 className="text-lg font-medium">
                  Search Properties
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  Find your dream property with AI-powered search
                </p>
              </div>
            </Link>

            <Link
              href="/properties/create"
              className="relative group bg-white p-6 focus-within:ring-2 focus-within:ring-inset focus-within:ring-blue-500 rounded-lg shadow hover:shadow-md transition-shadow"
            >
              <div>
                <span className="rounded-lg inline-flex p-3 bg-green-50 text-green-700 ring-4 ring-white">
                  ➕
                </span>
              </div>
              <div className="mt-4">
                <h3 className="text-lg font-medium">
                  List Property
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  Create a new property listing
                </p>
              </div>
            </Link>

            <Link
              href="/builders/search"
              className="relative group bg-white p-6 focus-within:ring-2 focus-within:ring-inset focus-within:ring-blue-500 rounded-lg shadow hover:shadow-md transition-shadow"
            >
              <div>
                <span className="rounded-lg inline-flex p-3 bg-purple-50 text-purple-700 ring-4 ring-white">
                  🏗️
                </span>
              </div>
              <div className="mt-4">
                <h3 className="text-lg font-medium">
                  Find Builders
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  Connect with trusted builders
                </p>
              </div>
            </Link>

            <Link
              href="/visits/schedule"
              className="relative group bg-white p-6 focus-within:ring-2 focus-within:ring-inset focus-within:ring-blue-500 rounded-lg shadow hover:shadow-md transition-shadow"
            >
              <div>
                <span className="rounded-lg inline-flex p-3 bg-orange-50 text-orange-700 ring-4 ring-white">
                  📅
                </span>
              </div>
              <div className="mt-4">
                <h3 className="text-lg font-medium">
                  Schedule Visit
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  Book a property visit
                </p>
              </div>
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
