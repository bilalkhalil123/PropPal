import { useUser } from '@/context/UserContext'
import { UserResponse } from '@/lib/types/user'

/**
 * Custom hook to access the current authenticated user
 * 
 * @returns {Object} - User data, loading state, error state, and helper functions
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { user, loading, error, refreshUser, isAuthenticated } = useCurrentUser()
 * 
 *   if (loading) return <div>Loading...</div>
 *   if (error) return <div>Error: {error}</div>
 *   if (!isAuthenticated) return <div>Please sign in</div>
 * 
 *   return <div>Welcome, {user.name}!</div>
 * }
 * ```
 */
export function useCurrentUser() {
  const context = useUser()
  
  return {
    // User data from your database
    user: context.user as UserResponse | null,
    
    // Loading state
    loading: context.loading,
    
    // Error state
    error: context.error,
    
    // Helper to manually refresh user data
    refreshUser: context.refreshUser,
    
    // Whether user is authenticated
    isAuthenticated: context.isAuthenticated,
    
    // Clerk ID for reference
    clerkId: context.clerkId,
    
    // Convenience helper to get user ID
    userId: context.user?.id || (context.user as any)?._id,
    
    // Convenience helper to get user role
    userRole: context.user?.role,
    
    // Guest status
    isGuest: context.isGuest,
  }
}

/**
 * Hook for accessing only the user data (no loading/error states)
 * Use this when you're sure user is loaded
 */
export function useCurrentUserData() {
  const { user } = useCurrentUser()
  return user
}

/**
 * Hook for checking authentication status only
 * Lightweight check without fetching user data
 */
export function useAuthStatus() {
  const { isAuthenticated, loading, clerkId } = useCurrentUser()
  return {
    isAuthenticated,
    isLoading: loading,
    clerkId,
  }
}

