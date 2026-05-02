"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import dynamic from "next/dynamic"
import { MagnifyingGlassIcon } from "@heroicons/react/24/outline"

// Dynamically import react-leaflet components to avoid SSR issues
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

// Import Leaflet CSS
if (typeof window !== "undefined") {
  import("leaflet/dist/leaflet.css")
}

// Inner component that uses useMapEvents — must be a child of MapContainer
function MapClickHandler({ onMapClick }: { onMapClick: (lat: number, lng: number) => void }) {
  const [useMapEvents, setUseMapEvents] = useState<any>(null)

  useEffect(() => {
    import("react-leaflet").then((mod) => {
      setUseMapEvents(() => mod.useMapEvents)
    })
  }, [])

  if (!useMapEvents) return null

  return <MapClickHandlerInner useMapEvents={useMapEvents} onMapClick={onMapClick} />
}

function MapClickHandlerInner({
  useMapEvents,
  onMapClick,
}: {
  useMapEvents: any
  onMapClick: (lat: number, lng: number) => void
}) {
  useMapEvents({
    click(e: any) {
      onMapClick(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

// Component to fly the map to a new position programmatically
function FlyToHandler({ position }: { position: [number, number] | null }) {
  const [useMap, setUseMap] = useState<any>(null)

  useEffect(() => {
    import("react-leaflet").then((mod) => {
      setUseMap(() => mod.useMap)
    })
  }, [])

  if (!useMap || !position) return null

  return <FlyToInner useMap={useMap} position={position} />
}

function FlyToInner({ useMap, position }: { useMap: any; position: [number, number] }) {
  const map = useMap()
  useEffect(() => {
    if (position) {
      map.flyTo(position, 16, { duration: 1.2 })
    }
  }, [map, position])
  return null
}

// Nominatim search result
interface NominatimResult {
  place_id: number
  display_name: string
  lat: string
  lon: string
}

interface LocationPickerProps {
  lat?: number
  lng?: number
  onLocationChange: (lat: number, lng: number) => void
}

export default function LocationPicker({ lat, lng, onLocationChange }: LocationPickerProps) {
  const [isClient, setIsClient] = useState(false)
  const [markerIcon, setMarkerIcon] = useState<any>(null)
  const [markerPosition, setMarkerPosition] = useState<[number, number] | null>(
    lat && lng ? [lat, lng] : null
  )
  const [flyTarget, setFlyTarget] = useState<[number, number] | null>(null)

  // Search state
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<NominatimResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const searchContainerRef = useRef<HTMLDivElement>(null)

  // Default center: Islamabad
  const defaultCenter: [number, number] = [33.6844, 73.0479]

  useEffect(() => {
    setIsClient(true)
    if (typeof window !== "undefined") {
      import("leaflet").then((L) => {
        try {
          if (L.Icon.Default.prototype && (L.Icon.Default.prototype as any)._getIconUrl) {
            delete (L.Icon.Default.prototype as any)._getIconUrl
          }
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
        } catch (error) {
          console.error("Error setting up Leaflet icon:", error)
        }
      })
    }
  }, [])

  // Sync external prop changes
  useEffect(() => {
    if (lat && lng) {
      setMarkerPosition([lat, lng])
    }
  }, [lat, lng])

  // Close search results on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setShowResults(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleMapClick = useCallback(
    (clickLat: number, clickLng: number) => {
      setMarkerPosition([clickLat, clickLng])
      onLocationChange(clickLat, clickLng)
    },
    [onLocationChange]
  )

  const handleMarkerDragEnd = useCallback(
    (e: any) => {
      const newLat = e.target.getLatLng().lat
      const newLng = e.target.getLatLng().lng
      setMarkerPosition([newLat, newLng])
      onLocationChange(newLat, newLng)
    },
    [onLocationChange]
  )

  // Debounced search using Nominatim (free, no API key needed)
  const searchPlace = useCallback(async (query: string) => {
    if (!query.trim() || query.trim().length < 3) {
      setSearchResults([])
      setShowResults(false)
      return
    }

    setIsSearching(true)
    try {
      const params = new URLSearchParams({
        q: query,
        format: "json",
        limit: "5",
        countrycodes: "pk",
      })
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?${params}`,
        {
          headers: {
            "Accept": "application/json",
            "User-Agent": "PropPal/1.0",
          },
        }
      )
      if (response.ok) {
        const data: NominatimResult[] = await response.json()
        setSearchResults(data)
        setShowResults(data.length > 0)
      }
    } catch (error) {
      console.error("Geocoding search failed:", error)
    } finally {
      setIsSearching(false)
    }
  }, [])

  const handleSearchInputChange = (value: string) => {
    setSearchQuery(value)
    // Debounce: wait 500ms after user stops typing
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)
    searchTimeoutRef.current = setTimeout(() => {
      searchPlace(value)
    }, 500)
  }

  const handleSearchResultClick = (result: NominatimResult) => {
    const resultLat = parseFloat(result.lat)
    const resultLng = parseFloat(result.lon)
    setMarkerPosition([resultLat, resultLng])
    setFlyTarget([resultLat, resultLng])
    onLocationChange(resultLat, resultLng)
    setSearchQuery(result.display_name.split(",")[0]) // Show short name
    setShowResults(false)
  }

  if (!isClient) {
    return (
      <div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg overflow-hidden">
        <div className="h-[350px] w-full bg-slate-200 animate-pulse rounded-2xl" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Search Bar */}
      <div ref={searchContainerRef} className="relative">
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearchInputChange(e.target.value)}
            onFocus={() => searchResults.length > 0 && setShowResults(true)}
            placeholder="Search a place, e.g. FAST University, F-10 Markaz..."
            className="w-full pl-11 pr-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent text-sm"
          />
          {isSearching && (
            <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-slate-400" />
            </div>
          )}
        </div>

        {/* Search Results Dropdown */}
        {showResults && searchResults.length > 0 && (
          <div className="absolute z-50 w-full mt-1 bg-white rounded-xl border border-slate-200 shadow-xl overflow-hidden max-h-60 overflow-y-auto">
            {searchResults.map((result) => (
              <button
                key={result.place_id}
                type="button"
                onClick={() => handleSearchResultClick(result)}
                className="w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-b-0"
              >
                <p className="text-sm font-medium text-slate-800 line-clamp-1">
                  {result.display_name.split(",")[0]}
                </p>
                <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">
                  {result.display_name}
                </p>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Map */}
      <div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg overflow-hidden">
        <div className="h-[350px] w-full relative">
          <MapContainer
            center={markerPosition || defaultCenter}
            zoom={12}
            scrollWheelZoom={true}
            className="h-full w-full z-0"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <MapClickHandler onMapClick={handleMapClick} />
            <FlyToHandler position={flyTarget} />
            {markerPosition && markerIcon && (
              <Marker
                position={markerPosition}
                icon={markerIcon}
                draggable={true}
                eventHandlers={{ dragend: handleMarkerDragEnd }}
              >
                <Popup>
                  <div className="text-center">
                    <h4 className="font-semibold text-sm mb-1">Property Location</h4>
                    <p className="text-xs text-slate-600">
                      {markerPosition[0].toFixed(6)}, {markerPosition[1].toFixed(6)}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">Drag to adjust</p>
                  </div>
                </Popup>
              </Marker>
            )}
          </MapContainer>
        </div>
      </div>

      {/* Coordinate Display & Help text */}
      <div className="flex items-center justify-between px-1">
        <p className="text-xs text-slate-500">
          {markerPosition
            ? "📍 Drag the pin or click elsewhere to adjust"
            : "👆 Click on the map to set your property location"}
        </p>
        {markerPosition && (
          <span className="text-xs font-mono text-slate-400">
            {markerPosition[0].toFixed(5)}, {markerPosition[1].toFixed(5)}
          </span>
        )}
      </div>
    </div>
  )
}
