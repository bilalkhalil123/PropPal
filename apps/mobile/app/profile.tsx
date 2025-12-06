import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Image } from 'expo-image';
import { Ionicons } from '@expo/vector-icons';
import { api } from '@/lib/api-client';
import { getUser, isAuthenticated, signOut, storeUser, User } from '@/lib/auth';
import Navbar from '@/components/Navbar';
import Constants from 'expo-constants';

// Helper function to get full image URL
const getImageUrl = (imageUrl: string | undefined): string | null => {
  if (!imageUrl) return null;
  if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
    return imageUrl;
  }
  const apiUrl = Constants.expoConfig?.extra?.apiUrl || 'http://localhost:8000';
  return `${apiUrl}${imageUrl.startsWith('/') ? '' : '/'}${imageUrl}`;
};

export default function ProfilePage() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    role: 'buyer',
  });

  // Check authentication and load user
  useEffect(() => {
    const loadUserData = async () => {
      const authenticated = await isAuthenticated();
      if (!authenticated) {
        router.replace('/sign-in');
        return;
      }

      try {
        setLoading(true);
        setError(null);
        
        // Try to get fresh user data from API
        const userData = await api.auth.getMe();
        
        if (userData) {
          setUser(userData);
          setFormData({
            name: userData.name || '',
            phone: userData.phone || '',
            role: userData.role || 'buyer',
          });
          // Update stored user data
          await storeUser(userData);
        } else {
          // Fallback to stored user data
          const storedUser = await getUser();
          if (storedUser) {
            setUser(storedUser);
            setFormData({
              name: storedUser.name || '',
              phone: storedUser.phone || '',
              role: storedUser.role || 'buyer',
            });
          }
        }
      } catch (err: any) {
        console.error('Error loading user:', err);
        // Fallback to stored user data
        const storedUser = await getUser();
        if (storedUser) {
          setUser(storedUser);
          setFormData({
            name: storedUser.name || '',
            phone: storedUser.phone || '',
            role: storedUser.role || 'buyer',
          });
        } else {
          setError(err?.message || 'Failed to load user');
        }
      } finally {
        setLoading(false);
      }
    };

    loadUserData();
  }, [router]);

  const handleUpdate = async () => {
    if (!user) return;

    try {
      setUpdating(true);
      setError(null);
      
      // For now, we'll update locally since we don't have an update endpoint
      // In a real app, you'd call: await api.users.update(user.id, formData)
      const updatedUser: User = {
        ...user,
        name: formData.name,
        phone: formData.phone,
        role: formData.role,
        updated_at: new Date().toISOString(),
      };
      
      setUser(updatedUser);
      await storeUser(updatedUser);
      setEditMode(false);
      
      Alert.alert('Success', 'Profile updated successfully');
    } catch (err: any) {
      setError(err?.message || 'Failed to update profile');
      Alert.alert('Error', err?.message || 'Failed to update profile');
    } finally {
      setUpdating(false);
    }
  };

  const handleCancel = () => {
    if (user) {
      setFormData({
        name: user.name || '',
        phone: user.phone || '',
        role: user.role || 'buyer',
      });
    }
    setEditMode(false);
    setError(null);
  };

  const handleSignOut = async () => {
    Alert.alert(
      'Sign Out',
      'Are you sure you want to sign out?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Sign Out',
          style: 'destructive',
          onPress: async () => {
            await signOut();
            router.replace('/sign-in');
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View className="flex-1 bg-[#f8f6f3] justify-center items-center">
        <ActivityIndicator size="large" color="#0a7ea4" />
      </View>
    );
  }

  if (!user) {
    return (
      <View className="flex-1 bg-[#f8f6f3] justify-center items-center px-6">
        <Text className="text-slate-600 text-center mb-4">
          Please sign in to view your profile.
        </Text>
        <TouchableOpacity
          onPress={() => router.replace('/sign-in')}
          className="bg-[#0a7ea4] rounded-xl px-6 py-3"
        >
          <Text className="text-white font-semibold">Sign In</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (error && !user) {
    return (
      <View className="flex-1 bg-[#f8f6f3] justify-center items-center px-6">
        <View className="bg-red-50 border border-red-200 rounded-2xl p-6 items-center max-w-md">
          <Text className="text-base font-semibold text-red-700 mb-2">Error</Text>
          <Text className="text-sm text-red-600 mb-4 text-center">{error}</Text>
          <TouchableOpacity
            onPress={() => {
              setError(null);
              setLoading(true);
              // Reload user data
              const loadUserData = async () => {
                const storedUser = await getUser();
                if (storedUser) {
                  setUser(storedUser);
                  setFormData({
                    name: storedUser.name || '',
                    phone: storedUser.phone || '',
                    role: storedUser.role || 'buyer',
                  });
                }
                setLoading(false);
              };
              loadUserData();
            }}
            className="bg-[#0a7ea4] rounded-xl px-4 py-2"
          >
            <Text className="text-white font-medium text-sm">Try Again</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin':
        return { bg: 'bg-purple-100', text: 'text-purple-800' };
      case 'builder':
        return { bg: 'bg-blue-100', text: 'text-blue-800' };
      case 'seller':
        return { bg: 'bg-green-100', text: 'text-green-800' };
      default:
        return { bg: 'bg-gray-100', text: 'text-gray-800' };
    }
  };

  const roleColors = getRoleColor(user.role);

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
        <View className="px-6 py-4">
          {/* Header */}
          <View className="flex-row items-center justify-between mb-6">
            <View className="flex-1">
              <Text className="text-3xl font-bold text-slate-900 mb-1">My Profile</Text>
              <Text className="text-sm text-slate-600">
                Manage your personal details and account preferences.
              </Text>
            </View>
            {!editMode && (
              <TouchableOpacity
                onPress={() => setEditMode(true)}
                className="bg-[#0a7ea4] rounded-xl px-5 py-2.5"
              >
                <Text className="text-white text-sm font-medium">Edit</Text>
              </TouchableOpacity>
            )}
          </View>

          {/* User Card */}
          <View className="bg-white rounded-2xl border border-slate-200 p-6 mb-4">
            {/* Avatar */}
            <View className="flex-row items-center gap-4 mb-6">
              <View className="h-24 w-24 rounded-full bg-gradient-to-br from-[#0a7ea4] to-[#f59e0b] p-[2px]">
                <View className="h-full w-full rounded-full bg-white items-center justify-center overflow-hidden">
                  {user.profile_image ? (
                    <Image
                      source={{ uri: getImageUrl(user.profile_image) || '' }}
                      style={{ width: '100%', height: '100%' }}
                      contentFit="cover"
                    />
                  ) : (
                    <Text className="text-3xl font-semibold text-slate-500">
                      {user.name?.charAt(0).toUpperCase() || 'U'}
                    </Text>
                  )}
                </View>
              </View>

              <View className="flex-1">
                <Text className="text-xl font-semibold text-slate-900">{user.name}</Text>
                <Text className="text-sm text-slate-600">{user.email}</Text>
                <View className={`mt-2 self-start px-2.5 py-1 rounded-full ${roleColors.bg}`}>
                  <Text className={`text-xs font-semibold ${roleColors.text}`}>
                    {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                  </Text>
                </View>
              </View>
            </View>

            {/* Form Fields */}
            <View className="gap-4">
              {/* Name */}
              <View>
                <Text className="text-sm font-medium text-slate-700 mb-1">Name</Text>
                {editMode ? (
                  <TextInput
                    value={formData.name}
                    onChangeText={(text) => setFormData({ ...formData, name: text })}
                    className="border border-slate-300 rounded-xl px-4 py-3 text-slate-900 bg-white"
                    placeholder="Enter your name"
                  />
                ) : (
                  <Text className="text-slate-900 py-2">{user.name}</Text>
                )}
              </View>

              {/* Email */}
              <View>
                <Text className="text-sm font-medium text-slate-700 mb-1">Email</Text>
                <Text className="text-slate-900 py-2">{user.email}</Text>
                <Text className="text-xs text-slate-500 mt-1">
                  Email cannot be changed.
                </Text>
              </View>

              {/* Phone */}
              <View>
                <Text className="text-sm font-medium text-slate-700 mb-1">Phone</Text>
                {editMode ? (
                  <TextInput
                    value={formData.phone}
                    onChangeText={(text) => setFormData({ ...formData, phone: text })}
                    className="border border-slate-300 rounded-xl px-4 py-3 text-slate-900 bg-white"
                    placeholder="Enter your phone number"
                    keyboardType="phone-pad"
                  />
                ) : (
                  <Text className="text-slate-900 py-2">{user.phone || 'Not provided'}</Text>
                )}
              </View>

              {/* Role */}
              <View>
                <Text className="text-sm font-medium text-slate-700 mb-1">Role</Text>
                {editMode ? (
                  <View className="border border-slate-300 rounded-xl bg-white">
                    <View className="flex-row">
                      {['buyer', 'seller', 'builder', 'admin'].map((role) => (
                        <TouchableOpacity
                          key={role}
                          onPress={() => setFormData({ ...formData, role })}
                          className={`flex-1 py-3 items-center ${
                            formData.role === role ? 'bg-[#0a7ea4]' : 'bg-white'
                          } ${formData.role === role ? 'rounded-xl' : ''}`}
                        >
                          <Text
                            className={`text-sm font-medium ${
                              formData.role === role ? 'text-white' : 'text-slate-700'
                            }`}
                          >
                            {role.charAt(0).toUpperCase() + role.slice(1)}
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                ) : (
                  <Text className="text-slate-900 py-2 capitalize">{user.role}</Text>
                )}
              </View>
            </View>

            {/* Account Info */}
            <View className="pt-6 mt-6 border-t border-slate-200">
              <Text className="text-sm font-semibold text-slate-800 mb-4">Account Details</Text>
              <View className="gap-4">
                <View>
                  <Text className="text-sm font-medium text-slate-700 mb-1">User ID</Text>
                  <Text className="text-slate-900 font-mono text-sm">{user.id}</Text>
                </View>
                <View>
                  <Text className="text-sm font-medium text-slate-700 mb-1">Member Since</Text>
                  <Text className="text-slate-900 text-sm">
                    {user.created_at
                      ? new Date(user.created_at).toLocaleDateString()
                      : 'N/A'}
                  </Text>
                </View>
              </View>
            </View>

            {/* Buttons */}
            {editMode && (
              <View className="flex-row justify-end gap-3 pt-6 mt-6 border-t border-slate-200">
                <TouchableOpacity
                  onPress={handleCancel}
                  className="border border-slate-300 rounded-xl px-4 py-2"
                >
                  <Text className="text-sm font-medium text-slate-700">Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={handleUpdate}
                  disabled={updating}
                  className="bg-[#0a7ea4] rounded-xl px-5 py-2.5"
                  style={{ opacity: updating ? 0.5 : 1 }}
                >
                  <Text className="text-white text-sm font-medium">
                    {updating ? 'Saving...' : 'Save Changes'}
                  </Text>
                </TouchableOpacity>
              </View>
            )}
          </View>

          {/* Sign Out Button */}
          <TouchableOpacity
            onPress={handleSignOut}
            className="bg-red-50 border border-red-200 rounded-xl p-4 flex-row items-center justify-center gap-2"
          >
            <Ionicons name="log-out-outline" size={20} color="#ef4444" />
            <Text className="text-red-600 font-semibold">Sign Out</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
}

