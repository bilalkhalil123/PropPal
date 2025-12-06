import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '@/lib/api-client';
import { getUser, isAuthenticated } from '@/lib/auth';
import Navbar from '@/components/Navbar';

interface BuilderProfile {
  _id: string;
  company_name: string;
  specialization: string[];
  experience_years: number;
  rating?: number;
  location: {
    city: string;
    latitude: number;
    longitude: number;
  };
  about?: string;
  founded_year?: number;
  portfolio_images?: string[];
}

interface BuilderService {
  _id: string;
  title: string;
  description: string;
  category: string;
  base_price?: number;
  price_unit?: string;
  service_features?: string[];
}

export default function BuilderPage() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [searchQuery, setSearchQuery] = useState('');
  const [user, setUser] = useState<any>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [builderProfile, setBuilderProfile] = useState<BuilderProfile | null | undefined>(undefined);
  const [builderServices, setBuilderServices] = useState<BuilderService[]>([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);

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

  // Load builder data
  useEffect(() => {
    if (authLoading || !user?.id) return;
    
    let cancelled = false;
    const load = async () => {
      try {
        setDataLoading(true);
        setDataError(null);
        const [profile, services] = await Promise.all([
          api.builders.getProfile(user.id),
          api.builders.getServices(user.id),
        ]);
        if (!cancelled) {
          setBuilderProfile(profile);
          setBuilderServices(services || []);
        }
      } catch (err: any) {
        if (!cancelled) {
          setDataError(err?.message || 'Failed to load builder data');
        }
      } finally {
        if (!cancelled) {
          setDataLoading(false);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user?.id]);

  const handleSearch = () => {
    if (searchQuery.trim()) {
      router.push({
        pathname: '/chat',
        params: { query: searchQuery.trim() },
      } as any);
    }
  };

  const handleCreateProfile = () => {
    router.push({
      pathname: '/chat',
      params: { query: 'Create my builder profile' },
    } as any);
  };

  const handleManageServices = () => {
    router.push({
      pathname: '/chat',
      params: { query: 'Manage my services' },
    } as any);
  };

  if (authLoading || (dataLoading && typeof builderProfile === 'undefined')) {
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
        className="flex-1"
        contentContainerStyle={{ 
          paddingBottom: insets.bottom + 40,
          paddingTop: 20,
        }}
        showsVerticalScrollIndicator={false}
      >
        <View className="px-6 py-4 space-y-6">
          {/* Search Section */}
          <View className="bg-white rounded-2xl border border-slate-200 p-6">
            <View className="mb-6">
              <Text className="text-3xl font-bold text-slate-900 mb-2">Builder Dashboard</Text>
              <Text className="text-slate-600">
                Manage your profile, services, and connect with clients
              </Text>
            </View>
            <View className="flex-row gap-3">
              <View className="flex-1 relative">
                <Ionicons 
                  name="search" 
                  size={20} 
                  color="#94a3b8" 
                  style={{ position: 'absolute', left: 12, top: 14, zIndex: 1 }}
                />
                <TextInput
                  className="w-full pl-12 pr-4 py-3.5 border border-slate-300 rounded-xl text-slate-900 bg-white"
                  placeholder="Ask me anything about your profile or services..."
                  placeholderTextColor="#94a3b8"
                  value={searchQuery}
                  onChangeText={setSearchQuery}
                  onSubmitEditing={handleSearch}
                />
              </View>
              <TouchableOpacity
                onPress={handleSearch}
                className="bg-[#0a7ea4] rounded-xl px-5 py-3.5 flex-row items-center gap-2"
              >
                <Ionicons name="chatbubbles" size={20} color="#ffffff" />
                <Text className="text-white font-semibold">Chat</Text>
              </TouchableOpacity>
            </View>
            <Text className="text-sm text-slate-500 mt-3">
              💡 Try: "Update my profile", "Add new service", "View my ratings"
            </Text>
          </View>

          {/* Profile Section */}
          {dataLoading && (
            <View className="bg-white rounded-2xl border border-slate-200 p-6">
              <Text className="text-slate-600">Loading your builder data…</Text>
            </View>
          )}

          {dataError && (
            <View className="bg-red-50 rounded-2xl border border-red-200 p-6">
              <Text className="text-red-700 font-medium">{dataError}</Text>
            </View>
          )}

          {builderProfile ? (
            <View className="bg-white rounded-2xl border border-slate-200 p-6">
              <View className="flex-row items-center justify-between mb-6">
                <View className="flex-1">
                  <Text className="text-2xl font-bold text-slate-900">
                    {builderProfile.company_name}
                  </Text>
                  <Text className="text-slate-600 mt-1">Your professional profile</Text>
                </View>
                <TouchableOpacity
                  onPress={() => {
                    router.push({
                      pathname: '/chat',
                      params: { query: 'Update my builder profile' },
                    } as any);
                  }}
                  className="bg-slate-50 rounded-lg px-4 py-2.5 border border-slate-200"
                >
                  <Text className="text-sm font-medium text-slate-700">Edit Profile</Text>
                </TouchableOpacity>
              </View>

              <View className="gap-6">
                {/* Company Info */}
                <View className="gap-3">
                  <View className="flex-row items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <Text className="text-sm text-slate-600 font-medium">Experience</Text>
                    <Text className="text-lg font-bold text-slate-900">
                      {builderProfile.experience_years} years
                    </Text>
                  </View>
                  {builderProfile.founded_year && (
                    <View className="flex-row items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
                      <Text className="text-sm text-slate-600 font-medium">Founded</Text>
                      <Text className="text-lg font-bold text-slate-900">
                        {builderProfile.founded_year}
                      </Text>
                    </View>
                  )}
                  <View className="flex-row items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <Text className="text-sm text-slate-600 font-medium">Location</Text>
                    <Text className="text-lg font-bold text-slate-900">
                      {builderProfile.location.city}
                    </Text>
                  </View>
                  {builderProfile.rating && (
                    <View className="flex-row items-center justify-between p-4 bg-amber-50 rounded-lg border border-amber-200">
                      <Text className="text-sm text-slate-600 font-medium">Rating</Text>
                      <View className="flex-row items-center gap-2">
                        <Ionicons name="star" size={20} color="#f59e0b" />
                        <Text className="text-lg font-bold text-slate-900">
                          {builderProfile.rating}
                        </Text>
                      </View>
                    </View>
                  )}
                </View>

                {/* Specialization */}
                <View>
                  <Text className="text-sm font-semibold text-slate-900 mb-3">Specializations</Text>
                  <View className="flex-row flex-wrap gap-2">
                    {builderProfile.specialization.map((spec, index) => (
                      <View
                        key={index}
                        className="bg-amber-100 rounded-full px-4 py-2"
                      >
                        <Text className="text-sm font-medium text-amber-800">{spec}</Text>
                      </View>
                    ))}
                  </View>
                  {builderProfile.about && (
                    <View className="mt-6">
                      <Text className="text-sm font-semibold text-slate-900 mb-2">About</Text>
                      <Text className="text-slate-600 leading-6">{builderProfile.about}</Text>
                    </View>
                  )}
                </View>
              </View>
            </View>
          ) : (
            <View className="bg-white rounded-2xl border border-slate-200 p-12 items-center">
              <View className="w-16 h-16 bg-slate-100 rounded-2xl items-center justify-center mb-6">
                <Ionicons name="construct" size={32} color="#94a3b8" />
              </View>
              <Text className="text-2xl font-bold text-slate-900 mb-3">No Profile Found</Text>
              <Text className="text-slate-600 mb-8 text-center max-w-md">
                Create your builder profile to start managing your services and connecting with
                clients.
              </Text>
              <TouchableOpacity
                onPress={handleCreateProfile}
                className="bg-[#0a7ea4] rounded-xl px-6 py-3 flex-row items-center gap-2"
              >
                <Ionicons name="add-circle" size={20} color="#ffffff" />
                <Text className="text-white font-semibold">Create Your Profile</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Services Section */}
          {builderProfile && (
            <View className="bg-white rounded-2xl border border-slate-200 p-6">
              <View className="flex-row items-center justify-between mb-6">
                <View className="flex-1">
                  <Text className="text-2xl font-bold text-slate-900">Your Services</Text>
                  <Text className="text-slate-600 mt-1">Manage and showcase your offerings</Text>
                </View>
                <TouchableOpacity
                  onPress={handleManageServices}
                  className="bg-slate-50 rounded-lg px-4 py-2.5 border border-slate-200"
                >
                  <Text className="text-sm font-medium text-slate-700">Manage Services</Text>
                </TouchableOpacity>
              </View>

              {builderServices.length > 0 ? (
                <View className="gap-4">
                  {builderServices.map((service) => (
                    <View
                      key={service._id}
                      className="border border-slate-200 rounded-xl p-5 bg-white"
                    >
                      <View className="mb-3">
                        <Text className="font-semibold text-lg text-slate-900">
                          {service.title}
                        </Text>
                      </View>
                      <Text className="text-sm text-slate-600 mb-4" numberOfLines={2}>
                        {service.description}
                      </Text>
                      <View className="gap-2 mb-4 pb-4 border-b border-slate-200">
                        <View>
                          <Text className="text-xs text-slate-500">
                            <Text className="font-medium">Category:</Text> {service.category}
                          </Text>
                        </View>
                        {(service.base_price || service.price_unit) && (
                          <View>
                            <Text className="text-xs text-slate-500">
                              <Text className="font-medium">Price:</Text>{' '}
                              {service.base_price ? `Rs ${service.base_price.toLocaleString()}` : ''}
                              {service.price_unit ? ` ${service.price_unit}` : ''}
                            </Text>
                          </View>
                        )}
                      </View>
                      {service.service_features && service.service_features.length > 0 && (
                        <View>
                          <Text className="text-xs font-medium text-slate-700 mb-2">Features:</Text>
                          <View className="flex-row flex-wrap gap-1">
                            {service.service_features.slice(0, 3).map((feature, idx) => (
                              <View
                                key={idx}
                                className="bg-amber-100 rounded px-2 py-1"
                              >
                                <Text className="text-xs text-amber-700">{feature}</Text>
                              </View>
                            ))}
                            {service.service_features.length > 3 && (
                              <Text className="text-xs text-slate-500 self-center">
                                +{service.service_features.length - 3} more
                              </Text>
                            )}
                          </View>
                        </View>
                      )}
                    </View>
                  ))}
                </View>
              ) : (
                <View className="items-center py-12 bg-slate-50 rounded-xl border border-slate-200">
                  <Text className="text-slate-600 mb-4">No services added yet</Text>
                  <TouchableOpacity onPress={handleManageServices}>
                    <Text className="text-amber-600 font-semibold text-sm">
                      Add your first service →
                    </Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

