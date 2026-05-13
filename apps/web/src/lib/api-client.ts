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
  private getToken?: () => Promise<string | null>

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  setGetToken(getTokenFn: () => Promise<string | null>) {
    this.getToken = getTokenFn
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

    if (this.getToken) {
      try {
        const token = await this.getToken()
        if (token) {
          (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
        }
      } catch (e) {
        console.error('Failed to get auth token', e)
      }
    } else if (typeof window !== 'undefined' && (window as any).Clerk?.session) {
       try {
         const token = await (window as any).Clerk.session.getToken()
         if (token) {
           (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
         }
       } catch (e) {
         console.error('Failed to get Clerk token from window', e)
       }
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
    } catch (error: unknown) {
      // Enhanced error logging for debugging
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
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
  async post<T>(endpoint: string, data?: Record<string, unknown>, options?: RequestInit): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    })
  }

  /**
   * PUT request
   */
  async put<T>(endpoint: string, data?: Record<string, unknown>, options?: RequestInit): Promise<T> {
    return this.makeRequest<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    })
  }

  /**
   * PATCH request
   */
  async patch<T>(endpoint: string, data?: Record<string, unknown>, options?: RequestInit): Promise<T> {
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

/** Visit row from GET /api/visits/* */
export type VisitApiRow = {
  id: string
  _id?: string
  buyer_id?: string
  property_id?: string | null
  seller_id?: string | null
  confirmed_time?: string | null
  status?: string
  property_title?: string
  buyer_name?: string
  agent_notes?: string | null
}

// Export convenience methods
export const api = {
  /**
   * User endpoints
   */
  users: {
    getCurrent: (clerkId: string) => apiClient.get(`/api/users/me?clerk_id=${clerkId}`),
    sync: (data: Record<string, unknown>) => apiClient.post('/api/users/sync', data),
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
    getServicesByBuilderId: (builderId: string, options?: RequestInit) =>
      apiClient.get(`/api/builder/services/builder/${builderId}`, options),
    getMyServices: (options?: RequestInit) => 
      apiClient.get('/api/builder/services/me/', options),
    getById: (id: string, options?: RequestInit) => 
      apiClient.get(`/api/builder/profiles/id/${id}`, options),
    searchProfiles: (query: string, filters?: Record<string, unknown>, options?: RequestInit) => 
      apiClient.post('/api/builder/profiles/search', { query, ...filters }, options),
    searchServices: (query: string, filters?: Record<string, unknown>, options?: RequestInit) => 
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
    deleteSession: (userId: string, sessionId: string) =>
      apiClient.delete(`/api/chat/sessions/${encodeURIComponent(sessionId)}?user_id=${encodeURIComponent(userId)}`),
    booking: (
      body: {
        message: string
        property_id: string
        conversation_history: Array<{ role: string; content: string }>
      },
      options?: RequestInit
    ) => apiClient.post<{
      success: boolean
      agent_response: string
      updated_history: Array<{ role: string; content: string }>
      visit_object?: Record<string, unknown> | null
      metadata?: Record<string, unknown>
      error?: string | null
    }>('/api/chat/booking', body, options),
  },

  /**
   * Search endpoints
   */
  search: {
    properties: (query: string, filters?: Record<string, unknown>) =>
      apiClient.post('/api/search/properties', { query, ...filters }),
  },

  /**
   * Properties endpoints
   */
  properties: {
    getById: (id: string) => apiClient.get(`/api/properties/${id}`),
    contactSeller: (propertyId: string, message?: string, options?: RequestInit) =>
      apiClient.post(`/api/properties/${propertyId}/contact-seller`, { message }, options),
    favorite: (propertyId: string, options?: RequestInit) =>
      apiClient.post(`/api/properties/${propertyId}/favorite`, undefined, options),
    unfavorite: (propertyId: string, options?: RequestInit) =>
      apiClient.delete(`/api/properties/${propertyId}/favorite`, options),
    getFavorites: (options?: RequestInit) =>
      apiClient.get('/api/properties/user/favorites', options),
  },

  /**
   * Recommendations endpoints
   */
  recommendations: {
    properties: (userId: string, limit: number = 12) =>
      apiClient.get(`/api/recommendations/properties?user_id=${encodeURIComponent(userId)}&limit=${limit}`),
  },

  /**
   * Property visits (booking)
   */
  visits: {
    myUpcoming: (options?: RequestInit) =>
      apiClient.get<{ visits: VisitApiRow[] }>('/api/visits/me/upcoming', options),
    sellerUpcoming: (options?: RequestInit) =>
      apiClient.get<{ visits: VisitApiRow[] }>('/api/visits/seller/upcoming', options),
  },

  /**
   * Projects & bidding endpoints
   */
  projects: {
    open: (excludeUserId?: string) => {
      const ts = new Date().getTime()
      const url = excludeUserId 
        ? `/api/projects/open?exclude_user_id=${encodeURIComponent(excludeUserId)}&_t=${ts}` 
        : `/api/projects/open?_t=${ts}`
      return apiClient.get<{ projects: any[] }>(url)
    },
    mine: () => apiClient.get<{ projects: any[] }>('/api/projects/me'),
    create: (data: Record<string, unknown>, options?: RequestInit) =>
      apiClient.post<any>('/api/projects', data, options),
    getById: (id: string) => apiClient.get<any>(`/api/projects/${id}`),
    delete: (id: string) => apiClient.delete<{ deleted: boolean }>(`/api/projects/${id}`),
    listBids: (projectId: string) => apiClient.get<{ bids: any[] }>(`/api/projects/${projectId}/bids`),
    createBid: (projectId: string, data: Record<string, unknown>, options?: RequestInit) =>
      apiClient.post<any>(`/api/projects/${projectId}/bids`, { ...data, project_id: projectId }, options),
    myBids: () => apiClient.get<{ bids: any[] }>('/api/projects/bids/me'),
    updateBid: (bidId: string, data: Record<string, unknown>, options?: RequestInit) =>
      apiClient.patch<any>(`/api/projects/bids/${bidId}`, data, options),
    deleteBid: (bidId: string) =>
      apiClient.delete<{ deleted: boolean }>(`/api/projects/bids/${bidId}`),
  },

  /**
   * Conversations endpoints
   */
  conversations: {
    list: (clerkId: string) => apiClient.get<{ conversations: any[] }>(`/api/conversations?clerk_id=${encodeURIComponent(clerkId)}`),
    start: (clerkId: string, data: Record<string, unknown>) =>
      apiClient.post<{ conversation: any }>(`/api/conversations?clerk_id=${encodeURIComponent(clerkId)}`, data),
    messages: (clerkId: string, conversationId: string) =>
      apiClient.get<{ messages: any[] }>(`/api/conversations/${conversationId}/messages?clerk_id=${encodeURIComponent(clerkId)}`),
    sendMessage: (clerkId: string, conversationId: string, data: Record<string, unknown>) =>
      apiClient.post<{ message: any }>(`/api/conversations/${conversationId}/messages?clerk_id=${encodeURIComponent(clerkId)}`, data),
  },
}

// Default export
export default apiClient
