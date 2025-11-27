"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

interface NavLink {
  href: string
  label: string
}

interface NavbarProps {
  links: NavLink[]
}

export default function Navbar({ links }: NavbarProps) {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])
  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 px-6 md:px-12 lg:px-24 transition-all ${
        scrolled
          ? "bg-white/10 backdrop-blur supports-[backdrop-filter]:bg-white/40 border-b border-white/20 shadow-md"
          : "bg-white/5 backdrop-blur-sm border-b border-white/10"
      }`}
      role="navigation"
      aria-label="Primary"
    >
      <div className="max-w-7xl mx-auto flex justify-between items-center py-4">
        <Link href="/" className="text-white text-xl font-bold tracking-tight">
          PropPal
        </Link>
        <div className="hidden md:flex space-x-8 text-white/90">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="relative text-sm font-medium transition-colors hover:text-white after:absolute after:inset-x-0 after:-bottom-1 after:h-[2px] after:bg-white/70 after:scale-x-0 after:origin-left hover:after:scale-x-100 after:transition-transform"
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  )
}


