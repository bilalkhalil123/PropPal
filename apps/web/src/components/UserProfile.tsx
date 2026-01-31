'use client'

import { useState, useEffect, useCallback } from 'react'
import { useUser } from '@clerk/nextjs'
import { UserService } from '@/lib/services/user-service'
import { UserResponse, UpdateUserData } from '@/lib/types/user'
import { motion } from 'framer-motion'

export default function UserProfile() {
  const { user: clerkUser, isLoaded } = useUser()
  const [user, setUser] = useState<UserResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState<UpdateUserData>({})

  const loadUser = useCallback(async () => {
    if (!clerkUser?.id) return

    try {
      setLoading(true)
      setError(null)
      const userData = await UserService.getCurrentUser(clerkUser.id)
      setUser(userData)
      setFormData({
        name: userData.name,
        phone: userData.phone || '',
        role: userData.role,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load user')
    } finally {
      setLoading(false)
    }
  }, [clerkUser?.id])

  useEffect(() => {
    if (isLoaded && clerkUser) {
      loadUser()
    }
  }, [isLoaded, clerkUser, loadUser])

  const handleUpdate = async () => {
    if (!clerkUser?.id) return

    try {
      setUpdating(true)
      setError(null)
      const updatedUser = await UserService.updateCurrentUser(clerkUser.id, formData)
      setUser(updatedUser)
      setEditMode(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user')
    } finally {
      setUpdating(false)
    }
  }

  const handleCancel = () => {
    if (user) {
      setFormData({
        name: user.name,
        phone: user.phone || '',
        role: user.role,
      })
    }
    setEditMode(false)
    setError(null)
  }

  // --- UI STATES ---
  if (!isLoaded || loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[color:var(--color-accent-gold)]"></div>
      </div>
    )
  }

  if (!clerkUser) {
    return (
      <div className="text-center py-28">
        <p className="text-slate-600" style={{ fontFamily: 'var(--font-sans)' }}>
          Please sign in to view your profile.
        </p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto mt-20 bg-red-50 border border-red-200 rounded-2xl shadow-card p-6 text-center">
        <h3 className="text-base font-semibold text-red-700 mb-2">Error</h3>
        <p className="text-sm text-red-600 mb-4">{error}</p>
        <button
          onClick={loadUser}
          className="px-4 py-2 text-sm font-medium text-white bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))] rounded-xl hover:ring-2 hover:ring-[color:var(--color-accent-gold)] active:scale-95 transition-all"
        >
          Try Again
        </button>
      </div>
    )
  }

  // --- MAIN UI ---
  return (
    <div
      className="min-h-screen py-28 px-6 md:px-12 lg:px-24 bg-[linear-gradient(to_bottom,#f9f9f9,#edece8)]"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="max-w-3xl mx-auto bg-white/70 backdrop-blur-xl border border-slate-200/60 shadow-elevated rounded-2xl p-8"
      >
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2
              className="text-3xl font-bold tracking-tight text-slate-900"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              My Profile
            </h2>
            <p className="text-sm text-slate-600" style={{ fontFamily: 'var(--font-sans)' }}>
              Manage your personal details and account preferences.
            </p>
          </div>

          {!editMode && (
            <button
              onClick={() => setEditMode(true)}
              className="px-5 py-2.5 rounded-2xl bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))] text-white text-sm font-medium hover:ring-2 hover:ring-[color:var(--color-accent-gold)] active:scale-95 transition-all"
            >
              Edit
            </button>
          )}
        </div>

        {/* User Card */}
        {user && (
          <div className="space-y-8">
            {/* Avatar */}
            <div className="flex items-center gap-6">
              <div className="h-24 w-24 rounded-full bg-gradient-to-br from-[color:var(--color-primary)] to-[color:var(--color-accent-gold)] p-[2px]">
                <div className="h-full w-full rounded-full bg-white flex items-center justify-center overflow-hidden">
                  {user.profile_image ? (
                    <>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={user.profile_image}
                        alt={user.name}
                        className="h-full w-full object-cover rounded-full"
                      />
                    </>
                  ) : (
                    <span className="text-3xl font-semibold text-slate-500">
                      {user.name.charAt(0).toUpperCase()}
                    </span>
                  )}
                </div>
              </div>

              <div>
                <h3 className="text-xl font-semibold text-slate-900">{user.name}</h3>
                <p className="text-sm text-slate-600">{user.email}</p>
                <span
                  className={`inline-flex mt-2 px-2.5 py-1 text-xs font-semibold rounded-full ${
                    user.role === 'admin'
                      ? 'bg-purple-100 text-purple-800'
                      : user.role === 'builder'
                      ? 'bg-blue-100 text-blue-800'
                      : user.role === 'seller'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                </span>
              </div>
            </div>

            {/* Form Fields */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Name */}
              <div>
                <label className="text-sm font-medium text-slate-700">Name</label>
                {editMode ? (
                  <input
                    type="text"
                    value={formData.name || ''}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="mt-1 block w-full rounded-xl border-slate-300 focus:ring-2 focus:ring-[color:var(--color-accent-gold)] text-slate-800"
                  />
                ) : (
                  <p className="mt-1 text-slate-900">{user.name}</p>
                )}
              </div>

              {/* Email */}
              <div>
                <label className="text-sm font-medium text-slate-700">Email</label>
                <p className="mt-1 text-slate-900">{user.email}</p>
                <p className="text-xs text-slate-500">
                  Email is managed by Clerk and cannot be changed here.
                </p>
              </div>

              {/* Phone */}
              <div>
                <label className="text-sm font-medium text-slate-700">Phone</label>
                {editMode ? (
                  <input
                    type="tel"
                    value={formData.phone || ''}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="mt-1 block w-full rounded-xl border-slate-300 focus:ring-2 focus:ring-[color:var(--color-accent-gold)] text-slate-800"
                  />
                ) : (
                  <p className="mt-1 text-slate-900">{user.phone || 'Not provided'}</p>
                )}
              </div>

              {/* Role */}
              <div>
                <label className="text-sm font-medium text-slate-700">Role</label>
                {editMode ? (
                  <select
                    value={formData.role || 'buyer'}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value as UserResponse['role'] })}
                    className="mt-1 block w-full rounded-xl border-slate-300 focus:ring-2 focus:ring-[color:var(--color-accent-gold)] text-slate-800"
                  >
                    <option value="buyer">Buyer</option>
                    <option value="seller">Seller</option>
                    <option value="builder">Builder</option>
                    <option value="admin">Admin</option>
                  </select>
                ) : (
                  <p className="mt-1 text-slate-900 capitalize">{user.role}</p>
                )}
              </div>
            </div>

            {/* Account Info */}
            <div className="pt-6 border-t border-slate-200">
              <h4 className="text-sm font-semibold text-slate-800 mb-4">Account Details</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="text-sm font-medium text-slate-700">Clerk ID</label>
                  <p className="mt-1 text-slate-900 font-mono text-sm">{user.clerk_id}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700">Member Since</label>
                  <p className="mt-1 text-slate-900 text-sm">
                    {new Date(user.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </div>

            {/* Buttons */}
            {editMode && (
              <div className="flex justify-end gap-3 pt-6 border-t border-slate-200">
                <button
                  onClick={handleCancel}
                  className="px-4 py-2 rounded-xl border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpdate}
                  disabled={updating}
                  className="px-5 py-2.5 rounded-2xl bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))] text-white text-sm font-medium hover:ring-2 hover:ring-[color:var(--color-accent-gold)] active:scale-95 transition-all disabled:opacity-50"
                >
                  {updating ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            )}
          </div>
        )}
      </motion.div>
    </div>
  )
}
