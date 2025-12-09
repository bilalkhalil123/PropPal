/**
 * User API service for frontend
 */
import { UserResponse } from '@/lib/types/user'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL

if (!API_BASE_URL) {
  throw new Error('NEXT_PUBLIC_API_URL environment variable is not set')
}

export interface UserStats {
  total_users: number
  buyers: number
  sellers: number
  builders: number
  admins: number
}

export interface UpdateUserData {
  name?: string
  phone?: string
  role?: 'buyer' | 'seller' | 'builder' | 'admin'
}

export class UserService {
  private static async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  }

  /**
   * Get current user by Clerk ID
   */
  static async getCurrentUser(clerkId: string): Promise<UserResponse> {
    return this.makeRequest<UserResponse>(`/api/users/me?clerk_id=${clerkId}`)
  }

  /**
   * Update current user profile
   */
  static async updateCurrentUser(
    clerkId: string,
    data: UpdateUserData
  ): Promise<UserResponse> {
    const params = new URLSearchParams({ clerk_id: clerkId })
    
    if (data.name) params.append('name', data.name)
    if (data.phone) params.append('phone', data.phone)
    if (data.role) params.append('role', data.role)

    return this.makeRequest<UserResponse>(`/api/users/me?${params.toString()}`, {
      method: 'PUT',
    })
  }

  /**
   * Get user by ID
   */
  static async getUserById(userId: string): Promise<UserResponse> {
    return this.makeRequest<UserResponse>(`/api/users/${userId}`)
  }

  /**
   * Get all users with optional filtering
   */
  static async getUsers(options: {
    role?: string
    skip?: number
    limit?: number
  } = {}): Promise<UserResponse[]> {
    const params = new URLSearchParams()
    
    if (options.role) params.append('role', options.role)
    if (options.skip) params.append('skip', options.skip.toString())
    if (options.limit) params.append('limit', options.limit.toString())

    const queryString = params.toString()
    return this.makeRequest<UserResponse[]>(`/api/users${queryString ? `?${queryString}` : ''}`)
  }

  /**
   * Get user statistics
   */
  static async getUserStats(): Promise<{ message: string; stats: UserStats }> {
    return this.makeRequest<{ message: string; stats: UserStats }>('/api/users/stats')
  }

  /**
   * Sync user from Clerk (manual sync)
   */
  static async syncUserFromClerk(clerkId: string): Promise<{
    message: string
    clerk_id: string
    user_id?: string
    suggestion?: string
  }> {
    return this.makeRequest(`/api/users/sync/${clerkId}`, {
      method: 'POST',
    })
  }
}

export default UserService
