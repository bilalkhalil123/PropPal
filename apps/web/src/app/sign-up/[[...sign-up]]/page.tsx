"use client"

import { SignUp } from '@clerk/nextjs'
import { motion } from 'framer-motion'

export default function SignUpPage() {
  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-2 overflow-hidden bg-[linear-gradient(to_bottom,#f9f9f9,#eceae4)]">
      {/* Left Visual Section */}
      <motion.div
        initial={{ opacity: 0, x: -40 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="hidden md:flex flex-col items-center justify-center relative bg-fixed bg-center bg-cover"
        style={{ backgroundImage: "url('/hero-house.jpg')" }}
      >
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(249,249,249,0.7),rgba(237,236,232,0.6))] backdrop-blur-sm" />
        <div className="relative z-10 text-center max-w-md px-10">
          <motion.h2
            className="text-4xl font-bold text-[color:var(--color-primary)] mb-4"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Welcome to PropPal
          </motion.h2>
          <p className="text-slate-700 leading-relaxed text-base">
            Create your account to start your luxury property journey.
          </p>
        </div>
      </motion.div>

      {/* Right Sign-Up Card */}
      <motion.div
        initial={{ opacity: 0, x: 40 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="flex items-center justify-center py-20 px-6 md:px-12 lg:px-24 bg-white/40 backdrop-blur-lg"
      >
        <div className="w-full max-w-md">
          <div className="flex justify-center">
            <SignUp
              routing="hash"
              appearance={{
                variables: {
                  colorPrimary: 'var(--color-accent-gold)',
                  colorText: '#111827',
                  colorBackground: '#ffffff',
                  borderRadius: '12px',
                  fontSize: '15px',
                },
                elements: {
                  card: 'rounded-2xl border border-slate-300 bg-white shadow-elevated',
                  headerTitle: 'text-slate-900 text-2xl md:text-3xl font-semibold tracking-tight',
                  headerSubtitle: 'text-slate-700 text-base',
                  formButtonPrimary:
                    'text-white rounded-2xl hover:ring-2 hover:ring-[color:var(--color-accent-gold)] active:scale-95 transition-all bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))]',
                  formFieldInput:
                    'rounded-xl border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:ring-2 focus:ring-[color:var(--color-accent-gold)] focus:border-[color:var(--color-accent-gold)]',
                  formFieldLabel: 'text-slate-900',
                  dividerLine: 'bg-slate-300',
                  dividerText: 'text-slate-700',
                  footerActionText: 'text-slate-800',
                  footerActionLink: 'text-[color:var(--color-accent-gold)] hover:text-amber-600',
                  socialButtonsBlockButton: 'rounded-xl border-slate-300 hover:bg-slate-50 text-slate-900',
                  identityPreview: 'text-slate-900',
                  formFieldHintText: 'text-slate-700',
                },
              }}
            />
          </div>
        </div>
      </motion.div>
    </div>
  )
}
