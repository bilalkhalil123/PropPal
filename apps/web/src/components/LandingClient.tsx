"use client"

import Link from 'next/link'
import Image from 'next/image'
import { useEffect, useState } from 'react'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { motion } from 'framer-motion'
import { HomeIcon, SparklesIcon, UsersIcon, ChatBubbleLeftIcon, ChevronDownIcon } from '@heroicons/react/24/outline'

export default function LandingClient() {
  const [scrolled, setScrolled] = useState(false)
  const { isAuthenticated, loading } = useCurrentUser()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const fadeUp = {
    hidden: { opacity: 0, y: 24 },
    visible: { opacity: 1, y: 0 }
  }
  const stagger = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.12, delayChildren: 0.1 } }
  }

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="relative min-h-screen flex items-center justify-center overflow-hidden">
        {/* Full-width parallax background image */}
        <div className="absolute inset-0 -z-10 bg-fixed bg-center bg-cover" style={{ backgroundImage: "url('/hero-house.svg')" }} />
        {/* Light luxury gradient overlay (reduced opacity for readability) */}
        <div aria-hidden className="absolute inset-0 -z-10 bg-[linear-gradient(to_bottom,rgba(249,249,249,0.6),rgba(237,236,232,0.6))]" />
        <div aria-hidden className="absolute -top-32 -right-32 h-80 w-80 rounded-full bg-white/10 blur-3xl" />
        <div aria-hidden className="absolute -bottom-24 -left-24 h-96 w-96 rounded-full bg-[color:var(--color-gold)]/10 blur-3xl" />

        {/* Navigation */}
        <nav
          className={`fixed top-0 left-0 right-0 z-50 px-6 md:px-12 lg:px-24 transition-all ${
            scrolled ? 'bg-white/70 backdrop-blur-lg border-b border-white/60 shadow-md' : 'bg-white/50 backdrop-blur-lg border-b border-white/40'
          }`}
          role="navigation"
          aria-label="Primary"
        >
          <div className="max-w-7xl mx-auto flex justify-between items-center py-4">
            <div className="flex items-center space-x-3 text-[color:var(--color-primary)]">
              <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center backdrop-blur-sm">
                <HomeIcon className="h-6 w-6" />
              </div>
              <span className="text-2xl font-bold tracking-tight">PropPal</span>
            </div>
            <div className="hidden md:flex space-x-8 text-[color:var(--color-primary)]/90">
              <Link href="#features" className="relative text-sm font-medium transition-colors hover:text-[color:var(--color-primary)] after:absolute after:inset-x-0 after:-bottom-1 after:h-[2px] after:bg-[color:var(--color-accent-gold)]/80 after:scale-x-0 after:origin-left hover:after:scale-x-100 after:transition-transform">
                Features
              </Link>
              <Link href="#" className="relative text-sm font-medium transition-colors hover:text-[color:var(--color-primary)] after:absolute after:inset-x-0 after:-bottom-1 after:h-[2px] after:bg-[color:var(--color-accent-gold)]/80 after:scale-x-0 after:origin-left hover:after:scale-x-100 after:transition-transform">
                Properties
              </Link>
              <Link href="#" className="relative text-sm font-medium transition-colors hover:text-[color:var(--color-primary)] after:absolute after:inset-x-0 after:-bottom-1 after:h-[2px] after:bg-[color:var(--color-accent-gold)]/80 after:scale-x-0 after:origin-left hover:after:scale-x-100 after:transition-transform">
                About
              </Link>
              <Link href="#" className="relative text-sm font-medium transition-colors hover:text-[color:var(--color-primary)] after:absolute after:inset-x-0 after:-bottom-1 after:h-[2px] after:bg-[color:var(--color-accent-gold)]/80 after:scale-x-0 after:origin-left hover:after:scale-x-100 after:transition-transform">
                Contact
              </Link>
            </div>
          </div>
        </nav>

        {/* Hero Content */}
        <div className="text-center text-[color:var(--foreground)] max-w-6xl mx-auto px-6 md:px-12 lg:px-24 pt-28">
          <motion.div
            className="mb-8 inline-block"
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.6 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          >
            <div
              className="inline-flex items-center justify-center px-5 py-2 rounded-full border shadow-card"
              style={{ backgroundColor: '#ffffff', borderColor: 'var(--color-primary)' }}
            >
              <SparklesIcon className="h-4 w-4 mr-2 text-[color:var(--color-primary)]" />
              <span className="text-sm font-semibold text-[color:var(--color-primary)]">AI‑Powered Real Estate</span>
            </div>
          </motion.div>

          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true }}>
            <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold mb-6 tracking-tight text-balance text-[color:var(--color-primary)]">
              Find Your Dream Property
            </motion.h1>
            <motion.p
              variants={fadeUp}
              className="text-xl md:text-2xl mb-10 text-slate-700 max-w-3xl mx-auto leading-relaxed text-balance"
            >
              Discover properties with AI-powered search. Connect with builders and sellers seamlessly.
            </motion.p>

            <motion.div variants={fadeUp} className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-8">
              <Link
                href="/sign-up"
                className="px-8 py-4 rounded-2xl text-lg font-semibold transition-all duration-200 active:scale-95 transform hover:scale-105 shadow-cta text-[var(--color-primary-contrast)] hover:ring-2 hover:ring-[color:var(--color-accent-gold)] bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))]"
              >
                Get Started
              </Link>
              {!loading && !isAuthenticated && (
                <Link
                  href="/sign-in"
                  className="px-8 py-4 rounded-2xl text-lg font-semibold transition-all duration-200 active:scale-95 border text-[color:var(--color-primary)] border-[color:var(--color-primary)] bg-white/70 hover:bg-white"
                >
                  Sign In
                </Link>
              )}
            </motion.div>
          </motion.div>
        </div>

        {/* Scroll Indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-white">
          <div className="flex flex-col items-center gap-1 opacity-90">
            <ChevronDownIcon className="w-6 h-6 animate-pulse" />
            <ChevronDownIcon className="w-6 h-6 animate-pulse [animation-delay:150ms]" />
          </div>
        </div>
      </div>

      {/* Features Section */}
      <section id="features" className="py-28 bg-white relative">
        <div aria-hidden className="pointer-events-none absolute inset-x-0 -top-24 mx-auto h-48 w-[80%] rounded-3xl bg-gradient-to-r from-cyan-50 to-teal-50 blur-2xl opacity-60 -z-10" />
        <div className="relative max-w-7xl mx-auto px-6 md:px-12 lg:px-24">
          <div className="text-center mb-16 md:mb-20">
            <h2 className="text-4xl md:text-5xl font-bold text-[color:var(--color-primary)] mb-6 text-balance">Why Choose PropPal?</h2>
            <p className="text-xl text-slate-700 max-w-3xl mx-auto">
              Experience the future of real estate with our AI-powered platform designed for buyers, sellers, and
              builders.
            </p>
          </div>

          <motion.div
            className="grid md:grid-cols-3 gap-6 md:gap-8"
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.2 }}
          >
            {/* Feature 1 */}
            <motion.div variants={fadeUp} whileHover={{ y: -6 }} className="transition-transform">
              <div className="p-[1px] rounded-2xl transition-colors" style={{ backgroundImage: "linear-gradient(to right, var(--color-primary), var(--color-accent-gold))" }}>
                <div className="group rounded-2xl p-8 bg-white/85 backdrop-blur border border-slate-300 shadow-card hover:shadow-elevated">
              <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform" style={{ backgroundColor: 'var(--color-primary)' }}>
                <SparklesIcon className="h-7 w-7 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-[color:var(--color-primary)] mb-3">AI-Powered Search</h3>
              <p className="text-slate-700 leading-relaxed">
                Find properties using natural language. Just describe what you're looking for, and our AI will do the
                rest.
              </p>
                </div>
              </div>
            </motion.div>

            {/* Feature 2 */}
            <motion.div variants={fadeUp} whileHover={{ y: -6 }} className="transition-transform">
              <div className="p-[1px] rounded-2xl transition-colors" style={{ backgroundImage: "linear-gradient(to right, var(--color-accent-gold), var(--color-primary))" }}>
                <div className="group rounded-2xl p-8 bg-white/85 backdrop-blur border border-slate-300 shadow-card hover:shadow-elevated">
                  <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform" style={{ backgroundColor: 'var(--color-primary)' }}>
                    <UsersIcon className="h-7 w-7 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-[color:var(--color-primary)] mb-3">Smart Matching</h3>
                  <p className="text-slate-700 leading-relaxed">
                    Our intelligent system matches buyers with sellers and connects builders with the right opportunities.
                  </p>
                </div>
              </div>
            </motion.div>

            {/* Feature 3 */}
            <motion.div variants={fadeUp} whileHover={{ y: -6 }} className="transition-transform">
              <div className="p-[1px] rounded-2xl transition-colors" style={{ backgroundImage: "linear-gradient(to right, var(--color-accent-gold), var(--color-primary))" }}>
                <div className="group rounded-2xl p-8 bg-white/85 backdrop-blur border border-slate-300 shadow-card hover:shadow-elevated">
                  <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform" style={{ backgroundColor: 'var(--color-primary)' }}>
                    <ChatBubbleLeftIcon className="h-7 w-7 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-[color:var(--color-primary)] mb-3">24/7 AI Assistant</h3>
                  <p className="text-slate-700 leading-relaxed">
                    Get instant answers to your property questions with our intelligent chatbot available round the clock.
                  </p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-28 relative overflow-hidden" style={{ backgroundImage: "linear-gradient(to right, var(--color-primary), var(--color-accent-gold))" }}>
        <div aria-hidden className="absolute inset-0 bg-[radial-gradient(600px_300px_at_10%_10%,rgba(255,255,255,0.18),transparent),radial-gradient(700px_400px_at_90%_80%,rgba(255,255,255,0.15),transparent)]" />
        <div className="relative max-w-5xl mx-auto text-center px-6 md:px-12 lg:px-24">
          <motion.h2
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="text-4xl md:text-5xl font-bold text-white mb-6 text-balance"
          >
            Ready to Find Your Dream Property?
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="text-xl text-white/90 mb-10"
          >
            Join thousands of satisfied users who have found their perfect home with PropPal.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
          >
            <Link
              href="/sign-up"
              className="inline-block px-10 py-4 rounded-xl text-lg font-semibold transition-all duration-200 active:scale-95 transform hover:scale-105 shadow-xl hover:shadow-2xl bg-white text-[color:var(--color-primary)] hover:bg-slate-50"
            >
              Start Your Journey Today
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-white py-16">
        <div className="max-w-7xl mx-auto px-6 md:px-12 lg:px-24">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            <div>
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-teal-600 rounded-lg flex items-center justify-center">
                  <HomeIcon className="h-6 w-6" />
                </div>
                <span className="text-2xl font-bold">PropPal</span>
              </div>
              <p className="text-slate-400 text-sm leading-relaxed">
                Your AI-powered real estate platform for the modern world.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-4">Platform</h3>
              <ul className="space-y-3 text-slate-400 text-sm">
                <li>
                  <Link href="/chat" className="hover:text-white transition-colors">
                    For Buyers
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    For Sellers
                  </Link>
                </li>
                <li>
                  <Link href="/builder" className="hover:text-white transition-colors">
                    For Builders
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-4">Company</h3>
              <ul className="space-y-3 text-slate-400 text-sm">
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    About
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Careers
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Contact
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-4">Support</h3>
              <ul className="space-y-3 text-slate-400 text-sm">
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Help Center
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Terms of Service
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-slate-800 pt-8 text-center text-slate-400 text-sm">
            <p>&copy; 2025 PropPal. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}


