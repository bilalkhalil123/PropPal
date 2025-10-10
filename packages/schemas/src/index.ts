// PropPal Shared Schemas
// This package contains shared TypeScript schemas and validators

// Original Zod schemas (for frontend validation)
export * from './common'
export * from './user'
export * from './property'

// Re-export generated Pydantic models (for API type safety)
export * from '../generated/models'
