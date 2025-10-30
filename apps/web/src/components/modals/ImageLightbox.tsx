"use client"

import { XMarkIcon, ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/outline"
import { motion, AnimatePresence } from "framer-motion"

interface ImageLightboxProps {
  isOpen: boolean
  images: string[]
  title: string
  currentIndex: number
  onClose: () => void
  onPrev: () => void
  onNext: () => void
  onDotClick: (index: number) => void
}

export default function ImageLightbox({
  isOpen,
  images,
  title,
  currentIndex,
  onClose,
  onPrev,
  onNext,
  onDotClick,
}: ImageLightboxProps) {
  if (!isOpen || !images || images.length === 0) return null

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[60] flex items-center justify-center backdrop-blur-2xl"
          role="dialog"
          aria-modal="true"
          aria-label="Image lightbox"
          onClick={onClose}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Background overlay with gradient */}
          <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/50 to-black/70 backdrop-blur-2xl transition-opacity" />

          <motion.div
            onClick={(e) => e.stopPropagation()}
            className="relative w-full h-full max-w-6xl mx-auto px-6 flex flex-col items-center justify-center"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            {/* Close Button */}
            <button
              aria-label="Close"
              onClick={onClose}
              className="absolute top-6 right-6 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white backdrop-blur-md border border-white/20 shadow-lg transition-all"
            >
              <XMarkIcon className="w-6 h-6" />
            </button>

            {/* Image Display */}
            <div className="relative w-full h-[75vh] mt-12 flex items-center justify-center">
              <motion.img
                key={currentIndex}
                src={images[currentIndex] || "/placeholder.svg"}
                alt={title}
                className="max-h-full max-w-full object-contain rounded-2xl shadow-[0_8px_32px_rgba(31,38,135,0.37)] border border-white/20 bg-white/5"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4 }}
              />

              {/* Navigation Arrows */}
              {images.length > 1 && (
                <>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onPrev()
                    }}
                    className="absolute left-3 md:left-8 top-1/2 -translate-y-1/2 bg-white/15 hover:bg-white/25 text-white rounded-full w-11 h-11 flex items-center justify-center shadow-lg backdrop-blur-sm border border-white/20 transition-all"
                    aria-label="Previous image"
                  >
                    <ChevronLeftIcon className="w-6 h-6" />
                  </button>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onNext()
                    }}
                    className="absolute right-3 md:right-8 top-1/2 -translate-y-1/2 bg-white/15 hover:bg-white/25 text-white rounded-full w-11 h-11 flex items-center justify-center shadow-lg backdrop-blur-sm border border-white/20 transition-all"
                    aria-label="Next image"
                  >
                    <ChevronRightIcon className="w-6 h-6" />
                  </button>
                </>
              )}
            </div>

            {/* Dots Navigation */}
            {images.length > 1 && (
              <div className="flex items-center justify-center gap-2 mt-6">
                {images.map((_, idx) => (
                  <button
                    key={idx}
                    aria-label={`Go to image ${idx + 1}`}
                    className={`w-3 h-3 rounded-full transition-all ${
                      idx === currentIndex
                        ? "bg-gradient-to-r from-indigo-400 to-purple-400 scale-110 shadow-md"
                        : "bg-white/40 hover:bg-white/60"
                    }`}
                    onClick={() => onDotClick(idx)}
                  />
                ))}
              </div>
            )}

            {/* Title Overlay */}
            <div className="absolute bottom-10 text-center text-white/90 text-lg font-medium tracking-wide backdrop-blur-md bg-white/10 px-5 py-2 rounded-full border border-white/20">
              {title}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
