# Schema Generation System

This document explains how the PropPal schema generation system works.

## Overview

PropPal uses a **single source of truth** approach for data schemas:
- **Backend**: Pydantic models define the schema
- **Frontend**: TypeScript interfaces are **auto-generated** from Pydantic models
- **Contract Enforcement**: Type safety across the full stack

## Architecture

```
┌─────────────────────────────┐
│  Pydantic Models (Python)   │
│  apps/backend/models/       │
│  - users.py                 │
│  - properties.py            │
│  - builder_*.py             │
│  - etc.                     │
└──────────┬──────────────────┘
           │
           │ generate_schemas.py
           ↓
┌─────────────────────────────┐
│  TypeScript Interfaces      │
│  packages/schemas/          │
│  generated/models.ts        │
│  - UserResponse             │
│  - PropertyResponse         │
│  - etc.                     │
└──────────┬──────────────────┘
           │
           │ import
           ↓
┌─────────────────────────────┐
│  Frontend (Next.js)         │
│  Type-safe API calls        │
└─────────────────────────────┘
```

## How It Works

### 1. Pydantic Models (Backend)

All models are defined in `apps/backend/models/`:

```python
# apps/backend/models/users.py
from pydantic import BaseModel, EmailStr, Field
from .base import PyObjectId

class UserResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    email: EmailStr
    role: str
    created_at: datetime
```

### 2. Generation Script

The script `apps/backend/generate_schemas.py`:
1. Imports all Pydantic models
2. Converts them to JSON Schema
3. Transforms JSON Schema to TypeScript
4. Writes to `packages/schemas/generated/models.ts`

### 3. Generated TypeScript

```typescript
// packages/schemas/generated/models.ts (AUTO-GENERATED)
export interface UserResponse {
  _id: string;  // ObjectId converted to string
  name: string;
  email: string;
  role: string;
  created_at: string;
}
```

### 4. Frontend Usage

```typescript
// apps/web/src/lib/api-client.ts
import { UserResponse, PropertyResponse } from '@proppal/schemas/generated'

async function getUser(id: string): Promise<UserResponse> {
  const response = await fetch(`/api/users/${id}`)
  return response.json()  // Type-safe!
}
```

## Available Models

### User Models
- `UserResponse` - User data for API responses (no password_hash)
- `UserCreate` - User creation request

### Property Models
- `PropertyResponse` - Property listing data
- `PropertyCreate` - Property creation request
- `PropertyAmenityResponse` - Nearby amenities
- `PropertyAmenityCreate` - Amenity creation

### Builder Models
- `BuilderProfileResponse` - Builder profile data
- `BuilderProfileCreate` - Builder profile creation
- `BuilderServiceResponse` - Builder service offerings
- `BuilderServiceCreate` - Service creation
- `BuilderBidResponse` - Bids on projects
- `BuilderBidCreate` - Bid creation

### Project Models
- `UserProjectResponse` - User-posted projects
- `UserProjectCreate` - Project creation
- `ProjectResponse` - Builder portfolio projects
- `ProjectCreate` - Portfolio project creation

### Visit & Chat Models
- `VisitResponse` - Property visit bookings
- `VisitCreate` - Visit booking request
- `ChatHistoryResponse` - Chat conversation
- `ChatHistoryCreate` - Chat creation
- `ChatMessage` - Individual chat message
- `QueryLogResponse` - NLP query logs
- `QueryLogCreate` - Query log creation

## Build Process

### Manual Generation

```bash
# From backend directory
cd apps/backend
python generate_schemas.py
```

### Automatic Generation (via Turborepo)

The schemas are automatically generated when building:

```bash
# Build schemas package (triggers generation)
npm run build

# Or build everything
turbo build
```

### Turborepo Configuration

In `turbo.json`:

```json
{
  "pipeline": {
    "@proppal/schemas#build": {
      "outputs": ["dist/**", "generated/models.ts"]
    },
    "web#dev": {
      "dependsOn": ["@proppal/schemas#build"]
    }
  }
}
```

**This ensures**:
1. Schemas are generated before web app starts
2. Web app always uses latest schema definitions
3. Type safety is enforced at build time

## Type Conversions

### Python → TypeScript

| Python Type | TypeScript Type |
|-------------|-----------------|
| `str` | `string` |
| `int` | `number` |
| `float` | `number` |
| `bool` | `boolean` |
| `List[T]` | `Array<T>` |
| `Dict` | `Record<string, any>` |
| `Optional[T]` | `T \| null` |
| `PyObjectId` | `string` |
| `datetime` | `string` (ISO format) |

### Special Handling

**MongoDB ObjectId:**
- Backend: `PyObjectId` (BSON ObjectId)
- Frontend: `string` (24-character hex)

**Timestamps:**
- Backend: `datetime`
- Frontend: `string` (ISO 8601 format)

**JSON Fields:**
- Backend: `str` (JSON as string)
- Frontend: `string` (parse with `JSON.parse()`)

## Integration Testing

### Verify Generated Types

```typescript
// apps/web/src/__tests__/schema-test.ts
import { PropertyResponse } from '@proppal/schemas/generated'

// This will fail at compile time if schema doesn't match
const property: PropertyResponse = {
  _id: "507f1f77bcf86cd799439011",
  seller_id: "507f1f77bcf86cd799439012",
  title: "3-Bedroom House",
  price: 15000000,
  // ... all required fields
}
```

### API Client Example

```typescript
// apps/web/src/lib/api-client.ts
import { 
  PropertyResponse, 
  PropertyCreate,
  BuilderBidResponse,
  VisitCreate 
} from '@proppal/schemas/generated'

export const api = {
  properties: {
    async getAll(): Promise<PropertyResponse[]> {
      const res = await fetch('/api/properties')
      return res.json()
    },
    
    async create(data: PropertyCreate): Promise<PropertyResponse> {
      const res = await fetch('/api/properties', {
        method: 'POST',
        body: JSON.stringify(data)
      })
      return res.json()
    }
  },
  
  builders: {
    async getBids(projectId: string): Promise<BuilderBidResponse[]> {
      const res = await fetch(`/api/projects/${projectId}/bids`)
      return res.json()
    }
  },
  
  visits: {
    async book(data: VisitCreate): Promise<VisitResponse> {
      const res = await fetch('/api/visits', {
        method: 'POST',
        body: JSON.stringify(data)
      })
      return res.json()
    }
  }
}
```

## Best Practices

### DO ✅

1. **Always regenerate** after changing Pydantic models
2. **Import from generated** for API types
3. **Use Zod schemas** for frontend validation
4. **Type API responses** with generated interfaces
5. **Run build** before committing schema changes

### DON'T ❌

1. **Don't manually edit** `generated/models.ts`
2. **Don't duplicate** types in frontend
3. **Don't skip** generation step
4. **Don't commit** without building schemas
5. **Don't use `any`** for API responses

## Troubleshooting

### Schema Not Updating

```bash
# Clean and rebuild
npm run clean
npm run build
```

### Import Errors

```bash
# Ensure schemas are built
cd packages/schemas
npm run build
```

### Type Mismatches

1. Check backend model definition
2. Regenerate schemas
3. Verify frontend import path

## Development Workflow

### Adding New Model

1. **Create Pydantic model** in `apps/backend/models/`
   ```python
   # apps/backend/models/new_model.py
   class NewModelResponse(BaseModel):
       id: PyObjectId = Field(alias="_id")
       # ... fields
   ```

2. **Export in `__init__.py`**
   ```python
   # apps/backend/models/__init__.py
   from .new_model import NewModelResponse
   __all__ = [..., "NewModelResponse"]
   ```

3. **Add to generation script**
   ```python
   # apps/backend/generate_schemas.py
   from models import NewModelResponse
   models = {
       ...,
       "NewModelResponse": NewModelResponse
   }
   ```

4. **Generate and build**
   ```bash
   npm run build
   ```

5. **Use in frontend**
   ```typescript
   import { NewModelResponse } from '@proppal/schemas/generated'
   ```

## CI/CD Integration

### Pre-commit Hook

```bash
#!/bin/sh
# .husky/pre-commit

# Generate schemas before commit
cd packages/schemas && npm run generate
git add generated/models.ts
```

### GitHub Actions

```yaml
- name: Build Schemas
  run: |
    npm install
    npm run build
    
- name: Type Check
  run: |
    cd apps/web
    npm run type-check
```

---

**Schema generation ensures type safety across the entire stack!** 🎯

