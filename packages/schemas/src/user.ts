import { z } from 'zod'

/**
 * User Role Enum
 */
export const UserRoleSchema = z.enum(['buyer', 'seller', 'builder', 'admin'])
export type UserRole = z.infer<typeof UserRoleSchema>

/**
 * User Schema
 */
export const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  name: z.string(),
  role: UserRoleSchema,
  phone: z.string().optional(),
  createdAt: z.date(),
  updatedAt: z.date(),
})

export type User = z.infer<typeof UserSchema>

/**
 * Create User Schema (for registration)
 */
export const CreateUserSchema = UserSchema.omit({
  id: true,
  createdAt: true,
  updatedAt: true,
})

export type CreateUser = z.infer<typeof CreateUserSchema>

