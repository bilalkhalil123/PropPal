import React from 'react';
import { View, Text, ScrollView } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import Navbar from '@/components/Navbar';

export default function SellerPage() {
  const insets = useSafeAreaInsets();

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
        {/* Coming Soon Section */}
        <View className="items-center justify-center px-6 py-16">
          {/* Icon */}
          <View 
            className="rounded-full p-6 mb-6"
            style={{ backgroundColor: 'rgba(10, 126, 164, 0.1)' }}
          >
            <Ionicons name="storefront" size={64} color="#0a7ea4" />
          </View>

          {/* Title */}
          <Text className="text-3xl font-bold text-slate-900 text-center mb-3">
            Seller Features
          </Text>
          <Text className="text-2xl font-bold text-[#0a7ea4] text-center mb-4">
            Coming Soon
          </Text>

          {/* Description */}
          <Text className="text-base text-slate-600 text-center mb-8 leading-6 px-4">
            We're working hard to bring you amazing seller features. Stay tuned for updates!
          </Text>

          {/* Features List */}
          <View className="w-full max-w-md gap-4">
            <View className="bg-white rounded-2xl p-5 border border-slate-200">
              <View className="flex-row items-start gap-4">
                <View 
                  className="rounded-xl p-3 mt-1"
                  style={{ backgroundColor: 'rgba(10, 126, 164, 0.1)' }}
                >
                  <Ionicons name="add-circle" size={24} color="#0a7ea4" />
                </View>
                <View className="flex-1">
                  <Text className="text-lg font-semibold text-slate-900 mb-1">
                    List Your Properties
                  </Text>
                  <Text className="text-sm text-slate-600 leading-5">
                    Easily add and manage your property listings with detailed information and photos.
                  </Text>
                </View>
              </View>
            </View>

            <View className="bg-white rounded-2xl p-5 border border-slate-200">
              <View className="flex-row items-start gap-4">
                <View 
                  className="rounded-xl p-3 mt-1"
                  style={{ backgroundColor: 'rgba(10, 126, 164, 0.1)' }}
                >
                  <Ionicons name="chatbubbles" size={24} color="#0a7ea4" />
                </View>
                <View className="flex-1">
                  <Text className="text-lg font-semibold text-slate-900 mb-1">
                    Manage Inquiries
                  </Text>
                  <Text className="text-sm text-slate-600 leading-5">
                    Respond to buyer inquiries and manage conversations all in one place.
                  </Text>
                </View>
              </View>
            </View>

            <View className="bg-white rounded-2xl p-5 border border-slate-200">
              <View className="flex-row items-start gap-4">
                <View 
                  className="rounded-xl p-3 mt-1"
                  style={{ backgroundColor: 'rgba(10, 126, 164, 0.1)' }}
                >
                  <Ionicons name="settings" size={24} color="#0a7ea4" />
                </View>
                <View className="flex-1">
                  <Text className="text-lg font-semibold text-slate-900 mb-1">
                    Advanced Settings
                  </Text>
                  <Text className="text-sm text-slate-600 leading-5">
                    Customize your seller profile, pricing, and listing preferences.
                  </Text>
                </View>
              </View>
            </View>
          </View>

          {/* Bottom Message */}
          <View className="mt-8 px-4">
            <Text className="text-sm text-slate-500 text-center leading-5">
              We're excited to launch these features soon. Check back regularly for updates!
            </Text>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

