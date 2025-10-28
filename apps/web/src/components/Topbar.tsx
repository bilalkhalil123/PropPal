'use client'

import Link from 'next/link'
import { UserButton } from '@clerk/nextjs'
import { usePathname } from 'next/navigation'
import { useMemo } from 'react'
import { HomeIcon } from '@heroicons/react/24/outline'

// Segmented control items (include home/chat and roles together)
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
    <header className="bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60 sticky top-0 z-40 border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center">
        <Link href="/" className="flex items-center gap-2 text-indigo-600 hover:text-indigo-700">
          <HomeIcon className="h-6 w-6" />
          <span className="font-bold text-xl">PropPal</span>
        </Link>

        {/* Right side controls: segmented control + profile */}
        <div className="ml-auto hidden md:flex items-center gap-4">
          {/* Segmented control with glass effect */}
          <div className="relative h-10 rounded-2xl border border-white/30 bg-white/10 backdrop-blur-md shadow-inner overflow-hidden" style={{ width: '420px' }}>
            {/* moving glass */}
            <div
              className="absolute top-0 h-full rounded-2xl bg-white/40 backdrop-blur-xl shadow transition-all duration-300"
              style={{ width: `${segWidth}%`, left: `${activeIndex * segWidth}%` }}
            />
            <div className="relative z-10 grid grid-cols-5 h-full">
              {segments.map((r, idx) => (
                <Link
                  key={r.href}
                  href={r.href}
                  className={`flex items-center justify-center text-sm font-medium ${idx === activeIndex ? 'text-slate-800' : 'text-slate-600 hover:text-slate-800'}`}
                >
                  {r.label}
                </Link>
              ))}
            </div>
          </div>

          {/* Profile */}
          <Link href="/profile" className="hidden sm:inline text-sm text-slate-600 hover:text-indigo-700">Profile</Link>
          <UserButton afterSignOutUrl="/" />
        </div>
      </div>
    </header>
  )
}


