"use client"

import { ScrollArea } from "@/components/ui/scroll-area"
import { motion } from "framer-motion"

export default function QuickSuggestions({
  suggestedQuestions,
  onSelect,
}: {
  suggestedQuestions: string[]
  onSelect: (q: string) => void
}) {
  return (
    <aside className="hidden lg:flex w-full flex-col min-h-0 px-2 py-3">
      <ScrollArea className="h-full w-full max-h-[85vh] pr-1 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="space-y-4"
        >
          {/* Quick Suggestions Card */}
          <div className="relative rounded-2xl bg-gradient-to-br from-white/60 to-white/40 backdrop-blur-lg border border-white/30 shadow-sm hover:shadow-md transition-all duration-300">
            {/* Soft glowing accent background */}
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-[color:var(--color-accent-gold)]/10 to-transparent blur-xl pointer-events-none" />
            <div className="relative p-4">
              <h3
                className="font-serif text-[color:var(--color-primary)] text-base font-semibold tracking-tight"
              >
                Quick Suggestions
              </h3>
              <p className="text-xs text-slate-500 mb-3">
                Jump in with a starter question
              </p>

              <div className="flex flex-wrap gap-2">
                {suggestedQuestions.map((q, i) => (
                  <motion.button
                    key={i}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => onSelect(q)}
                    className="inline-flex items-center gap-1.5 rounded-full border border-white/30 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white/50 hover:bg-[color:var(--color-accent-gold)]/10 hover:text-[color:var(--color-primary)] transition-all duration-200"
                  >
                    <span className="text-[color:var(--color-accent-gold)] text-xs">→</span>
                    {q}
                  </motion.button>
                ))}
              </div>
            </div>
          </div>

        </motion.div>
      </ScrollArea>
    </aside>
  )
}
