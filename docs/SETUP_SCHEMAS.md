# 🚀 Quick Setup Guide - Schema System

Follow these steps to get the schema generation system running.

## Step 1: Install Python Dependencies

```bash
cd apps/backend

# Activate virtual environment
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install new dependency
pip install pydantic2ts==1.3.0

# Or reinstall all
pip install -r requirements.txt
```

## Step 2: Test Schema Generation

```bash
# Still in apps/backend directory
python generate_schemas.py
```

**Expected Output:**
```
✅ TypeScript interfaces generated successfully!
📄 Output: ../../packages/schemas/generated/models.ts
📦 Generated 23 interfaces
```

## Step 3: Verify Generated File

```bash
# From project root
cat packages/schemas/generated/models.ts
```

You should see TypeScript interfaces like:
```typescript
export interface UserResponse {
  _id: string;
  name: string;
  email: string;
  role: string;
  // ...
}

export interface PropertyResponse {
  _id: string;
  seller_id: string;
  title: string;
  price: number;
  // ...
}
```

## Step 4: Build Schemas Package

```bash
# From project root
cd packages/schemas
npm run build
```

This will:
1. Run generation script
2. Compile TypeScript
3. Output to `dist/`

## Step 5: Test in Frontend

Create a test file to verify types work:

```typescript
// apps/web/src/test-types.ts
import { 
  PropertyResponse, 
  UserResponse,
  BuilderBidCreate 
} from '@proppal/schemas/generated'

// This should have full IntelliSense and type checking
const testProperty: PropertyResponse = {
  _id: "507f1f77bcf86cd799439011",
  seller_id: "507f1f77bcf86cd799439012",
  title: "Test Property",
  description: "Test description",
  price: 1000000,
  property_type: "house",
  area_sqft: 2000,
  bedrooms: 3,
  bathrooms: 2,
  floors: 2,
  city: "Islamabad",
  area: "F-10",
  lng: 73.0479,
  lat: 33.6844,
  images: [],
  metadata: {},
  last_indexed_at: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

console.log("Types work!", testProperty)
```

## Step 6: Run Full Build

```bash
# From project root
npm run build
```

Turbo will:
1. Build schemas (generate + compile)
2. Build other packages that depend on schemas
3. Ensure all types are in sync

---

## Quick Commands Reference

```bash
# Generate schemas only
cd apps/backend && python generate_schemas.py

# Build schemas package
cd packages/schemas && npm run build

# Build everything
npm run build

# Start development (generates schemas first)
npm run dev
```

---

## Troubleshooting

### "Module not found: @proppal/schemas/generated"

**Solution:**
```bash
cd packages/schemas
npm run build
```

### "pydantic2ts not found"

**Solution:**
```bash
cd apps/backend
pip install pydantic2ts==1.3.0
```

### Generated file is empty or has errors

**Solution:**
```bash
# Clean and regenerate
cd apps/backend
python generate_schemas.py

# Check for Python errors in the output
```

### Import errors in frontend

**Solution:**
```bash
# Ensure packages/schemas is built
cd packages/schemas
npm run clean
npm run build
```

---

## Verification Checklist

- [ ] Python dependencies installed
- [ ] `pydantic2ts` package available
- [ ] Generation script runs without errors
- [ ] `packages/schemas/generated/models.ts` exists
- [ ] Generated file contains all interfaces
- [ ] Schemas package builds successfully
- [ ] Frontend can import from `@proppal/schemas/generated`
- [ ] IntelliSense works for imported types

---

**Once all steps complete, the schema system is ready!** ✅

