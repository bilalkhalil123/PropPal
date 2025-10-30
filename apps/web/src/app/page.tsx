import Link from 'next/link'
import { HomeIcon } from '@heroicons/react/24/outline'

export const metadata = {
  title: 'PropPal - AI-Powered Real Estate Platform',
  description:
    'Your AI-powered real estate platform. Find your dream property with ease.',
}

export default function HomePage() {
  return (
    <>
      <div className="min-h-screen">
        {/* Hero Section with Background Image */}
        <div 
          className="relative min-h-screen flex items-center justify-center bg-cover bg-center bg-no-repeat"
          style={{
            backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0.3)), url('/hero-house.svg')`
          }}
        >
          {/* Navigation */}
          <nav className="absolute top-0 left-0 right-0 z-50 p-6">
            <div className="max-w-7xl mx-auto flex justify-between items-center">
              <div className="flex items-center space-x-2 text-white">
                <HomeIcon className="h-8 w-8" />
                <span className="text-2xl font-bold">PropPal</span>
              </div>
              <div className="hidden md:flex space-x-8 text-white">
                <Link href="#" className="hover:text-blue-300 transition-colors">Home</Link>
                <Link href="#" className="hover:text-blue-300 transition-colors">Properties</Link>
                <Link href="#" className="hover:text-blue-300 transition-colors">About</Link>
                <Link href="#" className="hover:text-blue-300 transition-colors">Contact</Link>
              </div>
            </div>
          </nav>

          {/* Hero Content */}
          <div className="text-center text-white max-w-4xl mx-auto px-6">
            {/* Logo/Icon */}
            <div className="mb-8">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-white/10 backdrop-blur-sm rounded-2xl border border-white/20">
                <HomeIcon className="h-10 w-10 text-white" />
              </div>
            </div>

            {/* Main Heading */}
            <h1 className="text-6xl md:text-7xl font-bold mb-6 tracking-tight">
              PropPal
            </h1>

            {/* Subheading */}
            <p className="text-xl md:text-2xl mb-12 text-gray-200 max-w-2xl mx-auto leading-relaxed">
              Your AI-powered real estate platform. Find your dream property with ease.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-8">
              <Link 
                href="/sign-up"
                className="bg-blue-500 hover:bg-blue-600 text-white px-8 py-4 rounded-xl text-lg font-semibold transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-xl"
              >
                Get Started
              </Link>
              <Link 
                href="/sign-in"
                className="bg-white/10 hover:bg-white/20 text-white px-8 py-4 rounded-xl text-lg font-semibold transition-all duration-300 backdrop-blur-sm border border-white/20 hover:border-white/30"
              >
                Already have an account? Login
              </Link>
            </div>
          </div>

          {/* Scroll Indicator */}
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 text-white animate-bounce">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </div>
        </div>

        {/* Features Section */}
        <section className="py-20 bg-white">
          <div className="max-w-7xl mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-4xl font-bold text-gray-900 mb-4">
                Why Choose PropPal?
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Experience the future of real estate with our AI-powered platform designed for buyers, sellers, and builders.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {/* Feature 1 */}
              <div className="text-center p-8 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-100 hover:shadow-lg transition-shadow">
                <div className="w-16 h-16 bg-blue-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4">AI-Powered Search</h3>
                <p className="text-gray-600">
                  Find properties using natural language. Just describe what you're looking for, and our AI will do the rest.
                </p>
              </div>

              {/* Feature 2 */}
              <div className="text-center p-8 rounded-2xl bg-gradient-to-br from-green-50 to-emerald-100 hover:shadow-lg transition-shadow">
                <div className="w-16 h-16 bg-green-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4">Smart Matching</h3>
                <p className="text-gray-600">
                  Our intelligent system matches buyers with sellers and connects builders with the right opportunities.
                </p>
              </div>

              {/* Feature 3 */}
              <div className="text-center p-8 rounded-2xl bg-gradient-to-br from-purple-50 to-violet-100 hover:shadow-lg transition-shadow">
                <div className="w-16 h-16 bg-purple-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4">24/7 AI Assistant</h3>
                <p className="text-gray-600">
                  Get instant answers to your property questions with our intelligent chatbot available round the clock.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 bg-gradient-to-r from-blue-600 to-indigo-600">
          <div className="max-w-4xl mx-auto text-center px-6">
            <h2 className="text-4xl font-bold text-white mb-6">
              Ready to Find Your Dream Property?
            </h2>
            <p className="text-xl text-blue-100 mb-8">
              Join thousands of satisfied users who have found their perfect home with PropPal.
            </p>
            <Link 
              href="/sign-up"
              className="inline-block bg-white text-blue-600 px-8 py-4 rounded-xl text-lg font-semibold hover:bg-gray-100 transition-colors shadow-lg hover:shadow-xl transform hover:scale-105"
            >
              Start Your Journey Today
            </Link>
          </div>
        </section>

        {/* Footer */}
        <footer className="bg-gray-900 text-white py-12">
          <div className="max-w-7xl mx-auto px-6">
            <div className="grid md:grid-cols-4 gap-8">
              <div>
                <div className="flex items-center space-x-2 mb-4">
                  <HomeIcon className="h-8 w-8" />
                  <span className="text-2xl font-bold">PropPal</span>
                </div>
                <p className="text-gray-400">
                  Your AI-powered real estate platform for the modern world.
                </p>
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-4">Platform</h3>
                <ul className="space-y-2 text-gray-400">
                  <li><Link href="/chat" className="hover:text-white transition-colors">For Buyers</Link></li>
                  <li><Link href="#" className="hover:text-white transition-colors">For Sellers</Link></li>
                  <li><Link href="/builder" className="hover:text-white transition-colors">For Builders</Link></li>
                </ul>
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-4">Company</h3>
                <ul className="space-y-2 text-gray-400">
                  <li><Link href="#" className="hover:text-white transition-colors">About</Link></li>
                  <li><Link href="#" className="hover:text-white transition-colors">Careers</Link></li>
                  <li><Link href="#" className="hover:text-white transition-colors">Contact</Link></li>
                </ul>
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-4">Support</h3>
                <ul className="space-y-2 text-gray-400">
                  <li><Link href="#" className="hover:text-white transition-colors">Help Center</Link></li>
                  <li><Link href="#" className="hover:text-white transition-colors">Privacy Policy</Link></li>
                  <li><Link href="#" className="hover:text-white transition-colors">Terms of Service</Link></li>
                </ul>
              </div>
            </div>
            <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
              <p>&copy; 2025 PropPal. All rights reserved.</p>
            </div>
          </div>
        </footer>
      </div>
    </>
  )
}
