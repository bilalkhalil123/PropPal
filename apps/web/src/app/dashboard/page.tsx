'use client'

import { useEffect } from 'react'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'

export default function DashboardPage() {
  const { user, loading, isAuthenticated } = useCurrentUser()
  const router = useRouter()

  useEffect(() => {
    if (!loading && isAuthenticated && user) {
      // Redirect based on user role
      switch (user.role) {
        case 'buyer':
          router.push('/buyer')
          break
        case 'builder':
          router.push('/builder')
          break
        case 'seller':
          router.push('/seller')
          break
        default:
          router.push('/buyer')
      }
    } else if (!loading && !isAuthenticated) {
      router.push('/sign-in')
    }
  }, [user, loading, isAuthenticated, router])

  return (
    <div
      className="min-h-screen flex items-center justify-center px-6 md:px-12 lg:px-24"
      style={{
        background:
          'linear-gradient(to bottom right, var(--background), #f4f3ef)',
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="flex flex-col items-center justify-center text-center rounded-2xl border border-slate-200/60 bg-white/70 backdrop-blur-xl shadow-card p-8 max-w-md"
      >
        <div className="relative w-14 h-14 mb-6">
          <div className="absolute inset-0 rounded-full border-2 border-[color:var(--color-accent-gold)] opacity-40 animate-ping"></div>
          <div className="animate-spin rounded-full h-14 w-14 border-t-2 border-[color:var(--color-primary)] mx-auto"></div>
        </div>
        <h2
          className="text-2xl font-bold tracking-tight text-[color:var(--foreground)]"
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          Redirecting to your dashboard...
        </h2>
        <p
          className="mt-2 text-slate-600"
          style={{ fontFamily: 'var(--font-sans)' }}
        >
          Please hold on while we prepare your personalized workspace.
        </p>
      </motion.div>
    </div>
  )
}
