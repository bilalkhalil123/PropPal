import React, { useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  StatusBar,
} from 'react-native';
import { Image } from 'expo-image';
import { Link, useRouter } from 'expo-router';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
  interpolate,
  Extrapolate,
} from 'react-native-reanimated';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Color constants matching web app
const COLORS = {
  primary: '#0a7ea4', // Teal/cyan primary
  accentGold: '#f59e0b', // Gold accent
  primaryDark: '#075e7a',
  white: '#ffffff',
  slate700: '#334155',
  slate900: '#0f172a',
  slate400: '#94a3b8',
  slate800: '#1e293b',
};

export default function LandingScreen() {
  const scrollY = useSharedValue(0);
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const handleScroll = (event: any) => {
    scrollY.value = event.nativeEvent.contentOffset.y;
  };

  // Animated navigation bar
  const navBarStyle = useAnimatedStyle(() => {
    const opacity = interpolate(
      scrollY.value,
      [0, 50],
      [0.5, 0.9],
      Extrapolate.CLAMP
    );
    const blur = scrollY.value > 8 ? 1 : 0;

    return {
      backgroundColor: `rgba(255, 255, 255, ${opacity})`,
      borderBottomWidth: scrollY.value > 8 ? 1 : 0.5,
      borderBottomColor: `rgba(255, 255, 255, ${opacity * 0.6})`,
    };
  });

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <ScrollView
        onScroll={handleScroll}
        scrollEventThrottle={16}
        showsVerticalScrollIndicator={false}
      >
        {/* Hero Section */}
        <View style={styles.heroSection}>
          {/* Background Image */}
          <Image
            source={{ uri: 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=1200' }}
            style={styles.heroBackground}
            contentFit="cover"
          />
          
          {/* Gradient Overlay */}
          <View style={styles.heroOverlay} />
          <View style={styles.heroBlur1} />
          <View style={styles.heroBlur2} />

          {/* Navigation */}
          <Animated.View style={[styles.navBar, navBarStyle, { paddingTop: insets.top }]}>
            <View style={styles.navContent}>
              <View style={styles.logoContainer}>
                <View style={styles.logoIcon}>
                  <Ionicons name="home" size={24} color={COLORS.primary} />
                </View>
                <Text style={styles.logoText}>PropPal</Text>
              </View>
              <View style={styles.navLinks}>
                <TouchableOpacity onPress={() => router.push('/')}>
                  <Text style={styles.navLink}>Features</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => router.push('/')}>
                  <Text style={styles.navLink}>Properties</Text>
                </TouchableOpacity>
              </View>
            </View>
          </Animated.View>

          {/* Hero Content */}
          <View style={[styles.heroContent, { paddingTop: insets.top + 100 }]}>
            <View style={styles.badge}>
              <Ionicons name="sparkles" size={16} color={COLORS.primary} />
              <Text style={styles.badgeText}>AI‑Powered Real Estate</Text>
            </View>

            <Text style={styles.heroTitle}>Find Your Dream Property</Text>
            <Text style={styles.heroSubtitle}>
              Discover properties with AI-powered search. Connect with builders and sellers seamlessly.
            </Text>

            <View style={styles.heroButtons}>
              <TouchableOpacity
                style={styles.primaryButton}
                onPress={() => router.push('/sign-up')}
              >
                <Text style={styles.primaryButtonText}>Get Started</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.secondaryButton}
                onPress={() => router.push('/sign-in')}
              >
                <Text style={styles.secondaryButtonText}>Sign In</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Scroll Indicator */}
          <View style={styles.scrollIndicator}>
            <Ionicons name="chevron-down" size={24} color={COLORS.white} />
            <Ionicons name="chevron-down" size={24} color={COLORS.white} style={{ marginTop: -12 }} />
          </View>
        </View>

        {/* Features Section */}
        <View style={styles.featuresSection}>
          <View style={styles.featuresBlur} />
          <View style={styles.featuresContent}>
            <Text style={styles.sectionTitle}>Why Choose PropPal?</Text>
            <Text style={styles.sectionSubtitle}>
              Experience the future of real estate with our AI-powered platform designed for buyers, sellers, and builders.
            </Text>

            <View style={styles.featuresGrid}>
              {/* Feature 1 */}
              <View style={styles.featureCard}>
                <View style={styles.featureGradient}>
                  <View style={styles.featureCardInner}>
                    <View style={styles.featureIcon}>
                      <Ionicons name="sparkles" size={28} color={COLORS.white} />
                    </View>
                    <Text style={styles.featureTitle}>AI-Powered Search</Text>
                    <Text style={styles.featureDescription}>
                      Find properties using natural language. Just describe what you're looking for, and our AI will do the rest.
                    </Text>
                  </View>
                </View>
              </View>

              {/* Feature 2 */}
              <View style={styles.featureCard}>
                <View style={styles.featureGradient}>
                  <View style={styles.featureCardInner}>
                    <View style={styles.featureIcon}>
                      <Ionicons name="people" size={28} color={COLORS.white} />
                    </View>
                    <Text style={styles.featureTitle}>Smart Matching</Text>
                    <Text style={styles.featureDescription}>
                      Our intelligent system matches buyers with sellers and connects builders with the right opportunities.
                    </Text>
                  </View>
                </View>
              </View>

              {/* Feature 3 */}
              <View style={styles.featureCard}>
                <View style={styles.featureGradient}>
                  <View style={styles.featureCardInner}>
                    <View style={styles.featureIcon}>
                      <Ionicons name="chatbubbles" size={28} color={COLORS.white} />
                    </View>
                    <Text style={styles.featureTitle}>24/7 AI Assistant</Text>
                    <Text style={styles.featureDescription}>
                      Get instant answers to your property questions with our intelligent chatbot available round the clock.
                    </Text>
                  </View>
                </View>
              </View>
            </View>
          </View>
        </View>

        {/* CTA Section */}
        <View style={styles.ctaSection}>
          <View style={styles.ctaBlur} />
          <View style={styles.ctaContent}>
            <Text style={styles.ctaTitle}>Ready to Find Your Dream Property?</Text>
            <Text style={styles.ctaSubtitle}>
              Join thousands of satisfied users who have found their perfect home with PropPal.
            </Text>
            <TouchableOpacity
              style={styles.ctaButton}
              onPress={() => router.push('/sign-up')}
            >
              <Text style={styles.ctaButtonText}>Start Your Journey Today</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <View style={styles.footerContent}>
            <View style={styles.footerSection}>
              <View style={styles.footerLogo}>
                <View style={styles.footerLogoIcon}>
                  <Ionicons name="home" size={24} color={COLORS.white} />
                </View>
                <Text style={styles.footerLogoText}>PropPal</Text>
              </View>
              <Text style={styles.footerDescription}>
                Your AI-powered real estate platform for the modern world.
              </Text>
            </View>

            <View style={styles.footerGrid}>
              <View style={styles.footerColumn}>
                <Text style={styles.footerHeading}>Platform</Text>
                <TouchableOpacity onPress={() => router.push('/chat')}>
                  <Text style={styles.footerLink}>For Buyers</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text style={styles.footerLink}>For Sellers</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => router.push('/builder')}>
                  <Text style={styles.footerLink}>For Builders</Text>
                </TouchableOpacity>
              </View>

              <View style={styles.footerColumn}>
                <Text style={styles.footerHeading}>Company</Text>
                <TouchableOpacity>
                  <Text style={styles.footerLink}>About</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text style={styles.footerLink}>Careers</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text style={styles.footerLink}>Contact</Text>
                </TouchableOpacity>
              </View>

              <View style={styles.footerColumn}>
                <Text style={styles.footerHeading}>Support</Text>
                <TouchableOpacity>
                  <Text style={styles.footerLink}>Help Center</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text style={styles.footerLink}>Privacy Policy</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text style={styles.footerLink}>Terms of Service</Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.footerBottom}>
              <Text style={styles.footerCopyright}>&copy; 2025 PropPal. All rights reserved.</Text>
            </View>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.white,
  },
  heroSection: {
    height: SCREEN_HEIGHT,
    position: 'relative',
  },
  heroBackground: {
    position: 'absolute',
    width: '100%',
    height: '100%',
  },
  heroOverlay: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    backgroundColor: 'rgba(249, 249, 249, 0.6)',
  },
  heroBlur1: {
    position: 'absolute',
    top: -128,
    right: -128,
    width: 320,
    height: 320,
    borderRadius: 160,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  heroBlur2: {
    position: 'absolute',
    bottom: -96,
    left: -96,
    width: 384,
    height: 384,
    borderRadius: 192,
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
  },
  navBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 50,
    borderBottomWidth: 0.5,
  },
  navContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 16,
  },
  logoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  logoIcon: {
    width: 40,
    height: 40,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.primary,
  },
  navLinks: {
    flexDirection: 'row',
    gap: 24,
  },
  navLink: {
    fontSize: 14,
    fontWeight: '500',
    color: COLORS.primary,
  },
  heroContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
    zIndex: 10,
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: COLORS.white,
    borderWidth: 1,
    borderColor: COLORS.primary,
    marginBottom: 32,
  },
  badgeText: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.primary,
  },
  heroTitle: {
    fontSize: 48,
    fontWeight: 'bold',
    color: COLORS.primary,
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 56,
  },
  heroSubtitle: {
    fontSize: 20,
    color: COLORS.slate700,
    textAlign: 'center',
    marginBottom: 40,
    lineHeight: 28,
    maxWidth: 600,
  },
  heroButtons: {
    flexDirection: 'row',
    gap: 16,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  primaryButton: {
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 16,
    backgroundColor: COLORS.accentGold,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  primaryButtonText: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.white,
  },
  secondaryButton: {
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: COLORS.primary,
    backgroundColor: 'rgba(255, 255, 255, 0.7)',
  },
  secondaryButtonText: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.primary,
  },
  scrollIndicator: {
    position: 'absolute',
    bottom: 32,
    left: '50%',
    transform: [{ translateX: -12 }],
    alignItems: 'center',
    opacity: 0.9,
  },
  featuresSection: {
    paddingVertical: 112,
    backgroundColor: COLORS.white,
    position: 'relative',
  },
  featuresBlur: {
    position: 'absolute',
    top: -96,
    left: '10%',
    right: '10%',
    height: 192,
    borderRadius: 24,
    backgroundColor: 'rgba(6, 182, 212, 0.1)',
  },
  featuresContent: {
    paddingHorizontal: 24,
    maxWidth: 1200,
    alignSelf: 'center',
    width: '100%',
  },
  sectionTitle: {
    fontSize: 40,
    fontWeight: 'bold',
    color: COLORS.primary,
    textAlign: 'center',
    marginBottom: 24,
  },
  sectionSubtitle: {
    fontSize: 20,
    color: COLORS.slate700,
    textAlign: 'center',
    marginBottom: 64,
    lineHeight: 28,
  },
  featuresGrid: {
    gap: 24,
  },
  featureCard: {
    marginBottom: 24,
  },
  featureGradient: {
    borderRadius: 16,
    padding: 1,
    backgroundColor: COLORS.primary,
  },
  featureCardInner: {
    borderRadius: 16,
    padding: 32,
    backgroundColor: 'rgba(255, 255, 255, 0.85)',
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  featureIcon: {
    width: 56,
    height: 56,
    borderRadius: 12,
    backgroundColor: COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
  },
  featureTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.primary,
    marginBottom: 12,
  },
  featureDescription: {
    fontSize: 16,
    color: COLORS.slate700,
    lineHeight: 24,
  },
  ctaSection: {
    paddingVertical: 112,
    backgroundColor: COLORS.primary,
    position: 'relative',
    overflow: 'hidden',
  },
  ctaBlur: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  ctaContent: {
    paddingHorizontal: 24,
    alignItems: 'center',
    zIndex: 10,
  },
  ctaTitle: {
    fontSize: 40,
    fontWeight: 'bold',
    color: COLORS.white,
    textAlign: 'center',
    marginBottom: 24,
  },
  ctaSubtitle: {
    fontSize: 20,
    color: 'rgba(255, 255, 255, 0.9)',
    textAlign: 'center',
    marginBottom: 40,
    lineHeight: 28,
  },
  ctaButton: {
    paddingHorizontal: 40,
    paddingVertical: 16,
    borderRadius: 12,
    backgroundColor: COLORS.white,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 8,
  },
  ctaButtonText: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.primary,
  },
  footer: {
    backgroundColor: COLORS.slate900,
    paddingVertical: 64,
  },
  footerContent: {
    paddingHorizontal: 24,
    maxWidth: 1200,
    alignSelf: 'center',
    width: '100%',
  },
  footerSection: {
    marginBottom: 48,
  },
  footerLogo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  footerLogoIcon: {
    width: 40,
    height: 40,
    backgroundColor: '#0891b2',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  footerLogoText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.white,
  },
  footerDescription: {
    fontSize: 14,
    color: COLORS.slate400,
    lineHeight: 20,
  },
  footerGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 32,
    marginBottom: 32,
  },
  footerColumn: {
    flex: 1,
    minWidth: 150,
  },
  footerHeading: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.white,
    marginBottom: 16,
  },
  footerLink: {
    fontSize: 14,
    color: COLORS.slate400,
    marginBottom: 12,
  },
  footerBottom: {
    borderTopWidth: 1,
    borderTopColor: COLORS.slate800,
    paddingTop: 32,
    alignItems: 'center',
  },
  footerCopyright: {
    fontSize: 14,
    color: COLORS.slate400,
  },
});
