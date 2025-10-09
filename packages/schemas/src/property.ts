import { z } from 'zod'

/**
 * Property Type Enum
 */
export const PropertyTypeSchema = z.enum([
  'house',
  'apartment',
  'condo',
  'plot',
  'commercial',
  'farmhouse',
])
export type PropertyType = z.infer<typeof PropertyTypeSchema>

/**
 * Property Status Enum
 */
export const PropertyStatusSchema = z.enum([
  'available',
  'pending',
  'sold',
  'rented',
])
export type PropertyStatus = z.infer<typeof PropertyStatusSchema>

/**
 * Location Schema
 */
export const LocationSchema = z.object({
  address: z.string(),
  city: z.string(),
  area: z.string(),
  zipCode: z.string().optional(),
  coordinates: z
    .object({
      lat: z.number(),
      lng: z.number(),
    })
    .optional(),
})

export type Location = z.infer<typeof LocationSchema>

/**
 * Property Features Schema
 */
export const PropertyFeaturesSchema = z.object({
  bedrooms: z.number().int().nonnegative(),
  bathrooms: z.number().nonnegative(),
  area: z.number().positive(), // in square feet or marla
  areaUnit: z.enum(['sqft', 'sqm', 'marla', 'kanal']).default('sqft'),
  yearBuilt: z.number().int().positive().optional(),
  parking: z.number().int().nonnegative().optional(),
  floor: z.number().int().optional(),
})

export type PropertyFeatures = z.infer<typeof PropertyFeaturesSchema>

/**
 * Property Schema
 */
export const PropertySchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  price: z.number().positive(),
  location: LocationSchema,
  type: PropertyTypeSchema,
  status: PropertyStatusSchema,
  features: PropertyFeaturesSchema,
  images: z.array(z.string().url()).default([]),
  sellerId: z.string(),
  createdAt: z.date(),
  updatedAt: z.date(),
})

export type Property = z.infer<typeof PropertySchema>

/**
 * Create Property Schema
 */
export const CreatePropertySchema = PropertySchema.omit({
  id: true,
  createdAt: true,
  updatedAt: true,
})

export type CreateProperty = z.infer<typeof CreatePropertySchema>

