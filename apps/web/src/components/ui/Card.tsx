import React from "react"
const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(" ")

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean
  gradient?: "teal" | "emerald" | "blue" | "none"
}

const gradientMap = {
  teal: "from-teal-500/20 to-cyan-500/20",
  emerald: "from-emerald-500/20 to-teal-500/20",
  blue: "from-blue-500/20 to-cyan-500/20",
  none: "from-transparent to-transparent",
}

export default function Card({ hover = true, gradient = "none", className, children, ...props }: CardProps) {
  const gradientStyle =
    gradient === "none"
      ? undefined
      : {
          backgroundImage:
            gradient === "teal"
              ? "linear-gradient(to right, var(--color-primary)/20, var(--color-accent)/20)"
              : gradient === "emerald"
              ? "linear-gradient(to right, var(--color-accent)/20, var(--color-primary)/20)"
              : "linear-gradient(to right, var(--color-accent)/20, var(--color-primary)/20)",
        } as React.CSSProperties
  return (
    <div className={cx("p-[1px] rounded-xl") } style={gradientStyle}>
      <div
        className={cx(
          "rounded-xl bg-white/70 backdrop-blur-lg border border-slate-200/70 shadow-subtle",
          hover && "transition-transform duration-300 hover:-translate-y-1 hover:shadow-card",
          className
        )}
        {...props}
      >
        {children}
      </div>
    </div>
  )
}


