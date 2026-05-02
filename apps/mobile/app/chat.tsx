import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Image } from 'expo-image';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import Animated, { FadeInDown, FadeIn, useSharedValue, useAnimatedStyle, withTiming, interpolate } from 'react-native-reanimated';
import { api, API_URL } from '@/lib/api-client';
import { getUser, isAuthenticated } from '@/lib/auth';
import Constants from 'expo-constants';
import Navbar from '@/components/Navbar';
import * as SecureStore from 'expo-secure-store';

const SESSION_KEY = 'chat_session_id';

interface Property {
  _id: string;
  title: string;
  price: number;
  city: string;
  area?: string;
  bedrooms: number;
  bathrooms: number;
  area_sqft: number;
  images?: string[];
  property_type: string;
  score?: number;
  amenity_summary?: string;
}

interface Builder {
  _id: string;
  company_name: string;
  specialization: string[];
  experience_years: number;
  rating?: number;
  location?: {
    city: string;
  };
  about?: string;
  score?: number;
}

interface ServiceResult {
  _id?: string;
  service_name?: string;
  description?: string;
  category?: string;
  price_range_min?: number;
  price_range_max?: number;
  builder_id?: string;
  score?: number;
}

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  properties?: Property[];
  builders?: Builder[];
  services?: ServiceResult[];
}

// Helper function to get full image URL
const getImageUrl = (imageUrl: string | undefined): string | null => {
  if (!imageUrl) return null;
  if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
    return imageUrl;
  }
  const apiUrl = Constants.expoConfig?.extra?.apiUrl || 'http://localhost:8000';
  return `${apiUrl}${imageUrl.startsWith('/') ? '' : '/'}${imageUrl}`;
};

const QUICK_SUGGESTIONS = [
  'Find houses in Lahore under 50 lakhs',
  'Show me 3 bedroom apartments in Karachi',
  'Best builders in Islamabad',
  'Properties with swimming pool',
  'New construction homes',
];

export default function ChatPage() {
  const router = useRouter();
  const { query: initialQuery } = useLocalSearchParams<{ query?: string }>();
  const insets = useSafeAreaInsets();
  const scrollViewRef = useRef<ScrollView>(null);
  const [user, setUser] = useState<any>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content:
        "Welcome to PropPal AI! I'm here to help you find your perfect property or connect with builders. Ask me to find houses in specific cities, search by price range, or discover construction companies.",
      sender: 'ai',
      timestamp: new Date(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const hasProcessedInitialQuery = useRef(false);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [sessions, setSessions] = useState<Array<{ session_id: string; last_message: string; updated_at: string }>>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const recordingRef = useRef<Audio.Recording | null>(null);

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

  // Initialize session ID (matches web app format)
  useEffect(() => {
    const initSession = async () => {
      try {
        let sid = await SecureStore.getItemAsync(SESSION_KEY);
        if (!sid) {
          // Generate session ID in same format as web app
          sid = `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
          await SecureStore.setItemAsync(SESSION_KEY, sid);
        }
        setSessionId(sid);
      } catch {
        setSessionId('session_fallback');
      }
    };
    initSession();
  }, []);

  // Load chat sessions (matches web app)
  useEffect(() => {
    const loadSessions = async () => {
      if (!user?.id) return;
      setLoadingSessions(true);
      try {
        const res = await api.chat.listSessions(user.id) as any;
        setSessions(res?.sessions || []);
      } catch (error) {
        console.error('Error loading sessions:', error);
      } finally {
        setLoadingSessions(false);
      }
    };

    if (user?.id) {
      loadSessions();
    }
  }, [user?.id, sessionId, sidebarRefresh]);

  // Function to start new session (matches web app)
  const startNewSession = async () => {
    const newSid = `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
    try {
      await SecureStore.setItemAsync(SESSION_KEY, newSid);
      setSessionId(newSid);
      setSidebarRefresh((v) => v + 1);
      setIsSidebarOpen(false);
      // Reset messages to welcome message
      setMessages([
        {
          id: '1',
          content:
            "Welcome to PropPal AI! I'm here to help you find your perfect property or connect with builders. Ask me to find houses in specific cities, search by price range, or discover construction companies.",
          sender: 'ai',
          timestamp: new Date(),
        },
      ]);
      hasProcessedInitialQuery.current = false;
    } catch (error) {
      console.error('Error creating new session:', error);
    }
  };

  // Function to switch to a different session
  const switchToSession = async (newSessionId: string) => {
    try {
      await SecureStore.setItemAsync(SESSION_KEY, newSessionId);
      setSessionId(newSessionId);
      setIsSidebarOpen(false);
      hasProcessedInitialQuery.current = false;
      // History will be loaded automatically by the useEffect
    } catch (error) {
      console.error('Error switching session:', error);
    }
  };

  // Load chat history (matches web app behavior)
  useEffect(() => {
    const loadHistory = async () => {
      if (!user?.id || !sessionId) return;

      try {
        // Load history for the current session only (matches web app)
        const res = await api.chat.getHistory(user.id, sessionId, 50) as any;
        const serverMessages = (res?.messages || []) as Array<any>;
        
        if (serverMessages.length === 0) {
          // If no messages for this session, keep the welcome message (matches web app)
          setMessages([
            {
              id: '1',
              content:
                "Welcome to PropPal AI! I'm here to help you find your perfect property or connect with builders. Ask me to find houses in specific cities, search by price range, or discover construction companies.",
              sender: 'ai',
              timestamp: new Date(),
            },
          ]);
          return;
        }

        // Map messages from backend format to frontend format (matches web app)
        const mapped: Message[] = serverMessages.map((m: any, idx: number) => ({
          id: `${m.timestamp || 'ts'}-${idx}`,
          content: String(m.content || ''),
          sender: m.role === 'user' ? 'user' : 'ai',
          timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
          properties: m._payload?.properties || [],
          builders: m._payload?.builders || [],
          services: m._payload?.services || [],
        }));
        
        setMessages(mapped);
      } catch (error) {
        console.error('Error loading chat history:', error);
        // On error, keep welcome message
        setMessages([
          {
            id: '1',
            content:
              "Welcome to PropPal AI! I'm here to help you find your perfect property or connect with builders. Ask me to find houses in specific cities, search by price range, or discover construction companies.",
            sender: 'ai',
            timestamp: new Date(),
          },
        ]);
      }
    };

    // Load history whenever user and session are available (matches web app)
    if (user?.id && sessionId) {
      loadHistory();
    }
  }, [user?.id, sessionId]);

  // Process initial query from buyer page
  useEffect(() => {
    const processInitialQuery = async () => {
      if (
        hasProcessedInitialQuery.current ||
        !initialQuery ||
        !user?.id ||
        isLoading ||
        authLoading ||
        !sessionId
      ) {
        return;
      }

      // Get query string (handle array case)
      const queryText = Array.isArray(initialQuery) ? initialQuery[0] : initialQuery;
      if (!queryText || !queryText.trim()) {
        return;
      }

      hasProcessedInitialQuery.current = true;
      console.log('Processing initial query:', queryText);

      // Set the input message
      setInputMessage(queryText);

      // Automatically send the message after a short delay to ensure page is ready
      setTimeout(async () => {
        const text = queryText.trim();
        if (!text || !user?.id) return;

        const userMessage: Message = {
          id: Date.now().toString(),
          content: text,
          sender: 'user',
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInputMessage('');
        setIsLoading(true);

        try {
          const response = await api.chat.sendMessage({
            user_id: user.id,
            message: text,
            session_id: sessionId || 'session_fallback',
          }) as any;

          // Handle response structure (matches web app)
          const aiMessage: Message = {
            id: `${Date.now()}-ai`,
            content: response.response || response.message || 'I received your message.',
            sender: 'ai',
            timestamp: new Date(),
            properties: response.properties || [],
            builders: response.builders || [],
            services: response.services || [],
          };

          setMessages((prev) => [...prev, aiMessage]);
        } catch (error: any) {
          console.error('Error sending message:', error);
          const errorMessage: Message = {
            id: `${Date.now()}-error`,
            content: 'Sorry, I encountered an error. Please try again.',
            sender: 'ai',
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, errorMessage]);
        } finally {
          setIsLoading(false);
        }
      }, 500);
    };

    processInitialQuery();
  }, [initialQuery, user?.id, isLoading, authLoading, sessionId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, [messages]);

  const sendMessage = async (messageText?: string) => {
    const text = messageText || inputMessage.trim();
    if (!text || isLoading || !user?.id) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: text,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await api.chat.sendMessage({
        user_id: user.id,
        message: text,
        session_id: sessionId || 'session_fallback',
      }) as any;

      // Handle response structure (matches web app)
      const aiMessage: Message = {
        id: `${Date.now()}-ai`,
        content: response.response || response.message || 'I received your message.',
        sender: 'ai',
        timestamp: new Date(),
        properties: response.properties || [],
        builders: response.builders || [],
        services: response.services || [],
      };

      setMessages((prev) => [...prev, aiMessage]);
      // Refresh sidebar to update session list (matches web app)
      setSidebarRefresh((v) => v + 1);
    } catch (error: any) {
        console.error('Error sending message:', error);
        const errorMessage: Message = {
          id: `${Date.now()}-error`,
          content: 'Sorry, I encountered an error. Please try again.',
          sender: 'ai',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }
    };

  const handleQuickSuggestion = (suggestion: string) => {
    sendMessage(suggestion);
  };

  const openPropertyDetails = (property: Property) => {
    router.push(`/properties/${property._id}` as any);
  };

  // Animation for sidebar (must be before conditional returns)
  // Sidebar slides from left, so negative values mean off-screen
  const sidebarTranslateX = useSharedValue(-320);
  
  useEffect(() => {
    sidebarTranslateX.value = withTiming(isSidebarOpen ? 0 : -320, {
      duration: 300,
    });
  }, [isSidebarOpen]);

  const sidebarAnimatedStyle = useAnimatedStyle(() => {
    return {
      transform: [{ translateX: sidebarTranslateX.value }],
    };
  });

  const startRecording = async () => {
    if (isRecording) return;
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        setMessages((prev) => [
          ...prev,
          {
            id: `${Date.now()}-mic-permission`,
            content: 'Microphone permission is required to use voice search.',
            sender: 'ai',
            timestamp: new Date(),
          },
        ]);
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY,
      );
      recordingRef.current = recording;
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
      setIsRecording(false);
    }
  };

  const sendAudioToBackend = async (uri: string) => {
    if (!API_URL || !user?.id || !sessionId) {
      return;
    }

    setIsLoading(true);
    const transcribingId = `${Date.now()}-transcribing`;
    setMessages((prev) => [
      ...prev,
      {
        id: transcribingId,
        content: 'Transcribing audio…',
        sender: 'user',
        timestamp: new Date(),
      },
    ]);

    try {
      const formData = new FormData();
      formData.append('audio', {
        uri,
        name: 'voice-message.m4a',
        type: 'audio/m4a',
      } as any);
      formData.append('user_id', user.id);
      formData.append('session_id', sessionId);

      const response = await fetch(`${API_URL.replace(/\/$/, '')}/api/chat/message/audio`, {
        method: 'POST',
        body: formData,
        headers: {
          Accept: 'application/json',
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to transcribe audio');
      }

      const data = await response.json();
      const transcript: string =
        data?.metadata?.transcript || 'Voice message';

      // Replace the placeholder message with the transcript
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === transcribingId
            ? {
                ...msg,
                content: transcript,
              }
            : msg,
        ),
      );

      const aiMessage: Message = {
        id: `${Date.now()}-ai-audio`,
        content: data.response || data.message || 'I received your voice message.',
        sender: 'ai',
        timestamp: new Date(),
        properties: data.properties || [],
        builders: data.builders || [],
        services: data.services || [],
      };

      setMessages((prev) => [...prev, aiMessage]);
      setSidebarRefresh((v) => v + 1);
    } catch (error: any) {
      console.error('Error sending audio message:', error);
      const message = error?.message || 'Transcription failed. Please try again.';
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === transcribingId
            ? {
                ...msg,
                content: `Error: ${message}`,
              }
            : msg,
        ),
      );
    } finally {
      setIsLoading(false);
    }
  };

  const stopRecording = async () => {
    if (!isRecording || !recordingRef.current) return;
    try {
      const recording = recordingRef.current;
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setIsRecording(false);
      recordingRef.current = null;
      if (uri) {
        await sendAudioToBackend(uri);
      }
    } catch (error) {
      console.error('Error stopping recording:', error);
      setIsRecording(false);
    }
  };

  const cancelRecording = async () => {
    if (!isRecording || !recordingRef.current) return;
    try {
      const recording = recordingRef.current;
      await recording.stopAndUnloadAsync();
    } catch (error) {
      console.error('Error cancelling recording:', error);
    } finally {
      recordingRef.current = null;
      setIsRecording(false);
    }
  };

  const overlayAnimatedStyle = useAnimatedStyle(() => {
    const opacity = interpolate(sidebarTranslateX.value, [-320, 0], [0, 0.6]);
    return {
      opacity,
    };
  });

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
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1 }}
        keyboardVerticalOffset={insets.top + 60}
      >
        <View className="flex-1">
          {/* Sidebar Toggle Button */}
          <TouchableOpacity
            onPress={() => setIsSidebarOpen(true)}
            className="absolute top-20 left-4 z-10 bg-white rounded-full p-3"
            style={{
              shadowColor: '#0a7ea4',
              shadowOffset: { width: 0, height: 4 },
              shadowOpacity: 0.3,
              shadowRadius: 8,
              elevation: 8,
            }}
          >
            <Ionicons name="chatbubbles" size={22} color="#0a7ea4" />
          </TouchableOpacity>

          {/* Overlay */}
          <Animated.View
            style={[
              StyleSheet.absoluteFillObject,
              { backgroundColor: 'rgba(0, 0, 0, 0.6)', zIndex: 998, pointerEvents: isSidebarOpen ? 'auto' : 'none' },
              overlayAnimatedStyle,
            ]}
            pointerEvents={isSidebarOpen ? 'auto' : 'none'}
          >
            <TouchableOpacity
              style={StyleSheet.absoluteFillObject}
              activeOpacity={1}
              onPress={() => setIsSidebarOpen(false)}
            />
          </Animated.View>

          {/* Sidebar Panel */}
          <Animated.View
            style={[
              {
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: 320,
                backgroundColor: '#ffffff',
                zIndex: 999,
                paddingTop: insets.top,
                paddingBottom: insets.bottom,
                borderTopRightRadius: 24,
                borderBottomRightRadius: 24,
                shadowColor: '#000',
                shadowOffset: { width: 4, height: 0 },
                shadowOpacity: 0.3,
                shadowRadius: 16,
                elevation: 15,
              },
              sidebarAnimatedStyle,
            ]}
            pointerEvents={isSidebarOpen ? 'auto' : 'none'}
          >
            {/* Conversations Heading - At Top */}
            <View 
              className="px-6 pt-4 pb-3 border-b border-slate-100"
              style={{
                backgroundColor: 'rgba(10, 126, 164, 0.05)',
              }}
            >
              <View className="flex-row items-center justify-between">
                <View className="flex-row items-center gap-3">
                  <View 
                    className="rounded-xl p-2"
                    style={{ backgroundColor: 'rgba(10, 126, 164, 0.1)' }}
                  >
                    <Ionicons name="chatbubbles" size={22} color="#0a7ea4" />
                  </View>
                  <Text className="text-lg font-bold text-slate-900">Conversations</Text>
                </View>
                <TouchableOpacity 
                  onPress={() => setIsSidebarOpen(false)}
                  className="rounded-full p-2"
                  style={{ backgroundColor: 'rgba(0, 0, 0, 0.05)' }}
                >
                  <Ionicons name="close" size={20} color="#334155" />
                </TouchableOpacity>
              </View>
            </View>

            {/* New Chat Button */}
            <View className="px-6 py-4">
              <TouchableOpacity
                onPress={startNewSession}
                className="rounded-2xl py-4 items-center"
                style={{
                  backgroundColor: '#0a7ea4',
                  shadowColor: '#0a7ea4',
                  shadowOffset: { width: 0, height: 4 },
                  shadowOpacity: 0.3,
                  shadowRadius: 8,
                  elevation: 6,
                }}
              >
                <View className="flex-row items-center gap-2">
                  <Ionicons name="add-circle" size={22} color="#ffffff" />
                  <Text className="text-white font-bold text-base">New Chat</Text>
                </View>
              </TouchableOpacity>
            </View>

            {/* Sessions List */}
            <ScrollView 
              className="flex-1 px-6" 
              showsVerticalScrollIndicator={false}
              contentContainerStyle={{ paddingBottom: 20 }}
            >
              {loadingSessions ? (
                <View className="items-center justify-center py-12">
                  <ActivityIndicator size="small" color="#0a7ea4" />
                  <Text className="text-sm text-slate-500 mt-3 font-medium">Loading...</Text>
                </View>
              ) : sessions.length === 0 ? (
                <View className="items-center justify-center py-12">
                  <View 
                    className="rounded-full p-4 mb-4"
                    style={{ backgroundColor: 'rgba(10, 126, 164, 0.1)' }}
                  >
                    <Ionicons name="chatbubbles-outline" size={40} color="#0a7ea4" />
                  </View>
                  <Text className="text-base font-semibold text-slate-700 mb-1">
                    No conversations yet
                  </Text>
                  <Text className="text-sm text-slate-500 text-center px-4">
                    Start a new chat to see your conversations here
                  </Text>
                </View>
              ) : (
                <View className="gap-3">
                  {sessions.map((session) => (
                    <TouchableOpacity
                      key={session.session_id}
                      onPress={() => switchToSession(session.session_id)}
                      className={`p-4 rounded-2xl border-2 ${
                        sessionId === session.session_id
                          ? 'border-[#0a7ea4]'
                          : 'bg-white border-slate-200'
                      }`}
                      style={
                        sessionId === session.session_id
                          ? { backgroundColor: 'rgba(10, 126, 164, 0.08)' }
                          : {}
                      }
                      style={{
                        shadowColor: sessionId === session.session_id ? '#0a7ea4' : '#000',
                        shadowOffset: { width: 0, height: 2 },
                        shadowOpacity: sessionId === session.session_id ? 0.15 : 0.05,
                        shadowRadius: 4,
                        elevation: sessionId === session.session_id ? 4 : 2,
                      }}
                    >
                      <View className="flex-row items-start gap-3">
                        <View 
                          className={`rounded-xl p-2 ${
                            sessionId === session.session_id
                              ? 'bg-[#0a7ea4]'
                              : 'bg-slate-100'
                          }`}
                        >
                          <Ionicons 
                            name="chatbubble-ellipses" 
                            size={18} 
                            color={sessionId === session.session_id ? '#ffffff' : '#64748b'} 
                          />
                        </View>
                        <View className="flex-1">
                          <Text
                            className={`text-sm font-semibold mb-1.5 ${
                              sessionId === session.session_id
                                ? 'text-[#0a7ea4]'
                                : 'text-slate-800'
                            }`}
                            numberOfLines={2}
                          >
                            {session.last_message || 'Conversation'}
                          </Text>
                          <Text className="text-xs text-slate-400 font-medium">
                            {new Date(session.updated_at).toLocaleString([], {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </Text>
                        </View>
                        {sessionId === session.session_id && (
                          <View 
                            className="rounded-full w-2 h-2 mt-1"
                            style={{ backgroundColor: '#0a7ea4' }}
                          />
                        )}
                      </View>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
            </ScrollView>
          </Animated.View>

          {/* Messages Area */}
          <ScrollView
            ref={scrollViewRef}
            className="flex-1 px-4"
            contentContainerStyle={{ paddingTop: 16, paddingBottom: 16 }}
            showsVerticalScrollIndicator={false}
          >
            {messages.length === 1 && (
              <View className="items-center justify-center py-8 mb-4">
                <Ionicons name="sparkles" size={48} color="#f59e0b" />
                <Text className="text-lg font-semibold text-slate-900 mt-4 mb-2">
                  Start your conversation with PropPal AI
                </Text>
                <Text className="text-sm text-slate-600 text-center px-4 mb-4">
                  Ask about builders, properties, or your dream home.
                </Text>
                {/* New Chat Button */}
                <TouchableOpacity
                  onPress={startNewSession}
                  className="flex-row items-center gap-2 bg-[#0a7ea4] rounded-full px-4 py-2"
                >
                  <Ionicons name="add-circle-outline" size={18} color="#ffffff" />
                  <Text className="text-white font-semibold text-sm">New Chat</Text>
                </TouchableOpacity>
              </View>
            )}

            {/* Quick Suggestions (only show when no messages except welcome) */}
            {messages.length === 1 && (
              <View className="mb-6">
                <Text className="text-sm font-semibold text-slate-700 mb-3 px-1">
                  Quick Suggestions
                </Text>
                <View className="flex-row flex-wrap gap-2">
                  {QUICK_SUGGESTIONS.map((suggestion, idx) => (
                    <TouchableOpacity
                      key={idx}
                      onPress={() => handleQuickSuggestion(suggestion)}
                      className="bg-white/80 border border-slate-200 rounded-full px-4 py-2"
                    >
                      <Text className="text-xs text-slate-700">{suggestion}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            )}

            {/* Messages */}
            {messages.map((message) => {
              const hasProperties = message.properties && message.properties.length > 0;
              const hasBuilders = message.builders && message.builders.length > 0;
              const hasServices = message.services && message.services.length > 0;
              const showTextMessage = !hasProperties && !hasBuilders && !hasServices;

              return (
                <Animated.View
                  key={message.id}
                  entering={FadeInDown.duration(300)}
                  className="mb-4"
                >
                  {showTextMessage && (
                    <View
                      className={`flex-row ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <View
                        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                          message.sender === 'user'
                            ? ''
                            : 'bg-white/80 border border-slate-200'
                        }`}
                        style={
                          message.sender === 'user'
                            ? { backgroundColor: '#0a7ea4' }
                            : {}
                        }
                      >
                        <Text
                          className={`leading-relaxed ${
                            message.sender === 'user' ? 'text-white' : 'text-slate-800'
                          }`}
                        >
                          {message.content}
                        </Text>
                        <Text
                          className={`mt-1 text-xs ${
                            message.sender === 'user' ? 'text-white/80' : 'text-slate-500'
                          }`}
                        >
                          {message.timestamp.toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </Text>
                      </View>
                    </View>
                  )}

                  {/* Property Cards */}
                  {message.sender === 'ai' && hasProperties && (
                    <View className="mt-2">
                      <Text className="text-sm font-semibold text-slate-700 mb-3">
                        Found {message.properties!.length} propert{message.properties!.length === 1 ? 'y' : 'ies'}
                      </Text>
                      <View className="gap-4">
                        {message.properties!.map((property) => (
                          <TouchableOpacity
                            key={property._id}
                            onPress={() => openPropertyDetails(property)}
                            className="bg-white rounded-2xl overflow-hidden border border-slate-200"
                            style={{
                              shadowColor: '#000',
                              shadowOffset: { width: 0, height: 2 },
                              shadowOpacity: 0.1,
                              shadowRadius: 8,
                              elevation: 3,
                            }}
                          >
                            {/* Property Image */}
                            <View style={{ width: '100%', height: 200, backgroundColor: '#e2e8f0' }}>
                              {property.images && property.images.length > 0 ? (
                                <Image
                                  source={{ uri: getImageUrl(property.images[0]) || '' }}
                                  style={{ width: '100%', height: '100%' }}
                                  contentFit="cover"
                                />
                              ) : (
                                <View className="flex-1 justify-center items-center">
                                  <Ionicons name="home" size={48} color="#94a3b8" />
                                </View>
                              )}
                            </View>

                            {/* Property Details */}
                            <View className="p-4">
                              <Text className="text-lg font-semibold text-slate-900 mb-2" numberOfLines={2}>
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
                              <View className="flex-row items-center gap-1.5 mb-2">
                                <Ionicons name="location" size={14} color="#94a3b8" />
                                <Text className="text-sm text-slate-700" numberOfLines={1}>
                                  {property.area ? `${property.area}, ${property.city}` : property.city}
                                </Text>
                              </View>

                              {/* Property Stats */}
                              <View className="flex-row items-center justify-between bg-slate-50 rounded-lg p-3 mb-3">
                                <Text className="text-xs text-slate-700">{property.bedrooms} bed</Text>
                                <Text className="text-xs text-slate-300">•</Text>
                                <Text className="text-xs text-slate-700">{property.bathrooms} bath</Text>
                                <Text className="text-xs text-slate-300">•</Text>
                                <Text className="text-xs text-slate-700">{property.area_sqft} sqft</Text>
                              </View>

                              {/* Amenity summary */}
                              {property.amenity_summary && (
                                <View className="mb-2">
                                  <Text className="text-[11px] text-slate-600 italic" numberOfLines={2}>
                                    {property.amenity_summary}
                                  </Text>
                                </View>
                              )}

                              {/* Property Type & Score */}
                              <View className="flex-row items-center justify-between">
                                <Text className="text-xs text-slate-500">{property.property_type}</Text>
                                {property.score && (
                                  <View className="bg-teal-100 rounded-full px-2 py-1">
                                    <Text className="text-xs font-medium text-teal-700">
                                      {Math.round(property.score * 100)}% match
                                    </Text>
                                  </View>
                                )}
                              </View>

                              {/* View Details Button */}
                              <TouchableOpacity
                                onPress={() => openPropertyDetails(property)}
                                className="mt-3 bg-[#0a7ea4] rounded-lg py-3 items-center"
                              >
                                <Text className="text-white font-semibold text-sm">View Details</Text>
                              </TouchableOpacity>
                            </View>
                          </TouchableOpacity>
                        ))}
                      </View>
                    </View>
                  )}

                  {/* Builder Cards */}
                  {message.sender === 'ai' && message.builders && message.builders.length > 0 && (
                    <View className="mt-2">
                      <Text className="text-sm font-semibold text-slate-700 mb-3">
                        Found {message.builders.length} builder{message.builders.length === 1 ? '' : 's'}
                      </Text>
                      <View className="gap-4">
                        {message.builders.map((builder) => (
                          <TouchableOpacity
                            key={builder._id}
                            className="bg-white rounded-2xl overflow-hidden border border-slate-200"
                            style={{
                              shadowColor: '#000',
                              shadowOffset: { width: 0, height: 2 },
                              shadowOpacity: 0.1,
                              shadowRadius: 8,
                              elevation: 3,
                            }}
                          >
                            {/* Builder Header */}
                            <View className="h-32 bg-gradient-to-br from-amber-400 to-orange-500 items-center justify-center">
                              <Ionicons name="business" size={40} color="#ffffff" />
                              <Text className="text-white font-semibold text-base mt-2 text-center px-4" numberOfLines={2}>
                                {builder.company_name}
                              </Text>
                            </View>

                            {/* Builder Details */}
                            <View className="p-4">
                              <Text className="text-lg font-semibold text-slate-900 mb-2" numberOfLines={2}>
                                {builder.company_name}
                              </Text>

                              {/* Specialization Tags */}
                              {builder.specialization && builder.specialization.length > 0 && (
                                <View className="flex-row flex-wrap gap-2 mb-3">
                                  {builder.specialization.slice(0, 2).map((spec, index) => (
                                    <View
                                      key={index}
                                      className="bg-amber-100 rounded-full px-3 py-1"
                                    >
                                      <Text className="text-xs font-medium text-amber-700">{spec}</Text>
                                    </View>
                                  ))}
                                </View>
                              )}

                              {/* Experience & Rating */}
                              <View className="flex-row items-center justify-between mb-2">
                                <View className="flex-row items-center gap-1">
                                  <Ionicons name="calendar" size={14} color="#64748b" />
                                  <Text className="text-sm text-slate-600">
                                    {builder.experience_years}y exp
                                  </Text>
                                </View>
                                {builder.rating && (
                                  <View className="flex-row items-center gap-1">
                                    <Ionicons name="star" size={14} color="#fbbf24" />
                                    <Text className="text-sm text-slate-600">{builder.rating}</Text>
                                  </View>
                                )}
                              </View>

                              {/* Location */}
                              {builder.location?.city && (
                                <View className="flex-row items-center gap-1 mb-2">
                                  <Ionicons name="location" size={14} color="#64748b" />
                                  <Text className="text-sm text-slate-600">{builder.location.city}</Text>
                                </View>
                              )}

                              {/* Score */}
                              {builder.score && (
                                <View className="flex-row items-center justify-between mb-3">
                                  <Text className="text-xs text-slate-500">Match</Text>
                                  <View className="bg-amber-100 rounded-full px-3 py-1">
                                    <Text className="text-xs font-medium text-amber-700">
                                      {Math.round(builder.score * 100)}%
                                    </Text>
                                  </View>
                                </View>
                              )}

                              {/* Action Buttons */}
                              <View className="flex-row gap-2 mt-2">
                                <TouchableOpacity
                                  className="flex-1 bg-gradient-to-r from-amber-500 to-orange-600 rounded-lg py-2.5 items-center"
                                >
                                  <Text className="text-white font-semibold text-sm">View Profile</Text>
                                </TouchableOpacity>
                                <TouchableOpacity
                                  className="flex-1 border border-slate-300 rounded-lg py-2.5 items-center"
                                >
                                  <Text className="text-slate-700 font-semibold text-sm">Contact</Text>
                                </TouchableOpacity>
                              </View>
                            </View>
                          </TouchableOpacity>
                        ))}
                      </View>
                    </View>
                  )}

                  {/* Service Cards */}
                  {message.sender === 'ai' && message.services && message.services.length > 0 && (
                    <View className="mt-2">
                      <Text className="text-sm font-semibold text-slate-700 mb-3">
                        Found {message.services.length} service{message.services.length === 1 ? '' : 's'}
                      </Text>
                      <View className="gap-4">
                        {message.services.map((service, idx) => (
                          <TouchableOpacity
                            key={service._id || `service-${idx}`}
                            className="bg-white rounded-2xl overflow-hidden border border-slate-200"
                            style={{
                              shadowColor: '#000',
                              shadowOffset: { width: 0, height: 2 },
                              shadowOpacity: 0.1,
                              shadowRadius: 8,
                              elevation: 3,
                            }}
                          >
                            {/* Service Header */}
                            <View className="p-4 pb-0">
                              <View className="flex-row items-center justify-between mb-2">
                                <View className="bg-amber-100 rounded-full px-3 py-1">
                                  <Text className="text-xs font-medium text-amber-800">
                                    {service.category || 'Service'}
                                  </Text>
                                </View>
                                {typeof service.score === 'number' && (
                                  <View className="bg-teal-50 rounded-full px-3 py-1">
                                    <Text className="text-xs font-medium text-teal-700">
                                      {Math.round(service.score * 100)}% match
                                    </Text>
                                  </View>
                                )}
                              </View>
                            </View>

                            {/* Service Content */}
                            <View className="p-4">
                              <Text className="text-lg font-semibold text-slate-900 mb-2" numberOfLines={2}>
                                {service.service_name || 'Service'}
                              </Text>

                              {service.description && (
                                <Text className="text-sm text-slate-700 mb-3" numberOfLines={3}>
                                  {service.description}
                                </Text>
                              )}

                              {/* Price Range */}
                              {(service.price_range_min || service.price_range_max) && (
                                <View className="flex-row items-center gap-2 mb-3">
                                  <Ionicons name="cash" size={16} color="#0d9488" />
                                  <Text className="text-sm font-semibold text-teal-700">
                                    {service.price_range_min
                                      ? `Rs ${service.price_range_min.toLocaleString()}`
                                      : ''}
                                    {service.price_range_max
                                      ? ` - Rs ${service.price_range_max.toLocaleString()}`
                                      : ''}
                                  </Text>
                                </View>
                              )}

                              {/* Action Buttons */}
                              <View className="flex-row gap-2 mt-2">
                                {service.builder_id ? (
                                  <TouchableOpacity
                                    className="flex-1 bg-gradient-to-r from-amber-500 to-orange-600 rounded-lg py-2.5 items-center"
                                  >
                                    <Text className="text-white font-semibold text-sm">View Builder</Text>
                                  </TouchableOpacity>
                                ) : (
                                  <View className="flex-1" />
                                )}
                                <TouchableOpacity
                                  className="flex-1 border border-slate-300 rounded-lg py-2.5 items-center"
                                >
                                  <Text className="text-slate-700 font-semibold text-sm">Contact</Text>
                                </TouchableOpacity>
                              </View>
                            </View>
                          </TouchableOpacity>
                        ))}
                      </View>
                    </View>
                  )}
                </Animated.View>
              );
            })}

            {/* Loading Indicator */}
            {isLoading && (
              <View className="flex-row justify-start mb-4">
                <View className="bg-white/80 border border-slate-200 rounded-2xl px-4 py-3">
                  <View className="flex-row items-center gap-2">
                    <ActivityIndicator size="small" color="#0a7ea4" />
                    <Text className="text-slate-600">Thinking…</Text>
                  </View>
                </View>
              </View>
            )}
          </ScrollView>

          {/* Input Area */}
          <View
            className="bg-white border-t border-slate-200 px-4 py-3"
            style={{ paddingBottom: insets.bottom + 12 }}
          >
            {/* New Chat Button (when messages exist) */}
            {messages.length > 1 && (
              <TouchableOpacity
                onPress={startNewSession}
                className="flex-row items-center justify-center gap-2 mb-3 py-2 bg-slate-50 rounded-full border border-slate-200"
              >
                <Ionicons name="add-circle-outline" size={18} color="#0a7ea4" />
                <Text className="text-[#0a7ea4] font-semibold text-sm">New Chat</Text>
              </TouchableOpacity>
            )}
            <View className="flex-row items-center gap-3">
              <View className="flex-1 flex-row items-center bg-slate-50 rounded-full border border-slate-200 px-4">
                <TextInput
                  value={inputMessage}
                  onChangeText={setInputMessage}
                  placeholder="Ask about properties..."
                  placeholderTextColor="#94a3b8"
                  className="flex-1 py-3 text-slate-900"
                  multiline
                  maxLength={500}
                  onSubmitEditing={() => sendMessage()}
                  returnKeyType="send"
                />
              </View>
              {isRecording && (
                <TouchableOpacity
                  onPress={() => cancelRecording()}
                  disabled={isLoading}
                  className="w-12 h-12 rounded-full items-center justify-center bg-slate-300"
                >
                  <Ionicons name="close" size={20} color="#0f172a" />
                </TouchableOpacity>
              )}
              <TouchableOpacity
                onPress={isRecording ? () => stopRecording() : () => startRecording()}
                disabled={isLoading}
                className={`w-12 h-12 rounded-full items-center justify-center ${
                  isRecording ? 'bg-emerald-600' : 'bg-slate-200'
                }`}
              >
                <Ionicons
                  name={isRecording ? 'checkmark' : 'mic'}
                  size={20}
                  color={isRecording ? '#ffffff' : '#0f172a'}
                />
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => sendMessage()}
                disabled={!inputMessage.trim() || isLoading}
                className={`w-12 h-12 rounded-full items-center justify-center ${
                  inputMessage.trim() && !isLoading
                    ? 'bg-[#0a7ea4]'
                    : 'bg-slate-300'
                }`}
              >
                <Ionicons
                  name="send"
                  size={20}
                  color={inputMessage.trim() && !isLoading ? '#ffffff' : '#94a3b8'}
                />
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}

