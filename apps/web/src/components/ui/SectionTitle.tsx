import React from "react"
const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(" ")

interface SectionTitleProps {
  eyebrow?: string
  title: string
  subtitle?: string
  center?: boolean
  className?: string
}

export default function SectionTitle({ eyebrow, title, subtitle, center = true, className }: SectionTitleProps) {
  return (
    <div className={cx("mb-12", center && "text-center", className)}>
      {eyebrow && (
        <div className="inline-flex items-center justify-center px-4 py-2 bg-white/10 backdrop-blur-md rounded-full border border-white/20 shadow-sm text-sm text-white/90">
          {eyebrow}
        </div>
      )}
      <h2 className={cx("mt-4 text-3xl md:text-5xl font-bold text-slate-900", center ? "" : "")}>{title}</h2>
      {subtitle && <p className="mt-3 text-lg md:text-xl text-slate-600 max-w-3xl mx-auto">{subtitle}</p>}
    </div>
  )
}


