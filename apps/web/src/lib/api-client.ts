const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL

if (!API_BASE_URL) {
  throw new Error('NEXT_PUBLIC_API_URL environment variable is not set')
}

/**
 * Centralized API client for making authenticated requests to the backend
 * Works with Clerk authentication - tokens are automatically handled
 */
class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  /**
   * Make a request to the backend API
   * Clerk automatically adds the Authorization header via middleware
   */
  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    let response: Response
    try {
      // Clerk middleware automatically adds the Authorization header
      response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include', // Include cookies if needed
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`)
      }
    } catch (error: any) {
      // Enhanced error logging for debugging
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        console.error(`[API Client] Network error - Could not reach ${url}`)
        console.error('This usually means:', {
          'Backend server not running': 'Check if the backend is running on the expected port',
          'CORS issue': 'Check backend CORS settings',
          'Wrong URL': `Current API URL: ${this.baseUrl}`,
        })
      }
      throw error
    }

    // Handle empty responses
    const text = await response.text()
    if (!text) {
      return {} as T
    }

    return JSON.parse(text)
  }

  /**
   * GET request
   */
  async get<T>(endpoint: string, options?: RequestInit): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: 'GET',
      ...options,
    })
  }

  /**
   * POST request
   */
  async post<T>(endpoint: string, data?: any, options?: RequestInit): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    })
  }

  /**
   * PUT request
   */
  async put<T>(endpoint: string, data?: any, options?: RequestInit): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    })
  }

  /**
   * PATCH request
   */
  async patch<T>(endpoint: string, data?: any, options?: RequestInit): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    })
  }

  /**
   * DELETE request
   */
  async delete<T>(endpoint: string, options?: RequestInit): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: 'DELETE',
      ...options,
    })
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL)

// Export convenience methods
export const api = {
  /**
   * User endpoints
   */
  users: {
    getCurrent: (clerkId: string) => apiClient.get(`/api/users/me?clerk_id=${clerkId}`),
    sync: (data: any) => apiClient.post('/api/users/sync', data),
  },

  /**
   * Builder endpoints
   */
  builders: {
    getProfile: (clerkId: string, options?: RequestInit) => 
      apiClient.get(`/api/builder/profile/${clerkId}`, options),
    getMyProfile: (options?: RequestInit) => 
      apiClient.get('/api/builder/profile/me/', options),
    getServices: (clerkId: string, options?: RequestInit) => 
      apiClient.get(`/api/builder/services/${clerkId}`, options),
    getMyServices: (options?: RequestInit) => 
      apiClient.get('/api/builder/services/me/', options),
    getById: (id: string, options?: RequestInit) => 
      apiClient.get(`/api/builder/profiles/id/${id}`, options),
    searchProfiles: (query: string, filters?: any, options?: RequestInit) => 
      apiClient.post('/api/builder/profiles/search', { query, ...filters }, options),
    searchServices: (query: string, filters?: any, options?: RequestInit) => 
      apiClient.post('/api/builder/services/search', { query, ...filters }, options),
  },

  /**
   * Chat endpoints
   */
  chat: {
    sendMessage: (message: string, userId?: string, sessionId?: string, clerkId?: string) =>
      apiClient.post('/api/chat/message', { message, user_id: userId, session_id: sessionId, clerk_id: clerkId }),
    health: () => apiClient.get('/api/chat/health'),
    capabilities: () => apiClient.get('/api/chat/capabilities'),
    history: (userId: string, sessionId?: string, limit: number = 50) =>
      apiClient.get(`/api/chat/history?user_id=${encodeURIComponent(userId)}${sessionId ? `&session_id=${encodeURIComponent(sessionId)}` : ''}&limit=${limit}`),
    messages: (userId: string, sessionId?: string, beforeMs?: number, limit: number = 50) =>
      apiClient.get(`/api/chat/history/messages?user_id=${encodeURIComponent(userId)}${sessionId ? `&session_id=${encodeURIComponent(sessionId)}` : ''}${beforeMs ? `&before_ms=${beforeMs}` : ''}&limit=${limit}`),
    sessions: (userId: string) =>
      apiClient.get(`/api/chat/sessions?user_id=${encodeURIComponent(userId)}`),
  },

  /**
   * Search endpoints
   */
  search: {
    properties: (query: string, filters?: any) =>
      apiClient.post('/api/search/properties', { query, ...filters }),
  },

  /**
   * Properties endpoints
   */
  properties: {
    getById: (id: string) => apiClient.get(`/api/properties/${id}`),
  },

  /**
   * Recommendations endpoints
   */
  recommendations: {
    properties: (userId: string, limit: number = 12) =>
      apiClient.get(`/api/recommendations/properties?user_id=${encodeURIComponent(userId)}&limit=${limit}`),
  },
}

// Default export
export default apiClient
