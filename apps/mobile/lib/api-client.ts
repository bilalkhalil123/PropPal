/**
 * API Client for PropPal Mobile App
 * 
 * Handles all API requests to the FastAPI backend.
 * Uses environment variables for configuration.
 */

import Constants from 'expo-constants';

// Get API URL from environment variables or use default
const API_BASE_URL = Constants.expoConfig?.extra?.apiUrl || 
                     process.env.EXPO_PUBLIC_API_URL || 
                     'http://localhost:8000';

if (!API_BASE_URL) {
  console.warn('API_BASE_URL is not set. Using default: http://localhost:8000');
}

/**
 * Centralized API client for making requests to the backend
 */
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    // Remove trailing slash
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  /**
   * Make a request to the backend API
   */
  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        
        try {
          const errorJson = JSON.parse(errorText);
          errorMessage = errorJson.detail || errorJson.message || errorMessage;
        } catch {
          errorMessage = errorText || errorMessage;
        }

        throw new Error(errorMessage);
      }

      // Handle empty responses
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return {} as T;
    } catch (error) {
      if (error instanceof Error) {
        // Network errors
        if (error.message.includes('Network request failed') || 
            error.message.includes('Failed to fetch')) {
          throw new Error(
            `Cannot connect to backend at ${this.baseUrl}. ` +
            `Make sure the server is running and your device is on the same network.`
          );
        }
        throw error;
      }
      throw new Error('An unknown error occurred');
    }
  }

  // GET request
  async get<T>(endpoint: string): Promise<T> {
    return this.makeRequest<T>(endpoint, { method: 'GET' });
  }

  // POST request
  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // PUT request
  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // DELETE request
  async delete<T>(endpoint: string): Promise<T> {
    return this.makeRequest<T>(endpoint, { method: 'DELETE' });
  }

  // Health check
  async healthCheck() {
    return this.get<{ status: string; service: string; version: string }>('/');
  }

  // Properties API
  properties = {
    getAll: () => this.get<any[]>('/api/properties'),
    getById: (id: string) => this.get<any>(`/api/properties/${id}`),
  };

  // Recommendations API
  recommendations = {
    properties: (userId?: string, limit: number = 12) => {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);
      params.append('limit', limit.toString());
      return this.get<any[]>(`/api/recommendations/properties?${params.toString()}`);
    },
  };

  // Chat API
  chat = {
    sendMessage: (data: {
      user_id: string;
      message: string;
      session_id?: string;
    }) => this.post<any>('/api/chat/message', data),
    
    getHistory: (userId: string, sessionId?: string, limit: number = 50) => {
      const params = new URLSearchParams();
      params.append('user_id', userId);
      if (sessionId) params.append('session_id', sessionId);
      params.append('limit', limit.toString());
      return this.get<any[]>(`/api/chat/history?${params.toString()}`);
    },

    listSessions: (userId: string) => {
      return this.get<any[]>(`/api/chat/sessions?user_id=${userId}`);
    },
  };

  // Search API
  search = {
    properties: (query: string, filters?: any) => {
      return this.post<any[]>('/api/search/properties', {
        query,
        filters,
      });
    },
  };
}

// Export singleton instance
export const api = new ApiClient(API_BASE_URL);

// Export the base URL for debugging
export const API_URL = API_BASE_URL;

