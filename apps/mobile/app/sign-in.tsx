import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  ActivityIndicator,
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
import { storeToken, storeUser, AuthResponse } from '@/lib/auth';

const COLORS = {
  primary: '#0a7ea4',
  accentGold: '#f59e0b',
  white: '#ffffff',
  slate700: '#334155',
  slate300: '#cbd5e1',
  slate400: '#94a3b8',
  slate900: '#0f172a',
};

export default function SignInPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const handleSignIn = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    setLoading(true);
    try {
      const response: any = await api.auth.login(email, password);
      
      console.log('Login response:', JSON.stringify(response, null, 2));
      
      // Check if response has the expected structure
      if (!response) {
        Alert.alert('Error', 'Invalid response from server');
        setLoading(false);
        return;
      }
      
      // Handle different response structures
      const token = response.access_token || response.token;
      const user = response.user || response;
      
      if (!token) {
        Alert.alert('Error', 'No access token received');
        setLoading(false);
        return;
      }
      
      // Store token and user data
      await storeToken(token);
      if (user) {
        await storeUser(user);
      }
      
      // Navigate to buyer page
      router.replace('/buyer');
    } catch (err: any) {
      console.error('Login error:', err);
      const errorMessage = err.message || err.response?.data?.detail || 'Failed to sign in. Please try again.';
      Alert.alert('Error', errorMessage);
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={[styles.scrollContent, { paddingTop: insets.top }]}
        showsVerticalScrollIndicator={false}
      >
        {/* Background Image Section */}
        <Animated.View
          entering={FadeIn.duration(800)}
          style={styles.imageSection}
        >
          <Image
            source={{ uri: 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=1200' }}
            style={styles.backgroundImage}
            contentFit="cover"
          />
          <View style={styles.imageOverlay} />
          <View style={styles.imageContent}>
            <Animated.Text
              entering={FadeInDown.duration(600).delay(200)}
              style={styles.welcomeTitle}
            >
              Welcome to PropPal
            </Animated.Text>
            <Animated.Text
              entering={FadeInDown.duration(600).delay(300)}
              style={styles.welcomeSubtitle}
            >
              Your intelligent partner in finding dream properties with AI precision and elegance.
            </Animated.Text>
          </View>
        </Animated.View>

        {/* Sign-In Form Section */}
        <Animated.View
          entering={FadeIn.duration(800).delay(400)}
          style={styles.formSection}
        >
          <View style={styles.formCard}>
            <View style={styles.logoContainer}>
              <View style={styles.logoCircle}>
                <Text style={styles.logoText}>P</Text>
              </View>
            </View>

            <Text style={styles.formTitle}>Welcome Back</Text>
            <Text style={styles.formSubtitle}>Sign in to continue your property journey</Text>

            <View style={styles.form}>
              {/* Email Input */}
              <View style={styles.inputContainer}>
                <Text style={styles.label}>Email</Text>
                <View style={styles.inputWrapper}>
                  <Ionicons name="mail-outline" size={20} color={COLORS.slate400} style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Enter your email"
                    placeholderTextColor={COLORS.slate400}
                    value={email}
                    onChangeText={setEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                    autoComplete="email"
                    editable={!loading}
                  />
                </View>
              </View>

              {/* Password Input */}
              <View style={styles.inputContainer}>
                <Text style={styles.label}>Password</Text>
                <View style={styles.inputWrapper}>
                  <Ionicons name="lock-closed-outline" size={20} color={COLORS.slate400} style={styles.inputIcon} />
                  <TextInput
                    style={[styles.input, styles.passwordInput]}
                    placeholder="Enter your password"
                    placeholderTextColor={COLORS.slate400}
                    value={password}
                    onChangeText={setPassword}
                    secureTextEntry={!showPassword}
                    autoCapitalize="none"
                    autoComplete="password"
                    editable={!loading}
                  />
                  <TouchableOpacity
                    onPress={() => setShowPassword(!showPassword)}
                    style={styles.eyeIcon}
                    disabled={loading}
                  >
                    <Ionicons
                      name={showPassword ? 'eye-outline' : 'eye-off-outline'}
                      size={20}
                      color={COLORS.slate400}
                    />
                  </TouchableOpacity>
                </View>
              </View>

              {/* Forgot Password */}
              <TouchableOpacity style={styles.forgotPassword} disabled={loading}>
                <Text style={styles.forgotPasswordText}>Forgot password?</Text>
              </TouchableOpacity>

              {/* Sign In Button */}
              <TouchableOpacity
                style={[styles.signInButton, loading && styles.signInButtonDisabled]}
                onPress={handleSignIn}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color={COLORS.white} />
                ) : (
                  <Text style={styles.signInButtonText}>Sign In</Text>
                )}
              </TouchableOpacity>

              {/* Sign Up Link */}
              <View style={styles.signUpContainer}>
                <Text style={styles.signUpText}>Don't have an account? </Text>
                <TouchableOpacity onPress={() => router.push('/sign-up')} disabled={loading}>
                  <Text style={styles.signUpLink}>Sign up</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </Animated.View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9f9f9',
  },
  scrollContent: {
    flexGrow: 1,
  },
  imageSection: {
    height: 300,
    position: 'relative',
  },
  backgroundImage: {
    width: '100%',
    height: '100%',
  },
  imageOverlay: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    backgroundColor: 'rgba(249, 249, 249, 0.7)',
  },
  imageContent: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  welcomeTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    color: COLORS.primary,
    textAlign: 'center',
    marginBottom: 16,
  },
  welcomeSubtitle: {
    fontSize: 16,
    color: COLORS.slate700,
    textAlign: 'center',
    lineHeight: 24,
  },
  formSection: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 32,
    paddingBottom: 40,
  },
  formCard: {
    backgroundColor: COLORS.white,
    borderRadius: 24,
    padding: 32,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 5,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  logoCircle: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.white,
  },
  formTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: COLORS.primary,
    textAlign: 'center',
    marginBottom: 8,
  },
  formSubtitle: {
    fontSize: 14,
    color: COLORS.slate700,
    textAlign: 'center',
    marginBottom: 32,
  },
  form: {
    gap: 20,
  },
  inputContainer: {
    gap: 8,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.slate900,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.slate300,
    borderRadius: 12,
    backgroundColor: COLORS.white,
    paddingHorizontal: 16,
    minHeight: 52,
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    fontSize: 15,
    color: COLORS.slate900,
    paddingVertical: 0,
  },
  passwordInput: {
    paddingRight: 12,
  },
  eyeIcon: {
    padding: 4,
  },
  forgotPassword: {
    alignSelf: 'flex-end',
  },
  forgotPasswordText: {
    fontSize: 14,
    color: COLORS.accentGold,
    fontWeight: '500',
  },
  signInButton: {
    backgroundColor: COLORS.primary,
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 8,
    shadowColor: COLORS.accentGold,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  signInButtonDisabled: {
    opacity: 0.6,
  },
  signInButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.white,
  },
  signUpContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 8,
  },
  signUpText: {
    fontSize: 14,
    color: COLORS.slate700,
  },
  signUpLink: {
    fontSize: 14,
    color: COLORS.accentGold,
    fontWeight: '600',
  },
});
