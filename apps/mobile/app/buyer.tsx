import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, {
  FadeInDown,
} from 'react-native-reanimated';
import { Ionicons } from '@expo/vector-icons';
import { api } from '@/lib/api-client';
import { getUser, isAuthenticated } from '@/lib/auth';
import Constants from 'expo-constants';
import Navbar from '@/components/Navbar';

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

interface Property {
  _id: string;
  title: string;
  price: number;
  city: string;
  bedrooms: number;
  bathrooms: number;
  area_sqft: number;
  images?: string[];
  property_type: string;
}

export default function BuyerPage() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [searchQuery, setSearchQuery] = useState('');
  const [priceRange, setPriceRange] = useState([0, 50000000]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [loadingProperties, setLoadingProperties] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const propertiesContainerRef = useRef<View>(null);
  const hasLoadedRef = useRef(false);

  // Check authentication
  useEffect(() => {
    const checkAuth = async () => {
      const authenticated = await isAuthenticated();
      if (!authenticated) {
        router.replace('/sign-in');
        return;
      }
      const userData = await getUser();
      setUser(userData);
      setAuthLoading(false);
    };
    checkAuth();
  }, [router]);

  // Load recommendations
  const loadRecommendations = async () => {
    if (loadingProperties || hasLoadedRef.current) {
      return;
    }

    hasLoadedRef.current = true;
    setLoadingProperties(true);

    try {
      // Get user ID - check both user.id and user._id for compatibility
      const userId = user?.id || user?._id || '';
      console.log('Loading recommendations for user:', userId);
      console.log('User object:', user);

      // Load personalized recommendations if user is logged in, otherwise load popular
      const response: any = await api.recommendations.properties(userId, 12);
      
      if (response?.properties) {
        // Response has properties array
        setProperties(response.properties);
        console.log('Loaded properties:', response.properties.length, 'source:', response.source);
      } else if (Array.isArray(response)) {
        // Response is directly an array
        setProperties(response);
        console.log('Loaded properties (array):', response.length);
      } else {
        console.warn('Unexpected response format:', response);
        setProperties([]);
      }
      
      setLoadingProperties(false);
    } catch (error: any) {
      console.error('Error loading recommendations:', error);
      setLoadingProperties(false);
      hasLoadedRef.current = false;
    }
  };

  // Load recommendations when user is available
  useEffect(() => {
    if (authLoading) {
      return;
    }

    // Reset the loaded flag when user changes
    hasLoadedRef.current = false;

    // Load recommendations (will use user.id if available, otherwise popular)
    loadRecommendations();
  }, [user?.id, authLoading]);

  const handleSearch = () => {
    if (searchQuery.trim()) {
      // Navigate to chat with the search query as a parameter
      router.push({
        pathname: '/chat',
        params: { query: searchQuery.trim() },
      } as any);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    hasLoadedRef.current = false;
    await loadRecommendations();
    setRefreshing(false);
  };

  const filteredProperties = properties.filter((property) => {
    const matchesPrice = property.price >= priceRange[0] && property.price <= priceRange[1];
    const matchesSearch = property.title.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesPrice && matchesSearch;
  });

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-PK', {
      style: 'currency',
      currency: 'PKR',
      minimumFractionDigits: 0,
    }).format(price);
  };

  const openPropertyDetails = (property: Property) => {
    console.log('Opening property details for:', property._id);
    const propertyId = typeof property._id === 'string' ? property._id : String(property._id);
    console.log('Property ID (string):', propertyId);
    console.log('Navigation path:', `/properties/${propertyId}`);
    
    // Use href format for Expo Router
    router.push(`/properties/${propertyId}` as any);
  };

  const openChat = (property: Property) => {
    router.push('/chat' as any);
  };

  const resetFilters = () => {
    setPriceRange([0, 50000000]);
    setSearchQuery('');
  };

  if (authLoading) {
    return (
      <View className="flex-1 bg-[#f8f6f3] justify-center items-center">
        <ActivityIndicator size="large" color="#0a7ea4" />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-[#f8f6f3]">
      <Navbar />
      <ScrollView
        ref={propertiesContainerRef}
        className="flex-1"
        contentContainerStyle={{ paddingBottom: 40 }}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{ paddingTop: 0 }}
      >
        {/* Hero Section with AI Search */}
        <View className="bg-white px-6 pt-4 border-b border-slate-200">
          <Text className="text-3xl font-bold text-slate-900 text-center mb-2">
            Discover Your Next Home
          </Text>
          <Text className="text-base text-slate-700 text-center mb-6">
            Use AI to find homes that perfectly match your preferences.
          </Text>

          <View className="flex-row gap-3">
            <View className="flex-1 flex-row items-center bg-white rounded-xl border border-slate-300 px-4" style={{ minHeight: 48 }}>
              <Ionicons name="search" size={20} color="#94a3b8" style={{ marginRight: 12 }} />
              <TextInput
                className="flex-1 text-base text-slate-900 py-0"
                placeholder='Try "Homes under 50 lakhs in Islamabad"...'
                placeholderTextColor="#94a3b8"
                value={searchQuery}
                onChangeText={setSearchQuery}
                onSubmitEditing={handleSearch}
              />
            </View>
            <TouchableOpacity 
              className="flex-row items-center justify-center bg-primary rounded-xl px-5 py-3 gap-2"
              style={{ 
                shadowColor: '#f59e0b', 
                shadowOffset: { width: 0, height: 2 }, 
                shadowOpacity: 0.2, 
                shadowRadius: 4, 
                elevation: 3 
              }}
              onPress={handleSearch}
            >
              <Ionicons name="sparkles" size={20} color="#ffffff" />
              <Text className="text-white text-base font-semibold">AI Search</Text>
            </TouchableOpacity>
          </View>
        </View>


        {/* Properties Section */}
        <View className="p-4">
          {loadingProperties ? (
            <View className="gap-4">
              {[...Array(6)].map((_, idx) => (
                <View key={idx} className="w-full bg-white rounded-2xl overflow-hidden" style={{ minHeight: 480 }}>
                  <View className="w-full h-[200px] bg-slate-200" />
                  <View className="p-4 flex-1 justify-between" style={{ minHeight: 280 }}>
                    <View>
                      <View className="h-6 bg-slate-200 rounded mb-2" style={{ minHeight: 48 }} />
                      <View className="h-5 bg-slate-200 rounded w-2/5 mb-2" />
                      <View className="h-4 bg-slate-200 rounded w-1/3 mb-3" />
                      <View className="h-12 bg-slate-200 rounded mb-3" />
                      <View className="h-4 bg-slate-200 rounded w-1/4" />
                    </View>
                    <View className="flex-row gap-3 mt-auto">
                      <View className="flex-1 h-11 bg-slate-200 rounded" />
                      <View className="flex-1 h-11 bg-slate-200 rounded" />
                    </View>
                  </View>
                </View>
              ))}
            </View>
          ) : filteredProperties.length === 0 ? (
            <View className="items-center justify-center py-16 px-8">
              <Ionicons name="home-outline" size={64} color="#cbd5e1" />
              <Text className="text-xl font-semibold text-slate-700 mt-4 mb-2">
                No properties found
              </Text>
              <Text className="text-sm text-slate-500 text-center mb-6 leading-5">
                {searchQuery
                  ? 'Try adjusting your search query.'
                  : user
                  ? "We couldn't find any recommendations. Start searching to get personalized recommendations!"
                  : 'Sign in to see personalized property recommendations based on your search history.'}
              </Text>
              {!searchQuery && (
                <TouchableOpacity
                  className="flex-row items-center gap-2 bg-primary rounded-xl px-6 py-3"
                  onPress={() => {
                    router.push('/chat' as any);
                  }}
                >
                  <Ionicons name="sparkles" size={20} color="#ffffff" />
                  <Text className="text-white text-base font-semibold">Start Searching</Text>
                </TouchableOpacity>
              )}
            </View>
          ) : (
            <View className="gap-4">
              {filteredProperties.map((property, idx) => (
                <Animated.View
                  key={property._id}
                  entering={FadeInDown.duration(400).delay(idx * 50)}
                  className="w-full"
                >
                  <TouchableOpacity
                    className="w-full bg-white rounded-2xl overflow-hidden"
                    style={{ 
                      shadowColor: '#000', 
                      shadowOffset: { width: 0, height: 2 }, 
                      shadowOpacity: 0.1, 
                      shadowRadius: 8, 
                      elevation: 3,
                      minHeight: 480,
                    }}
                    onPress={() => openPropertyDetails(property)}
                    activeOpacity={0.9}
                  >
                    {/* Property Image */}
                    <View style={{ width: '100%', height: 200, backgroundColor: '#e2e8f0', overflow: 'hidden' }}>
                      {(() => {
                        const imageUrl = getImageUrl(property.images?.[0]);
                        return imageUrl ? (
                          <Image
                            source={{ uri: imageUrl }}
                            style={{ width: '100%', height: '100%' }}
                            contentFit="cover"
                            transition={200}
                            cachePolicy="memory-disk"
                            onError={(error) => {
                              console.log('Image failed to load:', imageUrl, error);
                            }}
                            onLoad={() => {
                              console.log('Image loaded successfully:', imageUrl);
                            }}
                          />
                        ) : (
                          <View style={{ width: '100%', height: '100%', justifyContent: 'center', alignItems: 'center', backgroundColor: '#e2e8f0' }}>
                            <Ionicons name="home" size={48} color="#94a3b8" />
                          </View>
                        );
                      })()}
                    </View>

                    {/* Property Details */}
                    <View className="p-4 flex-1 justify-between" style={{ minHeight: 280 }}>
                      <View>
                        <Text className="text-lg font-semibold text-slate-900 mb-3 leading-6" numberOfLines={2} style={{ minHeight: 48 }}>
                          {property.title}
                        </Text>

                        {/* Price */}
                        <View className="flex-row items-center gap-2 mb-2">
                          <Ionicons name="cash" size={16} color="#0d9488" />
                          <Text className="text-xl font-bold text-teal-600">
                            Rs {property.price.toLocaleString()}
                          </Text>
                        </View>

                        {/* Location */}
                        <View className="flex-row items-center gap-1.5 mb-3">
                          <Ionicons name="location" size={14} color="#94a3b8" />
                          <Text className="text-sm text-slate-700" numberOfLines={1}>{property.city}</Text>
                        </View>

                        {/* Property Stats */}
                        <View className="flex-row items-center justify-between bg-slate-50 rounded-lg p-3 mb-3">
                          <Text className="text-xs text-slate-700">{property.bedrooms} bed</Text>
                          <Text className="text-xs text-slate-300">•</Text>
                          <Text className="text-xs text-slate-700">{property.bathrooms} bath</Text>
                          <Text className="text-xs text-slate-300">•</Text>
                          <Text className="text-xs text-slate-700">{property.area_sqft} sqft</Text>
                        </View>

                        {/* Property Type */}
                        <Text className="text-xs text-slate-500 mb-3">{property.property_type}</Text>
                      </View>

                      {/* Action Buttons */}
                      <View className="flex-row gap-3 mt-auto">
                        <TouchableOpacity
                          className="flex-1 bg-primary rounded-lg py-3 items-center justify-center"
                          style={{ minHeight: 44 }}
                          onPress={(e) => {
                            e.stopPropagation();
                            openPropertyDetails(property);
                          }}
                        >
                          <Text className="text-white text-sm font-semibold">View Details</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                          className="flex-1 flex-row items-center justify-center gap-1.5 border border-slate-300 rounded-lg py-3"
                          style={{ minHeight: 44 }}
                          onPress={(e) => {
                            e.stopPropagation();
                            openChat(property);
                          }}
                        >
                          <Ionicons name="chatbubble" size={16} color="#334155" />
                          <Text className="text-slate-700 text-sm font-medium">Ask AI</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  </TouchableOpacity>
                </Animated.View>
              ))}
            </View>
          )}
        </View>
      </ScrollView>
    </View>
  );
}
