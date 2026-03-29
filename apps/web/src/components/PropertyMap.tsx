"use client"

import { useEffect, useState } from "react"
import dynamic from "next/dynamic"

// Dynamically import MapContainer to avoid SSR issues
const MapContainer = dynamic(
  () => import("react-leaflet").then((mod) => mod.MapContainer),
  { ssr: false }
)
const TileLayer = dynamic(
  () => import("react-leaflet").then((mod) => mod.TileLayer),
  { ssr: false }
)
const Marker = dynamic(
  () => import("react-leaflet").then((mod) => mod.Marker),
  { ssr: false }
)
const Popup = dynamic(
  () => import("react-leaflet").then((mod) => mod.Popup),
  { ssr: false }
)

// Import Leaflet CSS - using dynamic import to avoid SSR issues
if (typeof window !== "undefined") {
  import("leaflet/dist/leaflet.css")
}

interface POI {
  name?: string
  lat?: number
  lng?: number
  lon?: number
}

interface PropertyMapProps {
  lat: number
  lng: number
  title: string
  city?: string
  area?: string
  amenities?: Record<string, POI[]>
}

export default function PropertyMap({ lat, lng, title, city, area, amenities }: PropertyMapProps) {
  const [isClient, setIsClient] = useState(false)
  const [markerIcon, setMarkerIcon] = useState<any>(null)
  const [amenityMarkerIcon, setAmenityMarkerIcon] = useState<any>(null)

  useEffect(() => {
    setIsClient(true)
    // Fix for default marker icons in Next.js
    if (typeof window !== "undefined") {
      import("leaflet").then((L) => {
        // Fix for default marker icons - create a new icon instance
        try {
          // Delete the problematic _getIconUrl method if it exists
          if (L.Icon.Default.prototype && (L.Icon.Default.prototype as any)._getIconUrl) {
            delete (L.Icon.Default.prototype as any)._getIconUrl
          }
          
          // Create a new icon instance with proper URLs
          const icon = new L.Icon({
            iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
            iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
            shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            tooltipAnchor: [16, -28],
            shadowSize: [41, 41],
          })
          setMarkerIcon(icon)

          const amIcon = new L.DivIcon({
            className: "bg-transparent",
            html: `<div class="w-5 h-5 rounded-full bg-white border-2 border-slate-700 shadow flex items-center justify-center text-[10px] items-center">📍</div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10],
            popupAnchor: [0, -10],
          })
          setAmenityMarkerIcon(amIcon)
        } catch (error) {
          console.error("Error setting up Leaflet icon:", error)
          // Fallback: use default icon
          setMarkerIcon(L.Icon.Default)
          setAmenityMarkerIcon(L.Icon.Default)
        }
      })
    }
  }, [])

  // Validate coordinates
  const isValidCoordinate = (coord: number, type: "lat" | "lng") => {
    if (type === "lat") {
      return coord >= -90 && coord <= 90
    }
    return coord >= -180 && coord <= 180
  }

  if (!isValidCoordinate(lat, "lat") || !isValidCoordinate(lng, "lng")) {
    return (
      <div className="rounded-3xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg p-8">
        <h3 className="text-2xl font-bold text-[color:var(--color-primary)] mb-4">Location</h3>
        <p className="text-slate-600">Location coordinates are invalid.</p>
      </div>
    )
  }

  const locationText = [city, area].filter(Boolean).join(", ")

  if (!isClient) {
    return (
      <div className="rounded-3xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg overflow-hidden">
        <div className="p-6 md:p-8">
          <h3 className="text-2xl font-bold text-[color:var(--color-primary)] mb-2">Location</h3>
        </div>
        <div className="h-[500px] w-full bg-slate-200 animate-pulse rounded-b-3xl"></div>
      </div>
    )
  }

  return (
    <div className="rounded-3xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg overflow-hidden">
      <div className="p-6 md:p-8">
        <h3 className="text-2xl font-bold text-[color:var(--color-primary)] mb-2">Location</h3>
        {locationText && (
          <p className="text-slate-600 mb-4 flex items-center gap-2">
            <svg
              className="w-5 h-5 text-[color:var(--color-accent-gold)]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            {locationText}
          </p>
        )}
      </div>
      <div className="h-[500px] w-full relative">
        <MapContainer
          center={[lat, lng]}
          zoom={15}
          scrollWheelZoom={true}
          className="h-full w-full rounded-b-3xl z-0"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {markerIcon && (
            <Marker position={[lat, lng]} icon={markerIcon}>
              <Popup>
                <div className="text-center">
                  <h4 className="font-semibold text-sm mb-1">{title}</h4>
                  {locationText && <p className="text-xs text-slate-600">{locationText}</p>}
                </div>
              </Popup>
            </Marker>
          )}
          {amenities && amenityMarkerIcon && Object.entries(amenities).map(([category, pois]) =>
            pois.map((poi, idx) => {
              const poiLng = poi.lng || poi.lon
              if (poi.lat && poiLng) {
                return (
                  <Marker
                    key={`${category}-${idx}`}
                    position={[poi.lat, poiLng]}
                    icon={amenityMarkerIcon}
                  >
                    <Popup>
                      <div className="text-center">
                        <h4 className="font-semibold text-sm mb-1">{poi.name || "Amenity"}</h4>
                        <p className="text-xs text-slate-500 capitalize">{category.replace('_', ' ')}</p>
                      </div>
                    </Popup>
                  </Marker>
                )
              }
              return null
            })
          )}
        </MapContainer>
      </div>
      <div className="p-6 md:p-8 pt-4">
        <a
          href={`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 bg-[color:var(--color-primary)] text-white rounded-xl hover:bg-[color:var(--color-accent-gold)] transition-all text-sm font-medium"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
            />
          </svg>
          Get Directions
        </a>
      </div>
    </div>
  )
}

