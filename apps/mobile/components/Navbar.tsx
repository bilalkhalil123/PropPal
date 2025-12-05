import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  ScrollView,
  Modal,
} from 'react-native';
import { useRouter, useSegments } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { getUser, signOut } from '@/lib/auth';

const NAV_ITEMS = [
  { href: '/buyer', label: 'Buyer', icon: 'home' as const },
  { href: '/chat', label: 'Chat', icon: 'chatbubbles' as const },
  { href: '/seller', label: 'Seller', icon: 'storefront' as const },
  { href: '/builder', label: 'Builder', icon: 'business' as const },
  { href: '/profile', label: 'Profile', icon: 'person' as const },
];

export default function Navbar() {
  const router = useRouter();
  const segments = useSegments();
  const insets = useSafeAreaInsets();
  const [menuVisible, setMenuVisible] = useState(false);
  const [user, setUser] = useState<any>(null);

  // Get current pathname from segments
  const pathname = '/' + segments.join('/');

  React.useEffect(() => {
    const loadUser = async () => {
      const userData = await getUser();
      setUser(userData);
    };
    loadUser();
  }, []);

  const handleNavigation = (href: string) => {
    setMenuVisible(false);
    router.push(href as any);
  };

  const handleSignOut = async () => {
    await signOut();
    router.replace('/sign-in');
  };

  const activeIndex = NAV_ITEMS.findIndex(
    (item) => pathname === item.href || pathname?.startsWith(item.href + '/')
  );

  // Don't show navbar on sign-in/sign-up pages
  if (pathname === '/sign-in' || pathname === '/sign-up') {
    return null;
  }

  return (
    <>
      {/* Top Navbar */}
      <View
        style={[
          styles.navbar,
          {
            paddingTop: insets.top + 8,
            paddingBottom: 12,
          },
        ]}
      >
        {/* Logo/Brand */}
        <TouchableOpacity
          onPress={() => router.push('/buyer' as any)}
          style={styles.logoContainer}
        >
          <View style={styles.logoIcon}>
            <Ionicons name="home" size={24} color="#0a7ea4" />
          </View>
          <Text style={styles.logoText}>PropPal</Text>
        </TouchableOpacity>

        {/* Right Actions */}
        <View style={styles.rightActions}>
          <TouchableOpacity
            onPress={() => setMenuVisible(true)}
            style={styles.menuButton}
          >
            <Ionicons name="menu" size={24} color="#334155" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Bottom Tab Bar */}
      <View
        style={[
          styles.bottomNav,
          {
            paddingBottom: insets.bottom + 8,
          },
        ]}
      >
        {NAV_ITEMS.slice(0, 4).map((item, idx) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
          return (
            <TouchableOpacity
              key={item.href}
              onPress={() => handleNavigation(item.href)}
              style={styles.bottomNavItem}
            >
              <Ionicons
                name={isActive ? item.icon : (`${item.icon}-outline` as any)}
                size={24}
                color={isActive ? '#0a7ea4' : '#64748b'}
              />
              <Text
                style={[
                  styles.bottomNavLabel,
                  isActive && styles.bottomNavLabelActive,
                ]}
              >
                {item.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Menu Modal */}
      <Modal
        visible={menuVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setMenuVisible(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setMenuVisible(false)}
        >
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Menu</Text>
              <TouchableOpacity onPress={() => setMenuVisible(false)}>
                <Ionicons name="close" size={24} color="#334155" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.menuList}>
              {NAV_ITEMS.map((item) => {
                const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
                return (
                  <TouchableOpacity
                    key={item.href}
                    onPress={() => handleNavigation(item.href)}
                    style={[styles.menuItem, isActive && styles.menuItemActive]}
                  >
                    <Ionicons
                      name={item.icon}
                      size={22}
                      color={isActive ? '#0a7ea4' : '#334155'}
                    />
                    <Text
                      style={[
                        styles.menuItemText,
                        isActive && styles.menuItemTextActive,
                      ]}
                    >
                      {item.label}
                    </Text>
                    {isActive && (
                      <View style={styles.menuItemIndicator} />
                    )}
                  </TouchableOpacity>
                );
              })}

              {/* User Info */}
              {user && (
                <View style={styles.userInfo}>
                  <View style={styles.userAvatar}>
                    <Ionicons name="person" size={24} color="#0a7ea4" />
                  </View>
                  <View style={styles.userDetails}>
                    <Text style={styles.userName}>{user.name || user.email}</Text>
                    <Text style={styles.userEmail}>{user.email}</Text>
                  </View>
                </View>
              )}

              {/* Sign Out */}
              <TouchableOpacity
                onPress={handleSignOut}
                style={styles.signOutButton}
              >
                <Ionicons name="log-out-outline" size={22} color="#ef4444" />
                <Text style={styles.signOutText}>Sign Out</Text>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </TouchableOpacity>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  navbar: {
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 3,
  },
  logoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  logoIcon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: 'rgba(10, 126, 164, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#0a7ea4',
  },
  rightActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  menuButton: {
    padding: 4,
  },
  bottomNav: {
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingTop: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 5,
  },
  bottomNavItem: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    paddingVertical: 4,
  },
  bottomNavLabel: {
    fontSize: 11,
    color: '#64748b',
    fontWeight: '500',
  },
  bottomNavLabelActive: {
    color: '#0a7ea4',
    fontWeight: '600',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#ffffff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '80%',
    paddingBottom: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#0f172a',
  },
  menuList: {
    padding: 20,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    paddingVertical: 16,
    paddingHorizontal: 12,
    borderRadius: 12,
    marginBottom: 4,
    position: 'relative',
  },
  menuItemActive: {
    backgroundColor: 'rgba(10, 126, 164, 0.1)',
  },
  menuItemText: {
    fontSize: 16,
    color: '#334155',
    fontWeight: '500',
    flex: 1,
  },
  menuItemTextActive: {
    color: '#0a7ea4',
    fontWeight: '600',
  },
  menuItemIndicator: {
    position: 'absolute',
    left: 0,
    top: '50%',
    transform: [{ translateY: -12 }],
    width: 4,
    height: 24,
    backgroundColor: '#0a7ea4',
    borderRadius: 2,
  },
  userInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 16,
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    marginTop: 8,
    marginBottom: 16,
  },
  userAvatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(10, 126, 164, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  userDetails: {
    flex: 1,
  },
  userName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0f172a',
    marginBottom: 2,
  },
  userEmail: {
    fontSize: 14,
    color: '#64748b',
  },
  signOutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#fee2e2',
    backgroundColor: '#fef2f2',
    marginTop: 8,
  },
  signOutText: {
    fontSize: 16,
    color: '#ef4444',
    fontWeight: '600',
  },
});

