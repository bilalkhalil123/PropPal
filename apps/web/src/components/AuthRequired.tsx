'use client'

import React from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { LockClosedIcon, SparklesIcon, ArrowRightIcon } from '@heroicons/react/24/outline'
import { Button } from './ui/button'

interface AuthRequiredProps {
  title: string
  description: string
  role?: string
}

export default function AuthRequired({ title, description, role }: AuthRequiredProps) {
  return (
    <div className="min-h-[80vh] flex items-center justify-center px-6">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-md w-full bg-white/70 backdrop-blur-xl border border-slate-200 shadow-xl rounded-3xl p-8 text-center"
      >
        <div className="w-16 h-16 bg-gradient-to-br from-[color:var(--color-primary)]/10 to-[color:var(--color-accent-gold)]/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <LockClosedIcon className="h-8 w-8 text-[color:var(--color-primary)]" />
        </div>
        
        <h2 className="text-2xl font-bold text-slate-900 mb-3">{title}</h2>
        <p className="text-slate-600 mb-8 leading-relaxed">
          {description}
        </p>

        <div className="space-y-4">
          <Link href="/sign-in">
            <Button className="w-full py-6 rounded-xl text-lg font-semibold bg-gradient-to-r from-[color:var(--color-primary)] to-[color:var(--color-accent-gold)] text-white shadow-md hover:shadow-lg transition-all group">
              Sign In to Continue
              <ArrowRightIcon className="h-5 w-5 ml-2 group-hover:translate-x-1 transition-transform" />
            </Button>
          </Link>
          
          <div className="flex items-center justify-center gap-2 text-sm text-slate-500 pt-4 border-t border-slate-100">
            <SparklesIcon className="h-4 w-4 text-[color:var(--color-accent-gold)]" />
            <span>Get personalized matches as a {role || 'user'}</span>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
