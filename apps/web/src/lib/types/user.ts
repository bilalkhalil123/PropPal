/**
 * User types for frontend
 */
export interface UserResponse {
  id: string
  name: string
  email: string
  phone?: string
  role: 'buyer' | 'seller' | 'builder' | 'admin'
  profile_image?: string
  clerk_id?: string
  created_at: string
  updated_at: string
}

export interface UserCreate {
  name: string
  email: string
  phone?: string
  role: 'buyer' | 'seller' | 'builder' | 'admin'
  password: string
}

export interface UserUpdate {
  name?: string
  phone?: string
  role?: 'buyer' | 'seller' | 'builder' | 'admin'
  profile_image?: string
}

export interface UserStats {
  total_users: number
  buyers: number
  sellers: number
  builders: number
  admins: number
}
