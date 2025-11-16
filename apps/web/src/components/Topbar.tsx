'use client'

import Link from 'next/link'
import { UserButton } from '@clerk/nextjs'
import { usePathname } from 'next/navigation'
import { useMemo } from 'react'
import { HomeIcon } from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
const segments = [
  { href: '/', label: 'Home' },
  { href: '/chat', label: 'Chat' },
  { href: '/buyer', label: 'Buyer' },
  { href: '/seller', label: 'Seller' },
  { href: '/builder', label: 'Builder' },
]

export default function Topbar() {
  const pathname = usePathname()

  const activeIndex = useMemo(() => {
    const i = segments.findIndex(r => pathname === r.href || pathname.startsWith(r.href + '/'))
    return i >= 0 ? i : 0
  }, [pathname])
  const segWidth = 100 / segments.length

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="sticky top-0 z-50 border-b border-slate-200/60 bg-[linear-gradient(to_right,rgba(255,255,255,0.9),rgba(250,250,250,0.7))] backdrop-blur-md shadow-card"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-12 lg:px-24 py-3 flex items-center justify-between">
        {/* Left Brand */}
        <Link
          href="/"
          className="flex items-center gap-2 text-[color:var(--color-primary)] hover:text-[color:var(--color-accent-gold)] transition-colors"
        >
          <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))] text-white font-bold">
            <HomeIcon className="h-5 w-5" />
          </div>
          <span
            className="font-serif text-2xl font-bold tracking-tight"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            PropPal
          </span>
        </Link>

        {/* Right Controls */}
        <div className="hidden md:flex items-center gap-5">
          {/* Segmented Control */}
          <div
            className="relative h-10 rounded-2xl border border-white/30 bg-white/30 backdrop-blur-lg overflow-hidden shadow-inner"
            style={{ width: '440px' }}
          >
            {/* Moving indicator */}
            <motion.div
              layout
              transition={{ type: 'spring', stiffness: 250, damping: 25 }}
              className="absolute top-0 h-full rounded-2xl bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))] shadow-card"
              style={{ width: `${segWidth}%`, left: `${activeIndex * segWidth}%` }}
            />
            {/* Segment Items */}
            <div className="relative z-10 grid grid-cols-5 h-full">
              {segments.map((r, idx) => (
                <Link
                  key={r.href}
                  href={r.href}
                  className={`flex items-center justify-center text-sm font-medium transition-colors ${
                    idx === activeIndex
                      ? 'text-white'
                      : 'text-slate-700 hover:text-[color:var(--color-primary)]'
                  }`}
                  style={{ fontFamily: 'var(--font-sans)' }}
                >
                  {r.label}
                </Link>
              ))}
            </div>
          </div>

          {/* Profile */}
          <Link
            href="/profile"
            className="text-sm text-slate-700 hover:text-[color:var(--color-accent-gold)] transition-colors font-medium"
          >
            Profile
          </Link>
          <div className="ml-1">
            <UserButton afterSignOutUrl="/" />
          </div>
        </div>
      </div>
    </motion.header>
  )
}