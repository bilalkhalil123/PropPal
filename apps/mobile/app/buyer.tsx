import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
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
  FadeIn,
  FadeInDown,
} from 'react-native-reanimated';
import { Ionicons } from '@expo/vector-icons';
import { api } from '@/lib/api-client';
import { getUser, isAuthenticated } from '@/lib/auth';

const COLORS = {
  primary: '#0a7ea4',
  accentGold: '#f59e0b',
  white: '#ffffff',
  slate700: '#334155',
  slate300: '#cbd5e1',
  slate400: '#94a3b8',
  slate500: '#64748b',
  slate900: '#0f172a',
  slate50: '#f8fafc',
  slate200: '#e2e8f0',
  teal600: '#0d9488',
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
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);
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
      // Load popular properties first
      const popularResponse: any = await api.recommendations.properties('', 12);
      if (popularResponse?.properties) {
        setProperties(popularResponse.properties);
        setLoadingProperties(false);
      } else if (Array.isArray(popularResponse)) {
        setProperties(popularResponse);
        setLoadingProperties(false);
      }

      // Then load personalized recommendations if user is logged in
      if (user?.id) {
        try {
          const response: any = await api.recommendations.properties(user.id, 12);
          if (response?.properties && response.source === 'recent_searches') {
            setProperties(response.properties);
          } else if (Array.isArray(response)) {
            setProperties(response);
          }
        } catch (error: any) {
          console.error('Error loading personalized recommendations:', error);
        }
      }
    } catch (error: any) {
      console.error('Error loading recommendations:', error);
      setLoadingProperties(false);
      hasLoadedRef.current = false;
    }
  };

  // Lazy load when component is visible
  useEffect(() => {
    if (authLoading || !user) {
      return;
    }

    // Load immediately for mobile (no intersection observer needed)
    loadRecommendations();
  }, [user, authLoading]);

  const handleSearch = () => {
    if (searchQuery.trim()) {
      // TODO: Create chat page
      Alert.alert('AI Search', `Searching for: ${searchQuery}`);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    hasLoadedRef.current = false;
    await loadRecommendations();
    setRefreshing(false);
  };

  const filteredProperties = properties.filter((property) => {
    const matchesCity = selectedCity ? property.city === selectedCity : true;
    const matchesType = selectedType ? property.property_type === selectedType : true;
    const matchesPrice = property.price >= priceRange[0] && property.price <= priceRange[1];
    const matchesSearch = property.title.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCity && matchesType && matchesPrice && matchesSearch;
  });

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-PK', {
      style: 'currency',
      currency: 'PKR',
      minimumFractionDigits: 0,
    }).format(price);
  };

  const openPropertyDetails = (property: Property) => {
    // TODO: Create property details page
    Alert.alert('Property Details', `Viewing details for: ${property.title}`);
  };

  const openChat = (property: Property) => {
    // TODO: Create chat page
    Alert.alert('Chat', `Opening chat for: ${property.title}`);
  };

  const resetFilters = () => {
    setSelectedCity(null);
    setSelectedType(null);
    setPriceRange([0, 50000000]);
    setSearchQuery('');
  };

  if (authLoading) {
    return (
      <View style={[styles.container, styles.centerContent]}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <ScrollView
        ref={propertiesContainerRef}
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Hero Section with AI Search */}
        <View style={styles.heroSection}>
          <Text style={styles.heroTitle}>Discover Your Next Home</Text>
          <Text style={styles.heroSubtitle}>
            Use AI to find homes that perfectly match your preferences.
          </Text>

          <View style={styles.searchContainer}>
            <View style={styles.searchInputWrapper}>
              <Ionicons name="search" size={20} color={COLORS.slate400} style={styles.searchIcon} />
              <TextInput
                style={styles.searchInput}
                placeholder='Try "Homes under 50 lakhs in Islamabad"...'
                placeholderTextColor={COLORS.slate400}
                value={searchQuery}
                onChangeText={setSearchQuery}
                onSubmitEditing={handleSearch}
              />
            </View>
            <TouchableOpacity style={styles.searchButton} onPress={handleSearch}>
              <Ionicons name="sparkles" size={20} color={COLORS.white} />
              <Text style={styles.searchButtonText}>AI Search</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Filters Section */}
        <View style={styles.filtersSection}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filtersScroll}>
            <View style={styles.filtersContainer}>
              {/* City Filter */}
              <TouchableOpacity
                style={[styles.filterChip, selectedCity && styles.filterChipActive]}
                onPress={() => {
                  const cities = ['Lahore', 'Karachi', 'Islamabad'];
                  const currentIndex = selectedCity ? cities.indexOf(selectedCity) : -1;
                  const nextIndex = (currentIndex + 1) % (cities.length + 1);
                  setSelectedCity(nextIndex === 0 ? null : cities[nextIndex - 1]);
                }}
              >
                <Ionicons
                  name="location"
                  size={16}
                  color={selectedCity ? COLORS.white : COLORS.slate700}
                />
                <Text style={[styles.filterChipText, selectedCity && styles.filterChipTextActive]}>
                  {selectedCity || 'City'}
                </Text>
              </TouchableOpacity>

              {/* Property Type Filter */}
              <TouchableOpacity
                style={[styles.filterChip, selectedType && styles.filterChipActive]}
                onPress={() => {
                  const types = ['Villa', 'Apartment', 'House'];
                  const currentIndex = selectedType ? types.indexOf(selectedType) : -1;
                  const nextIndex = (currentIndex + 1) % (types.length + 1);
                  setSelectedType(nextIndex === 0 ? null : types[nextIndex - 1]);
                }}
              >
                <Ionicons
                  name="home"
                  size={16}
                  color={selectedType ? COLORS.white : COLORS.slate700}
                />
                <Text style={[styles.filterChipText, selectedType && styles.filterChipTextActive]}>
                  {selectedType || 'Type'}
                </Text>
              </TouchableOpacity>

              {/* Reset Button */}
              {(selectedCity || selectedType || priceRange[0] > 0 || priceRange[1] < 50000000) && (
                <TouchableOpacity style={styles.resetButton} onPress={resetFilters}>
                  <Ionicons name="close-circle" size={16} color={COLORS.primary} />
                  <Text style={styles.resetButtonText}>Reset</Text>
                </TouchableOpacity>
              )}
            </View>
          </ScrollView>
        </View>

        {/* Properties Section */}
        <View style={styles.propertiesSection}>
          {loadingProperties ? (
            <View style={styles.propertiesGrid}>
              {[...Array(6)].map((_, idx) => (
                <View key={idx} style={styles.propertyCardSkeleton}>
                  <View style={styles.skeletonImage} />
                  <View style={styles.skeletonContent}>
                    <View style={styles.skeletonLine} />
                    <View style={[styles.skeletonLine, { width: '60%' }]} />
                    <View style={[styles.skeletonLine, { width: '40%', marginTop: 12 }]} />
                    <View style={[styles.skeletonLine, { width: '30%', marginTop: 8 }]} />
                  </View>
                </View>
              ))}
            </View>
          ) : filteredProperties.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="home-outline" size={64} color={COLORS.slate300} />
              <Text style={styles.emptyStateTitle}>No properties found</Text>
              <Text style={styles.emptyStateText}>
                {searchQuery || selectedCity || selectedType
                  ? 'Try adjusting your filters or search query.'
                  : user
                  ? "We couldn't find any recommendations. Start searching to get personalized recommendations!"
                  : 'Sign in to see personalized property recommendations based on your search history.'}
              </Text>
              {!searchQuery && !selectedCity && !selectedType && (
                <TouchableOpacity
                  style={styles.startSearchButton}
                  onPress={() => {
                    // TODO: Create chat page
                    Alert.alert('Start Searching', 'Chat feature coming soon!');
                  }}
                >
                  <Ionicons name="sparkles" size={20} color={COLORS.white} />
                  <Text style={styles.startSearchButtonText}>Start Searching</Text>
                </TouchableOpacity>
              )}
            </View>
          ) : (
            <View style={styles.propertiesGrid}>
              {filteredProperties.map((property, idx) => (
                <Animated.View
                  key={property._id}
                  entering={FadeInDown.duration(400).delay(idx * 50)}
                >
                  <TouchableOpacity
                    style={styles.propertyCard}
                    onPress={() => openPropertyDetails(property)}
                    activeOpacity={0.9}
                  >
                    {/* Property Image */}
                    <View style={styles.propertyImageContainer}>
                      {property.images && property.images.length > 0 ? (
                        <Image
                          source={{ uri: property.images[0] }}
                          style={styles.propertyImage}
                          contentFit="cover"
                          transition={200}
                        />
                      ) : (
                        <View style={styles.propertyImagePlaceholder}>
                          <Ionicons name="home" size={48} color={COLORS.slate400} />
                        </View>
                      )}
                    </View>

                    {/* Property Details */}
                    <View style={styles.propertyDetails}>
                      <Text style={styles.propertyTitle} numberOfLines={2}>
                        {property.title}
                      </Text>

                      {/* Price */}
                      <View style={styles.propertyPriceRow}>
                        <Ionicons name="cash" size={16} color={COLORS.teal600} />
                        <Text style={styles.propertyPrice}>
                          Rs {property.price.toLocaleString()}
                        </Text>
                      </View>

                      {/* Location */}
                      <View style={styles.propertyLocationRow}>
                        <Ionicons name="location" size={14} color={COLORS.slate400} />
                        <Text style={styles.propertyLocation}>{property.city}</Text>
                      </View>

                      {/* Property Stats */}
                      <View style={styles.propertyStats}>
                        <Text style={styles.propertyStat}>{property.bedrooms} bed</Text>
                        <Text style={styles.propertyStatDivider}>•</Text>
                        <Text style={styles.propertyStat}>{property.bathrooms} bath</Text>
                        <Text style={styles.propertyStatDivider}>•</Text>
                        <Text style={styles.propertyStat}>{property.area_sqft} sqft</Text>
                      </View>

                      {/* Property Type */}
                      <Text style={styles.propertyType}>{property.property_type}</Text>

                      {/* Action Buttons */}
                      <View style={styles.propertyActions}>
                        <TouchableOpacity
                          style={styles.viewDetailsButton}
                          onPress={(e) => {
                            e.stopPropagation();
                            openPropertyDetails(property);
                          }}
                        >
                          <Text style={styles.viewDetailsButtonText}>View Details</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                          style={styles.askAIButton}
                          onPress={(e) => {
                            e.stopPropagation();
                            openChat(property);
                          }}
                        >
                          <Ionicons name="chatbubble" size={16} color={COLORS.slate700} />
                          <Text style={styles.askAIButtonText}>Ask AI</Text>
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

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f6f3',
  },
  centerContent: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 40,
  },
  heroSection: {
    backgroundColor: COLORS.white,
    paddingHorizontal: 24,
    paddingVertical: 32,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.slate200,
  },
  heroTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    color: COLORS.slate900,
    textAlign: 'center',
    marginBottom: 8,
  },
  heroSubtitle: {
    fontSize: 16,
    color: COLORS.slate700,
    textAlign: 'center',
    marginBottom: 24,
  },
  searchContainer: {
    flexDirection: 'row',
    gap: 12,
  },
  searchInputWrapper: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.white,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.slate300,
    paddingHorizontal: 16,
    minHeight: 48,
  },
  searchIcon: {
    marginRight: 12,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    color: COLORS.slate900,
    paddingVertical: 0,
  },
  searchButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    paddingHorizontal: 20,
    paddingVertical: 12,
    gap: 8,
    shadowColor: COLORS.accentGold,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
  searchButtonText: {
    color: COLORS.white,
    fontSize: 15,
    fontWeight: '600',
  },
  filtersSection: {
    backgroundColor: COLORS.white,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.slate200,
  },
  filtersScroll: {
    flexGrow: 0,
  },
  filtersContainer: {
    flexDirection: 'row',
    paddingHorizontal: 24,
    gap: 12,
  },
  filterChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: COLORS.slate50,
    borderWidth: 1,
    borderColor: COLORS.slate300,
  },
  filterChipActive: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  filterChipText: {
    fontSize: 14,
    fontWeight: '500',
    color: COLORS.slate700,
  },
  filterChipTextActive: {
    color: COLORS.white,
  },
  resetButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: COLORS.slate50,
    borderWidth: 1,
    borderColor: COLORS.primary,
  },
  resetButtonText: {
    fontSize: 14,
    fontWeight: '500',
    color: COLORS.primary,
  },
  propertiesSection: {
    padding: 16,
  },
  propertiesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 16,
  },
  propertyCard: {
    width: '100%',
    backgroundColor: COLORS.white,
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
    marginBottom: 16,
  },
  propertyImageContainer: {
    width: '100%',
    height: 200,
    backgroundColor: COLORS.slate200,
  },
  propertyImage: {
    width: '100%',
    height: '100%',
  },
  propertyImagePlaceholder: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.slate200,
  },
  propertyDetails: {
    padding: 16,
  },
  propertyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.slate900,
    marginBottom: 12,
    lineHeight: 24,
  },
  propertyPriceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  propertyPrice: {
    fontSize: 20,
    fontWeight: 'bold',
    color: COLORS.teal600,
  },
  propertyLocationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 12,
  },
  propertyLocation: {
    fontSize: 14,
    color: COLORS.slate700,
  },
  propertyStats: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: COLORS.slate50,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  propertyStat: {
    fontSize: 12,
    color: COLORS.slate700,
  },
  propertyStatDivider: {
    fontSize: 12,
    color: COLORS.slate300,
  },
  propertyType: {
    fontSize: 12,
    color: COLORS.slate500,
    marginBottom: 12,
  },
  propertyActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 8,
  },
  viewDetailsButton: {
    flex: 1,
    backgroundColor: COLORS.primary,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  viewDetailsButtonText: {
    color: COLORS.white,
    fontSize: 14,
    fontWeight: '600',
  },
  askAIButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderWidth: 1,
    borderColor: COLORS.slate300,
    borderRadius: 10,
    paddingVertical: 12,
  },
  askAIButtonText: {
    color: COLORS.slate700,
    fontSize: 14,
    fontWeight: '500',
  },
  // Skeleton styles
  propertyCardSkeleton: {
    width: '100%',
    backgroundColor: COLORS.white,
    borderRadius: 16,
    overflow: 'hidden',
    marginBottom: 16,
  },
  skeletonImage: {
    width: '100%',
    height: 200,
    backgroundColor: COLORS.slate200,
  },
  skeletonContent: {
    padding: 16,
  },
  skeletonLine: {
    height: 16,
    backgroundColor: COLORS.slate200,
    borderRadius: 4,
    marginBottom: 8,
  },
  // Empty state
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
    paddingHorizontal: 32,
  },
  emptyStateTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: COLORS.slate700,
    marginTop: 16,
    marginBottom: 8,
  },
  emptyStateText: {
    fontSize: 14,
    color: COLORS.slate500,
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 20,
  },
  startSearchButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    paddingHorizontal: 24,
    paddingVertical: 12,
  },
  startSearchButtonText: {
    color: COLORS.white,
    fontSize: 15,
    fontWeight: '600',
  },
});

