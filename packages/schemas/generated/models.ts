/**
 * AUTO-GENERATED TypeScript interfaces from Pydantic models
 * DO NOT EDIT MANUALLY - Changes will be overwritten
 * Generated on: 2026-04-03T02:22:06.109703
 */

export interface UserResponse {
  name: string;
  email: string;
  phone?: string | null;
  /** User role: buyer, seller, builder, admin */
  role: string;
  profile_image?: string | null;
  /** Clerk user ID for authentication */
  clerk_id?: string | null;
  _id: string;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  name: string;
  email: string;
  phone?: string | null;
  /** User role: buyer, seller, builder, admin */
  role: string;
  profile_image?: string | null;
  /** Clerk user ID for authentication */
  clerk_id?: string | null;
  password: string;
}

export interface PropertyResponse {
  title: string;
  description: string;
  price: number;
  /** house, apartment, plot, commercial, etc. */
  property_type: string;
  area_sqft: number;
  bedrooms: number;
  bathrooms: number;
  floors?: number;
  city: string;
  area: string;
  /** Longitude */
  lng?: number | null;
  /** Latitude */
  lat?: number | null;
  _id: string;
  seller_id: string;
  images?: string[];
  metadata?: Record<string, any>;
  external_id?: string | null;
  source?: string | null;
  source_url?: string | null;
  date_added?: string | null;
  last_indexed_at?: string | null;
  /** Raw nearby amenities JSON from Overpass API */
  nearby_amenities?: Record<string, any>;
  /** Groq-generated human-readable amenity summary */
  amenity_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PropertyCreate {
  title: string;
  description: string;
  price: number;
  /** house, apartment, plot, commercial, etc. */
  property_type: string;
  area_sqft: number;
  bedrooms: number;
  bathrooms: number;
  floors?: number;
  city: string;
  area: string;
  /** Longitude */
  lng?: number | null;
  /** Latitude */
  lat?: number | null;
  seller_id: string;
  /** Array of image URLs */
  images?: string[];
  /** Additional metadata */
  metadata?: Record<string, any>;
  external_id?: string | null;
  source?: string | null;
  source_url?: string | null;
  date_added?: string | null;
}

export interface PropertyAmenityResponse {
  name: string;
  /** school, hospital, park, etc. */
  type: string;
  rating?: number | null;
  distance_meters: number;
  duration_minutes?: number | null;
  location_name: string;
  lat: number;
  lng: number;
  external_id?: string | null;
  _id: string;
  property_id: string;
  fetched_at: string;
}

export interface PropertyAmenityCreate {
  name: string;
  /** school, hospital, park, etc. */
  type: string;
  rating?: number | null;
  distance_meters: number;
  duration_minutes?: number | null;
  location_name: string;
  lat: number;
  lng: number;
  external_id?: string | null;
  property_id: string;
}

export interface BuilderProfileResponse {
  company_name: string;
  /** List of specializations: construction, renovation, interior, etc. */
  specialization?: string[];
  experience_years: number;
  /** List of portfolio image URLs */
  portfolio_images?: string[];
  rating?: number | null;
  about?: string | null;
  founded_year?: number | null;
  location?: any | null;
  _id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface BuilderProfileCreate {
  company_name: string;
  /** List of specializations: construction, renovation, interior, etc. */
  specialization?: string[];
  experience_years: number;
  /** List of portfolio image URLs */
  portfolio_images?: string[];
  rating?: number | null;
  about?: string | null;
  founded_year?: number | null;
  location?: any | null;
}

export interface BuilderServiceResponse {
  title: string;
  description: string;
  /** renovation, architecture, construction, etc. */
  category: string;
  base_price: number;
  /** per sqft, fixed, per hour, etc. */
  price_unit: string;
  estimated_duration?: string | null;
  /** List of features: 3D design, material sourcing, etc. */
  service_features?: string[];
  /** List of image URLs for the service */
  service_images?: string[];
  _id: string;
  builder_id: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface BuilderServiceCreate {
  title: string;
  description: string;
  /** renovation, architecture, construction, etc. */
  category: string;
  base_price: number;
  /** per sqft, fixed, per hour, etc. */
  price_unit: string;
  estimated_duration?: string | null;
  /** List of features: 3D design, material sourcing, etc. */
  service_features?: string[];
  /** List of image URLs for the service */
  service_images?: string[];
}

export interface UserProjectResponse {
  title: string;
  description: string;
  /** construction, renovation, etc. */
  project_type: string;
  budget_min: number;
  budget_max: number;
  location: string;
  /** open, in_discussion, closed */
  status?: string;
  _id: string;
  user_id: string;
  property_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserProjectCreate {
  title: string;
  description: string;
  /** construction, renovation, etc. */
  project_type: string;
  budget_min: number;
  budget_max: number;
  location: string;
  /** open, in_discussion, closed */
  status?: string;
  property_id?: string | null;
}

export interface BuilderBidResponse {
  proposal_title: string;
  proposal_details: string;
  estimated_cost: number;
  estimated_duration: string;
  /** Array of URLs (designs, PDFs, etc.) */
  attachments?: string[];
  /** pending, shortlisted, rejected, accepted */
  status?: string;
  _id: string;
  project_id: string;
  builder_id: string;
  created_at: string;
  updated_at: string;
}

export interface BuilderBidCreate {
  proposal_title: string;
  proposal_details: string;
  estimated_cost: number;
  estimated_duration: string;
  /** Array of URLs (designs, PDFs, etc.) */
  attachments?: string[];
  /** pending, shortlisted, rejected, accepted */
  status?: string;
  project_id: string;
}

export interface VisitResponse {
  /** Array of ISO timestamp strings */
  proposed_time_slots?: string[];
  confirmed_time?: string | null;
  /** pending, confirmed, cancelled, completed */
  status?: string;
  agent_notes?: string | null;
  _id: string;
  buyer_id: string;
  property_id?: string | null;
  builder_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface VisitCreate {
  /** Array of ISO timestamp strings */
  proposed_time_slots?: string[];
  confirmed_time?: string | null;
  /** pending, confirmed, cancelled, completed */
  status?: string;
  agent_notes?: string | null;
  property_id?: string | null;
  builder_id?: string | null;
}

export interface ProjectResponse {
  title: string;
  description: string;
  /** completed, ongoing, planned, etc. */
  status: string;
  /** Array of image URLs */
  images?: string[];
  location: string;
  _id: string;
  builder_id: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  title: string;
  description: string;
  /** completed, ongoing, planned, etc. */
  status: string;
  /** Array of image URLs */
  images?: string[];
  location: string;
}

export interface QueryLogResponse {
  query_text: string;
  /** Vector embedding as string */
  query_embedding?: string | null;
  /** Detected user intent */
  intent?: string | null;
  /** References to results (JSON array) */
  result_refs?: string | null;
  _id: string;
  user_id?: string | null;
  timestamp: string;
}

export interface QueryLogCreate {
  query_text: string;
  /** Vector embedding as string */
  query_embedding?: string | null;
  /** Detected user intent */
  intent?: string | null;
  /** References to results (JSON array) */
  result_refs?: string | null;
  user_id?: string | null;
}

export interface ChatHistoryResponse {
  /** Array of messages */
  messages?: string[];
  _id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface ChatHistoryCreate {
  /** Array of messages */
  messages?: string[];
}

export interface ChatMessage {
  /** user or assistant */
  role: string;
  content: string;
  timestamp?: string;
}
