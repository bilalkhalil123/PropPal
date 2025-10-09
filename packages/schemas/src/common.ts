import { z } from 'zod'

/**
 * Common API Response Schema
 */
export const ApiResponseSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  data: z.unknown().optional(),
  error: z.string().optional(),
})

export type ApiResponse<T = unknown> = {
  success: boolean
  message?: string
  data?: T
  error?: string
}

/**
 * Pagination Schema
 */
export const PaginationSchema = z.object({
  page: z.number().int().positive().default(1),
  limit: z.number().int().positive().max(100).default(10),
  total: z.number().int().nonnegative().optional(),
})

export type Pagination = z.infer<typeof PaginationSchema>

