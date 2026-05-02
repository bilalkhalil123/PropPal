import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Modal,
  StyleSheet,
  Dimensions,
  Linking,
  ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Image } from 'expo-image';
import { Ionicons } from '@expo/vector-icons';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';
import { WebView } from 'react-native-webview';
import { api } from '@/lib/api-client';
import Constants from 'expo-constants';
import Navbar from '@/components/Navbar';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface Property {
  _id: string;
  title: string;
  price: number;
  city: string;
  area?: string;
  bedrooms: number;
  bathrooms: number;
  area_sqft: number;
  floors?: number;
  images?: string[];
  property_type: string;
  description?: string;
  amenity_summary?: string;
  nearby_amenities?: Record<string, POI[]>;
  lat?: number;
  lng?: number;
}

interface POI {
  name?: string;
  lat?: number;
  lng?: number;
  lon?: number;
  distance_m?: number;
  distance?: number;
  rating?: number;
}

// Helper function to get full image URL
const getImageUrl = (imageUrl: string | undefined): string | null => {
  if (!imageUrl) return null;
  
  // If already absolute URL, return as is
  if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
    return imageUrl;
  }
  
  // If relative URL, prepend API base URL
  const apiUrl = Constants.expoConfig?.extra?.apiUrl || 'http://localhost:8000';
  return `${apiUrl}${imageUrl.startsWith('/') ? '' : '/'}${imageUrl}`;
};

export default function PropertyDetailPage() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [property, setProperty] = useState<Property | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [isLightboxOpen, setIsLightboxOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [activeAmenityCategory, setActiveAmenityCategory] = useState<string | null>(null);

  useEffect(() => {
    console.log('PropertyDetailPage mounted with id:', id);
  }, [id]);

  useEffect(() => {
    const fetchProperty = async () => {
      console.log('Fetching property with id:', id);
      if (!id) {
        console.error('Property ID is missing');
        setError('Property ID is required');
        setLoading(false);
        return;
      }

      // Ensure id is a string (Expo Router can pass it as an array)
      const propertyId = Array.isArray(id) ? id[0] : id;
      console.log('Using property ID:', propertyId);

      try {
        setLoading(true);
        console.log('Calling API for property:', propertyId);
        const data = await api.properties.getById(propertyId);
        console.log('Property data received:', data);
        setProperty(data);
      } catch (err: any) {
        console.error('Error fetching property:', err);
        console.error('Error details:', JSON.stringify(err, null, 2));
        setError(err.message || 'Failed to load property details');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchProperty();
    }
  }, [id]);

  // Auto-slide images every 10 seconds
  useEffect(() => {
    const count = property?.images?.length ?? 0;
    if (count <= 1) return;

    const timer = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % count);
    }, 10000);

    return () => clearInterval(timer);
  }, [property?.images]);

  const nextImage = () => {
    const count = property?.images?.length ?? 0;
    if (count === 0) return;
    setCurrentImageIndex((prev) => (prev + 1) % count);
  };

  const prevImage = () => {
    const count = property?.images?.length ?? 0;
    if (count === 0) return;
    setCurrentImageIndex((prev) => (prev - 1 + count) % count);
  };

  const openDirections = () => {
    if (!property?.lat || !property?.lng) return;
    const url = `https://www.google.com/maps/dir/?api=1&destination=${property.lat},${property.lng}`;
    Linking.openURL(url);
  };

  if (loading) {
    return (
      <View className="flex-1 bg-[#f8f6f3] justify-center items-center">
        <ActivityIndicator size="large" color="#0a7ea4" />
        <Text className="text-slate-600 mt-4">Loading property details...</Text>
      </View>
    );
  }

  if (error || !property) {
    return (
      <View className="flex-1 bg-[#f8f6f3] justify-center items-center px-6">
        <Ionicons name="alert-circle-outline" size={64} color="#ef4444" />
        <Text className="text-xl font-semibold text-slate-900 mt-4 mb-2">
          {error || 'Property not found'}
        </Text>
        <Text className="text-slate-600 text-center mb-6">
          {error || 'The property you are looking for does not exist.'}
        </Text>
        <TouchableOpacity
          onPress={() => router.back()}
          className="bg-primary rounded-xl px-6 py-3"
        >
          <Text className="text-white font-semibold">Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const images = property.images && property.images.length > 0 
    ? property.images 
    : [];
  const descriptionText = property.description || 'No description provided for this property.';
  const canCollapseDescription = descriptionText.length > 150;
  const amenityEntries = Object.entries(property.nearby_amenities || {}).filter(
    ([, items]) => Array.isArray(items) && items.length > 0,
  );

  const getAmenityIcon = (category: string) => {
    const icons: Record<string, string> = {
      education: 'school',
      schools: 'school',
      healthcare: 'medkit',
      hospitals: 'medkit',
      transport: 'train',
      shopping: 'cart',
      food: 'restaurant',
      entertainment: 'film',
      parks: 'leaf',
      worship: 'business',
      place_of_worships: 'business',
      police: 'shield',
      pharmacies: 'medical',
    };
    return icons[category] || 'pin';
  };

  const mapHtml = (() => {
    if (!property.lat || !property.lng) return '';
    const amenityMarkers = amenityEntries.flatMap(([, pois]) =>
      pois
        .map((poi) => {
          const poiLng = poi.lng ?? poi.lon;
          if (!poi.lat || !poiLng) return null;
          const safeName = (poi.name || 'Amenity').replace(/"/g, '&quot;');
          return `L.marker([${poi.lat}, ${poiLng}], {icon: amenityIcon}).addTo(map).bindPopup("${safeName}");`;
        })
        .filter(Boolean)
        .join('\n'),
    );
    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map { height: 100%; margin: 0; padding: 0; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const map = L.map('map').setView([${property.lat}, ${property.lng}], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const homeIcon = L.icon({
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41]
    });
    const amenityIcon = L.divIcon({
      html: '<div style="width:20px;height:20px;border-radius:999px;background:#fff;border:2px solid #1f2937;display:flex;align-items:center;justify-content:center;font-size:10px;">📍</div>',
      className: '',
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });

    L.marker([${property.lat}, ${property.lng}], {icon: homeIcon}).addTo(map).bindPopup('Property Location');
    ${amenityMarkers}
  </script>
</body>
</html>`;
  })();

  return (
    <View className="flex-1 bg-[#f8f6f3]">
      <Navbar />
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{ paddingBottom: insets.bottom + 100 }}
      >
        {/* Hero Image Gallery */}
        <View style={{ height: SCREEN_HEIGHT * 0.5, position: 'relative' }}>
          {images.length > 0 ? (
            <>
              <Animated.View
                key={currentImageIndex}
                entering={FadeIn.duration(400)}
                exiting={FadeOut.duration(400)}
                style={StyleSheet.absoluteFillObject}
              >
                <Image
                  source={{ uri: getImageUrl(images[currentImageIndex]) || '' }}
                  style={StyleSheet.absoluteFillObject}
                  contentFit="cover"
                  transition={300}
                />
              </Animated.View>

              {/* Gradient Overlay */}
              <View 
                className="absolute inset-0"
                style={{
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                }}
              />

              {/* Title Overlay */}
              <View className="absolute bottom-0 left-0 right-0 p-6 z-10">
                <Text className="text-3xl font-bold text-white mb-2 drop-shadow-lg">
                  {property.title}
                </Text>
                <View className="flex-row items-center">
                  <Ionicons name="location" size={18} color="#f59e0b" />
                  <Text className="text-white/90 text-base ml-1">
                    {property.city}
                    {property.area ? ` • ${property.area}` : ''} • {property.property_type}
                  </Text>
                </View>
              </View>

              {/* Navigation Controls */}
              {images.length > 1 && (
                <>
                  <TouchableOpacity
                    onPress={prevImage}
                    className="absolute left-4 rounded-full p-3"
                    style={{ 
                      top: SCREEN_HEIGHT * 0.25 - 20,
                      backgroundColor: 'rgba(255, 255, 255, 0.2)',
                    }}
                  >
                    <Ionicons name="chevron-back" size={24} color="#ffffff" />
                  </TouchableOpacity>
                  <TouchableOpacity
                    onPress={nextImage}
                    className="absolute right-4 rounded-full p-3"
                    style={{ 
                      top: SCREEN_HEIGHT * 0.25 - 20,
                      backgroundColor: 'rgba(255, 255, 255, 0.2)',
                    }}
                  >
                    <Ionicons name="chevron-forward" size={24} color="#ffffff" />
                  </TouchableOpacity>

                  {/* Dots Indicator */}
                  <View className="absolute bottom-20 left-0 right-0 flex-row justify-center gap-2">
                    {images.map((_, i) => {
                      const isActive = i === currentImageIndex;
                      return (
                        <TouchableOpacity
                          key={`dot-${i}-${images.length}`}
                          onPress={() => setCurrentImageIndex(i)}
                          className={`w-3 h-3 rounded-full ${
                            isActive ? 'bg-[#f59e0b]' : 'bg-white/60'
                          }`}
                          style={{
                            transform: [{ scale: isActive ? 1.25 : 1 }],
                          }}
                        />
                      );
                    })}
                  </View>

                  {/* Thumbnails */}
                  <ScrollView
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    className="absolute bottom-4 left-0 right-0"
                    contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}
                  >
                    {images.map((img, i) => (
                      <TouchableOpacity
                        key={i}
                        onPress={() => {
                          setCurrentImageIndex(i);
                          setIsLightboxOpen(true);
                        }}
                        className={`rounded-xl overflow-hidden border-2 ${
                          i === currentImageIndex
                            ? 'border-[#f59e0b]'
                            : 'border-transparent opacity-80'
                        }`}
                      >
                        <Image
                          source={{ uri: getImageUrl(img) || '' }}
                          style={{ width: 80, height: 60 }}
                          contentFit="cover"
                        />
                      </TouchableOpacity>
                    ))}
                  </ScrollView>
                </>
              )}

              {/* Tap to open lightbox */}
              <TouchableOpacity
                onPress={() => setIsLightboxOpen(true)}
                style={StyleSheet.absoluteFillObject}
                activeOpacity={0.9}
              />
            </>
          ) : (
            <View className="flex-1 justify-center items-center bg-slate-200">
              <Ionicons name="home" size={64} color="#94a3b8" />
            </View>
          )}
        </View>

        {/* Property Overview Section */}
        <View className="px-4 py-6">
          <View className="bg-white/70 backdrop-blur-xl rounded-3xl border border-slate-200 shadow-lg p-6 mb-6">
            <View className="flex-row justify-between items-start mb-4">
              <View className="flex-1">
                <Text className="text-3xl font-bold text-[#0a7ea4] mb-2">
                  Rs {Number(property.price).toLocaleString()}
                </Text>
                <Text className="text-slate-600 font-medium capitalize">
                  {property.property_type}
                </Text>
              </View>
            </View>

            {/* Property Stats */}
            <View className="flex-row flex-wrap gap-3 mb-4">
              <View className="bg-[#0a7ea4] rounded-xl px-4 py-2">
                <Text className="text-white text-sm font-semibold">
                  {property.bedrooms} Bedrooms
                </Text>
              </View>
              <View className="bg-[#0a7ea4] rounded-xl px-4 py-2">
                <Text className="text-white text-sm font-semibold">
                  {property.bathrooms} Bathrooms
                </Text>
              </View>
              <View className="bg-[#0a7ea4] rounded-xl px-4 py-2">
                <Text className="text-white text-sm font-semibold">
                  {property.area_sqft} sqft
                </Text>
              </View>
            </View>

            {/* Description */}
            <Text className="text-slate-700 leading-relaxed mb-2">
              {isDescriptionExpanded || !canCollapseDescription
                ? descriptionText
                : `${descriptionText.slice(0, 170)}...`}
            </Text>
            {canCollapseDescription && (
              <TouchableOpacity onPress={() => setIsDescriptionExpanded((v) => !v)}>
                <Text className="text-[#0a7ea4] font-semibold text-sm mb-3">
                  {isDescriptionExpanded ? 'Show Less' : 'Read More'}
                </Text>
              </TouchableOpacity>
            )}

            {/* Neighborhood / amenities summary */}
            {property.amenity_summary && (
              <View className="mt-2 bg-slate-50 rounded-2xl p-4 border border-slate-200">
                <View className="flex-row items-center mb-2">
                  <Ionicons name="map" size={18} color="#0a7ea4" />
                  <Text className="ml-2 text-base font-semibold text-slate-900">
                    Neighborhood Highlights
                  </Text>
                </View>
                <Text className="text-sm text-slate-700 leading-5">
                  {property.amenity_summary}
                </Text>
                <View className="items-end mt-3">
                  <View className="bg-slate-200 rounded-full px-3 py-1">
                    <Text className="text-[10px] font-semibold text-slate-600">AI GENERATED SUMMARY</Text>
                  </View>
                </View>
              </View>
            )}

            {/* Amenities chips and details */}
            {amenityEntries.length > 0 && (
              <View className="mt-4">
                <Text className="text-xl font-bold text-[#0a7ea4] mb-3">Neighborhood Highlights</Text>
                <View className="flex-row flex-wrap gap-2 mb-3">
                  {amenityEntries.map(([category, items]) => {
                    const isActive = activeAmenityCategory === category;
                    return (
                      <TouchableOpacity
                        key={category}
                        onPress={() =>
                          setActiveAmenityCategory((prev) => (prev === category ? null : category))
                        }
                        className={`flex-row items-center rounded-full px-3 py-2 border ${
                          isActive ? 'bg-[#123e4a] border-[#123e4a]' : 'bg-white border-slate-200'
                        }`}
                      >
                        <Ionicons
                          name={getAmenityIcon(category) as any}
                          size={15}
                          color={isActive ? '#fff' : '#334155'}
                        />
                        <Text
                          className={`ml-2 font-semibold capitalize ${
                            isActive ? 'text-white' : 'text-slate-700'
                          }`}
                        >
                          {category.replace('_', ' ')}
                        </Text>
                        <View className={`ml-2 rounded-full px-2 py-0.5 ${isActive ? 'bg-white/20' : 'bg-slate-100'}`}>
                          <Text className={`text-xs font-bold ${isActive ? 'text-white' : 'text-slate-500'}`}>
                            {items.length}
                          </Text>
                        </View>
                      </TouchableOpacity>
                    );
                  })}
                </View>

                {activeAmenityCategory && property.nearby_amenities?.[activeAmenityCategory] && (
                  <View className="bg-slate-100 rounded-2xl p-3 border border-slate-200">
                    <View className="flex-row flex-wrap gap-2">
                      {property.nearby_amenities[activeAmenityCategory].slice(0, 8).map((poi, idx) => (
                        <View key={`${activeAmenityCategory}-${idx}`} className="w-[48%] bg-white rounded-2xl p-3 border border-slate-200">
                          <Text className="text-base font-bold text-slate-800" numberOfLines={1}>
                            {poi.name || 'Unknown'}
                          </Text>
                          {(poi.distance_m || poi.distance) ? (
                            <Text className="text-sm text-slate-500 mt-1">
                              {Math.round(Number(poi.distance_m || poi.distance))} meters away
                            </Text>
                          ) : null}
                          {poi.rating ? (
                            <View className="self-start mt-2 bg-amber-100 border border-amber-300 rounded-lg px-2 py-0.5">
                              <Text className="text-xs font-bold text-amber-700">★ {Number(poi.rating).toFixed(1)}</Text>
                            </View>
                          ) : null}
                        </View>
                      ))}
                    </View>
                  </View>
                )}
              </View>
            )}
          </View>

          {/* Contact Card */}
          <View className="bg-white/80 backdrop-blur-xl rounded-3xl border border-slate-200 shadow-lg p-6 mb-6">
            <Text className="text-2xl font-bold text-[#0a7ea4] mb-4">Interested?</Text>
            <Text className="text-slate-600 mb-6">
              Schedule a visit or connect with the builder today. Our team is available 24/7.
            </Text>
            <TouchableOpacity
              className="w-full py-3 rounded-xl items-center justify-center mb-6"
              style={{
                backgroundColor: '#f59e0b',
              }}
            >
              <Text className="text-white font-semibold text-base">Contact Agent</Text>
            </TouchableOpacity>
            <View className="gap-3">
              <View className="flex-row items-center gap-2">
                <Ionicons name="checkmark-circle" size={20} color="#10b981" />
                <Text className="text-sm text-slate-600">Verified Listing</Text>
              </View>
              <View className="flex-row items-center gap-2">
                <Ionicons name="checkmark-circle" size={20} color="#10b981" />
                <Text className="text-sm text-slate-600">No Hidden Fees</Text>
              </View>
              <View className="flex-row items-center gap-2">
                <Ionicons name="checkmark-circle" size={20} color="#10b981" />
                <Text className="text-sm text-slate-600">AI-Matched Recommendations</Text>
              </View>
            </View>
          </View>

          {/* Map Section */}
          {property.lat && property.lng && (
            <View className="bg-white/70 backdrop-blur-xl rounded-3xl border border-slate-200 shadow-lg overflow-hidden mb-6">
              <View className="p-6">
                <Text className="text-2xl font-bold text-[#0a7ea4] mb-2">Location</Text>
                <View className="flex-row items-center gap-2 mb-4">
                  <Ionicons name="location" size={20} color="#f59e0b" />
                  <Text className="text-slate-600">
                    {[property.city, property.area].filter(Boolean).join(', ')}
                  </Text>
                </View>
              </View>
              <View
                style={{
                  height: 300,
                  width: '100%',
                  borderRadius: 12,
                  overflow: 'hidden',
                  backgroundColor: '#e2e8f0',
                }}
              >
                <WebView
                  originWhitelist={['*']}
                  source={{ html: mapHtml }}
                  style={{ flex: 1 }}
                  javaScriptEnabled
                  domStorageEnabled
                  setSupportMultipleWindows={false}
                />
              </View>
              <View className="p-6 pt-4">
                <TouchableOpacity
                  onPress={openDirections}
                  className="flex-row items-center justify-center gap-2 bg-[#0a7ea4] rounded-xl px-4 py-3"
                >
                  <Ionicons name="navigate" size={20} color="#ffffff" />
                  <Text className="text-white font-semibold">Get Directions</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {/* CTA Section */}
          <View
            className="rounded-3xl overflow-hidden mb-6"
            style={{
              backgroundColor: '#0a7ea4',
            }}
          >
            <View className="p-8 items-center">
              <Text className="text-3xl font-bold text-white mb-4 text-center">
                Looking for More Properties Like This?
              </Text>
              <Text className="text-lg text-white/90 mb-6 text-center">
                Explore similar listings with our AI-powered property search.
              </Text>
              <TouchableOpacity
                onPress={() => router.push('/chat' as any)}
                className="bg-white rounded-xl px-8 py-4"
              >
                <Text className="text-[#0a7ea4] font-semibold text-base">
                  Try AI Property Search
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </ScrollView>

      {/* Image Lightbox Modal */}
      <Modal
        visible={isLightboxOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setIsLightboxOpen(false)}
      >
        <View className="flex-1 bg-black/90">
          <TouchableOpacity
            onPress={() => setIsLightboxOpen(false)}
            className="absolute top-12 right-6 z-10 bg-white/10 rounded-full p-3"
          >
            <Ionicons name="close" size={24} color="#ffffff" />
          </TouchableOpacity>

          <View className="flex-1 justify-center items-center px-4">
            {images.length > 0 && (
              <>
                <Animated.View
                  key={currentImageIndex}
                  entering={FadeIn.duration(300)}
                  exiting={FadeOut.duration(300)}
                  className="w-full"
                >
                  <Image
                    source={{ uri: getImageUrl(images[currentImageIndex]) || '' }}
                    style={{ width: SCREEN_WIDTH - 32, height: SCREEN_HEIGHT * 0.6 }}
                    contentFit="contain"
                  />
                </Animated.View>

                {images.length > 1 && (
                  <>
                    <TouchableOpacity
                      onPress={prevImage}
                      className="absolute left-4 rounded-full p-3"
                      style={{ 
                        top: SCREEN_HEIGHT * 0.3,
                        backgroundColor: 'rgba(255, 255, 255, 0.15)',
                      }}
                    >
                      <Ionicons name="chevron-back" size={24} color="#ffffff" />
                    </TouchableOpacity>
                    <TouchableOpacity
                      onPress={nextImage}
                      className="absolute right-4 rounded-full p-3"
                      style={{ 
                        top: SCREEN_HEIGHT * 0.3,
                        backgroundColor: 'rgba(255, 255, 255, 0.15)',
                      }}
                    >
                      <Ionicons name="chevron-forward" size={24} color="#ffffff" />
                    </TouchableOpacity>

                    <View className="absolute bottom-20 flex-row gap-2">
                      {images.map((_, i) => {
                        const isActive = i === currentImageIndex;
                        return (
                          <TouchableOpacity
                            key={`lightbox-dot-${i}-${images.length}`}
                            onPress={() => setCurrentImageIndex(i)}
                            className={`w-3 h-3 rounded-full ${
                              isActive ? 'bg-[#f59e0b]' : 'bg-white/40'
                            }`}
                            style={{
                              transform: [{ scale: isActive ? 1.1 : 1 }],
                            }}
                          />
                        );
                      })}
                    </View>
                  </>
                )}
              </>
            )}
          </View>
        </View>
      </Modal>
    </View>
  );
}

