/**
 * Configuration for PropPal Mobile App
 * 
 * Centralized configuration management using environment variables
 */

import Constants from 'expo-constants';

export const config = {
  // API Configuration
  apiUrl: Constants.expoConfig?.extra?.apiUrl || 
          process.env.EXPO_PUBLIC_API_URL || 
          'http://localhost:8000',
  
  // App Configuration
  appName: Constants.expoConfig?.name || 'PropPal',
  appVersion: Constants.expoConfig?.version || '1.0.0',
  
  // Environment
  isDev: __DEV__,
};

/**
 * Get the local IP address for development
 * This helps when connecting from a physical device
 */
export function getLocalIP(): string | null {
  // In development, you can use your computer's local IP
  // This should be set via environment variable or app.json
  return Constants.expoConfig?.extra?.localIp || null;
}

