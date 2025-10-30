"use client"

import { XMarkIcon } from "@heroicons/react/24/outline"

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
    <div
      className="fixed inset-0 z-[60] bg-black/90 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label="Image lightbox"
      onClick={onClose}
    >
      <div className="relative w-full h-full max-w-6xl mx-auto px-6" onClick={(e) => e.stopPropagation()}>
        <button
          aria-label="Close"
          onClick={onClose}
          className="absolute top-6 right-6 p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white"
        >
          <XMarkIcon className="w-6 h-6" />
        </button>

        <div className="h-[75vh] mt-16 relative flex items-center justify-center">
          <img src={images[currentIndex] || "/placeholder.svg"} alt={title} className="max-h-full max-w-full object-contain" />

          {images.length > 1 && (
            <>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onPrev()
                }}
                className="absolute left-2 md:left-6 top-1/2 -translate-y-1/2 bg-white/15 hover:bg-white/25 text-white rounded-full w-10 h-10 flex items-center justify-center"
                aria-label="Previous image"
              >
                ‹
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onNext()
                }}
                className="absolute right-2 md:right-6 top-1/2 -translate-y-1/2 bg-white/15 hover:bg-white/25 text-white rounded-full w-10 h-10 flex items-center justify-center"
                aria-label="Next image"
              >
                ›
              </button>
            </>
          )}
        </div>

        {images.length > 1 && (
          <div className="flex items-center justify-center gap-2 mt-6">
            {images.map((_, idx) => (
              <button
                key={idx}
                aria-label={`Go to image ${idx + 1}`}
                className={`w-2.5 h-2.5 rounded-full ${idx === currentIndex ? "bg-white" : "bg-white/40"} transition-colors`}
                onClick={() => onDotClick(idx)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}


