"use client"

import React from "react"
import Link from "next/link"

type ButtonVariant = "primary" | "secondary" | "ghost"
type ButtonSize = "sm" | "md" | "lg"

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  href?: string
}

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(" ")

const base = "inline-flex items-center justify-center rounded-xl font-semibold transition-all duration-200 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2"

const sizes: Record<ButtonSize, string> = {
  sm: "h-9 px-3 text-sm",
  md: "h-11 px-5 text-sm",
  lg: "h-12 px-6 text-base",
}

const variants: Record<ButtonVariant, string> = {
  primary:
    "text-[var(--color-primary-contrast)] shadow-cta hover:ring-2 hover:ring-[color:var(--color-primary)] bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent))]",
  secondary:
    "bg-white/10 backdrop-blur-md border border-white/30 text-white hover:border-white/60 hover:ring-1 hover:ring-white/40",
  ghost:
    "bg-transparent text-[color:var(--color-primary)] hover:bg-[color:var(--color-primary-lighter)]/20 border border-transparent",
}

export default function Button({ variant = "primary", size = "md", href, className, children, ...props }: ButtonProps) {
  const classes = cx(base, sizes[size], variants[variant], className)
  if (href) {
    return (
      <Link href={href} className={classes} aria-label={typeof children === "string" ? children : undefined}>
        {children}
      </Link>
    )
  }
  return (
    <button className={classes} {...props}>
      {children}
    </button>
  )
}


