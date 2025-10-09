# Phase 0: Unified Setup & Architectural Foundation - COMPLETE ✅

This document details the completed Phase 0 implementation for PropPal monorepo.

## Overview

Phase 0 establishes a **backend-focused local development environment** with:
- ✅ Turborepo monorepo with selective build configuration
- ✅ Docker Compose for backend services (Gateway + NLP placeholder)
- ✅ External MongoDB Atlas integration (no local database)
- ✅ Minimal shared schemas package
- ✅ Unified linting and formatting

## Architecture Decisions

### 1. **Selective Builds**
- **Backend & Schemas**: Full build pipeline for production deployment
- **Web App**: Development and linting only (deployed separately to Vercel)

### 2. **External Database**
- **No local MongoDB**: All services connect to MongoDB Atlas
- **Environment-based**: Connection string configured via `.env`

### 3. **Docker Services**
- **Gateway Service**: FastAPI gateway (port 8000)
- **NLP Service**: Placeholder for NLP/RAG module (port 8001, optional)
- **No frontend**: Web/Mobile developed independently

---

## Project Structure

```
PropPal/
├── apps/
│   ├── backend/              # Backend services
│   │   ├── Dockerfile        # Unified backend container
│   │   ├── .dockerignore
│   │   ├── requirements.txt  # Python dependencies
│   │   └── services/
│   │       └── main.py       # FastAPI gateway
│   └── web/                  # Next.js (dev/lint only)
├── packages/
│   └── schemas/              # Shared TypeScript schemas
│       ├── package.json
│       ├── tsconfig.json
│       └── src/
│           ├── index.ts
│           ├── common.ts
│           ├── user.ts
│           └── property.ts
├── infra/
│   └── docker/
│       └── docker-compose.yml # Backend services only
├── package.json              # Root workspace config
├── turbo.json                # Selective build config
└── .env.example              # Environment template
```

---

## Setup Instructions

### Prerequisites

- **Node.js** >= 18.0.0
- **Python** >= 3.13
- **Docker** and **Docker Compose**
- **MongoDB Atlas** account and cluster

### Step 1: Clone and Install

```bash
git clone https://github.com/bilalrana8718/PropPal.git
cd PropPal
npm install
```

### Step 2: Setup Backend Python Environment

```bash
cd apps/backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cd ../..
```

### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your MongoDB Atlas connection string
# MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/proppal?retryWrites=true&w=majority
```

### Step 4: Start Backend Services

```bash
npm run docker:up
```

**Services available at:**
- 🔌 Gateway API: http://localhost:8000
- 📊 API Docs: http://localhost:8000/docs

### Step 5: Verify Installation

```bash
# Check running containers
docker ps

# View logs
npm run docker:logs

# Test API
curl http://localhost:8000
# Should return: {"status":"ok"}
```

---

## Available Commands

### Monorepo Commands

```bash
# Development
npm run dev          # Start all dev servers
npm run build        # Build backend + schemas (NOT web)
npm run lint         # Lint all code
npm run lint:js      # Lint JavaScript/TypeScript only
npm run lint:py      # Lint Python only
npm run format       # Format all code
npm run format:js    # Format JS/TS
npm run format:py    # Format Python
npm run test         # Run all tests
npm run clean        # Clean build artifacts

# Docker
npm run docker:up    # Start backend services
npm run docker:down  # Stop backend services
npm run docker:logs  # View service logs
```

### Package-Specific Commands

```bash
# Schemas package
cd packages/schemas
npm run build        # Build schemas
npm run dev          # Watch mode
npm run lint         # Lint schemas

# Web app (local dev only)
cd apps/web
npm run dev          # Start Next.js dev server
npm run lint         # Lint web code
```

---

## Configuration Details

### Turborepo Configuration

The `turbo.json` is configured for **selective builds**:

```json
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", "build/**"]
    },
    "web#build": {
      "cache": false,
      "dependsOn": []
    }
  }
}
```

**What this means:**
- Running `npm run build` will build backend and packages/schemas
- The web app build is **excluded** from the monorepo build
- Web app is meant for local dev/lint, deployed separately to Vercel

### Docker Compose Structure

The `docker-compose.yml` includes:

```yaml
services:
  gateway:
    # FastAPI Gateway - Main API entry point
    ports: ["8000:8000"]
    environment:
      - MONGODB_URL=${MONGODB_URL}

  nlp-service:
    # NLP/RAG Module - Placeholder
    ports: ["8001:8001"]
    profiles: ["nlp"]  # Optional service
```

**To start with NLP service:**
```bash
docker compose --profile nlp -f infra/docker/docker-compose.yml up -d
```

### Environment Variables

Required in `.env`:

```bash
# MongoDB Atlas (Required)
MONGODB_URL=mongodb+srv://...
MONGODB_DB_NAME=proppal

# Backend Config
ENVIRONMENT=development
LOG_LEVEL=info
ALLOWED_ORIGINS=http://localhost:3000

# AI/ML (Optional)
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4
```

---

## Linting & Formatting

### JavaScript/TypeScript

**Tools:**
- ESLint with TypeScript support
- Prettier for formatting

**Configuration:**
- `.eslintrc.json` - Root ESLint config
- `prettier.config.js` - Prettier settings
- `.editorconfig` - Editor consistency

**Usage:**
```bash
npm run lint:js      # Check JS/TS
npm run format:js    # Format JS/TS
```

### Python

**Tools:**
- Black for formatting (120 char line length)
- Flake8 for linting
- isort for import sorting
- mypy for type checking

**Configuration:**
- `pyproject.toml` - Black, isort, mypy settings
- `.flake8` - Flake8 rules
- `mypy.ini` - Type checking config

**Usage:**
```bash
npm run lint:py      # Lint Python (flake8 + mypy)
npm run format:py    # Format Python (black + isort)
```

---

## Shared Schemas Package

The `@proppal/schemas` package provides TypeScript schemas using Zod:

### Usage Example

```typescript
import { PropertySchema, CreatePropertySchema } from '@proppal/schemas'

// Validate property data
const property = PropertySchema.parse(data)

// Type-safe property creation
const newProperty: CreateProperty = {
  title: "3-Bedroom House",
  price: 15000000,
  location: { ... },
  // ...
}
```

### Available Schemas

- **Common**: `ApiResponse`, `Pagination`
- **User**: `User`, `CreateUser`, `UserRole`
- **Property**: `Property`, `CreateProperty`, `PropertyType`, `PropertyStatus`, `Location`, `PropertyFeatures`

---

## Development Workflow

### Backend Development

1. **Start services:**
   ```bash
   npm run docker:up
   ```

2. **Make changes** to `apps/backend/services/main.py`

3. **Hot reload** is enabled - changes reflect automatically

4. **Test API:**
   ```bash
   curl http://localhost:8000
   ```

### Frontend Development (Local)

1. **Start web dev server:**
   ```bash
   cd apps/web
   npm run dev
   ```

2. **Access at:** http://localhost:3000

3. **For production:** Deploy to Vercel (not part of monorepo build)

### Schema Development

1. **Edit schemas:**
   ```bash
   cd packages/schemas
   npm run dev  # Watch mode
   ```

2. **Build schemas:**
   ```bash
   npm run build
   ```

3. **Use in apps:**
   ```typescript
   import { PropertySchema } from '@proppal/schemas'
   ```

---

## Troubleshooting

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9
```

### Docker Issues

```bash
# Clean up
docker compose -f infra/docker/docker-compose.yml down
docker system prune -f

# Rebuild
docker compose -f infra/docker/docker-compose.yml build --no-cache
docker compose -f infra/docker/docker-compose.yml up -d
```

### MongoDB Connection Issues

1. **Check your `.env` file** - ensure `MONGODB_URL` is correct
2. **Verify Atlas cluster** - ensure it's running and accessible
3. **Check IP whitelist** - add `0.0.0.0/0` for development
4. **Test connection:**
   ```bash
   docker compose -f infra/docker/docker-compose.yml logs gateway
   ```

### Python Dependencies

```bash
cd apps/backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

---

## Next Steps

Phase 0 is complete! You can now:

1. ✅ **Develop Backend Services**: Add routes to `apps/backend/services/main.py`
2. ✅ **Create Agents**: Implement Listing Agent, Builder Agent, NLP Module
3. ✅ **Use Shared Schemas**: Import from `@proppal/schemas`
4. ✅ **Develop Frontend**: Run web app locally, deploy to Vercel
5. ✅ **Integrate MongoDB**: Use Atlas cluster for data persistence

---

## Phase 0 Checklist

- [x] Monorepo structure with workspaces
- [x] Turborepo with selective builds
- [x] Docker Compose for backend services
- [x] Backend Dockerfile with Python 3.13
- [x] External MongoDB Atlas integration
- [x] Shared schemas package with Zod
- [x] Linting/formatting for JS/TS and Python
- [x] Environment configuration
- [x] Documentation

**Status**: ✅ **COMPLETE**

**Date**: October 9, 2025

