# Qdrant Migration - Complete Step-by-Step Plan

## Summary

Your system has been successfully migrated from MongoDB Atlas Vector Search to Qdrant. Here's what was done and what you need to do next.

## What Was Changed

### ✅ Completed Changes

1. **Qdrant Client Service** (`apps/backend/common/qdrant.py`)
   - Singleton Qdrant client
   - Collection initialization functions

2. **Vector Search Service** (`apps/backend/services/vector_search/qdrant_service.py`)
   - Functions to store embeddings in Qdrant
   - Functions to search embeddings in Qdrant
   - Supports properties, builder profiles, and builder services

3. **Configuration** (`apps/backend/common/config.py`)
   - Added `QDRANT_URL` and `QDRANT_API_KEY` settings

4. **Updated All Search Functions**
   - `apps/backend/api/search/router.py` - Property search API
   - `apps/backend/api/builder/router.py` - Builder profile search
   - `apps/backend/agents/listing/tools/property_search.py` - Property search tool
   - `apps/backend/agents/builder/tools/builder_search.py` - Builder search tools

5. **Updated All Backfill Jobs**
   - `backfill_property_embeddings.py` - Now stores in Qdrant
   - `backfill_builders_profiles_embeddings.py` - Now stores in Qdrant
   - `backfill_builder_services.py` - Now stores in Qdrant

6. **Migration Scripts**
   - `jobs/init_qdrant_collections.py` - Initialize Qdrant collections
   - `jobs/migrate_to_qdrant.py` - Migrate existing data

## Step-by-Step Implementation Guide

### Step 1: Install Qdrant

**Option A: Local (Docker)**
```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

**Option B: Cloud (Recommended for Production)**
1. Sign up at https://cloud.qdrant.io/
2. Create a cluster
3. Get your API key and URL

### Step 2: Install Python Dependencies

```bash
cd apps/backend
pip install qdrant-client
```

Or add to `requirements.txt`:
```
qdrant-client>=1.7.0
```

### Step 3: Configure Environment Variables

Add to your `.env` file in `apps/backend/`:

```env
# Qdrant Configuration
QDRANT_URL=http://localhost:6333
# For cloud instances, also add:
# QDRANT_API_KEY=your-api-key-here
```

### Step 4: Initialize Qdrant Collections

```bash
cd apps/backend
python -m jobs.init_qdrant_collections
```

This creates three collections:
- `properties`
- `builder_profiles`
- `builder_services`

### Step 5: Migrate Existing Data (If You Have Existing Embeddings)

If you already have embeddings in MongoDB, migrate them:

```bash
# Migrate all collections
python -m jobs.migrate_to_qdrant

# Or migrate specific collection
python -m jobs.migrate_to_qdrant --collection properties
python -m jobs.migrate_to_qdrant --collection builder_profiles
python -m jobs.migrate_to_qdrant --collection builder_services
```

### Step 6: Test the Migration

1. **Test Property Search**
   ```bash
   curl -X POST http://localhost:8000/api/search/properties \
     -H "Content-Type: application/json" \
     -d '{"query": "3 bedroom house in Lahore", "k": 5}'
   ```

2. **Test Builder Profile Search**
   ```bash
   curl -X POST http://localhost:8000/api/builder/profiles/search \
     -H "Content-Type: application/json" \
     -d '{"query": "residential construction", "k": 5}'
   ```

3. **Check Qdrant Dashboard**
   - Open http://localhost:6333/dashboard
   - Verify collections exist and have data

### Step 7: Re-run Data Import Jobs (Optional)

If you want to re-import your data with Qdrant support:

```bash
# Import properties
python -m jobs.property_import --json-path ../../data/zameen_listing_results.json --seller-id <seller_id>

# Backfill property embeddings (will now store in Qdrant)
python -m jobs.backfill_property_embeddings

# Import builder profiles
python -m jobs.backfill_builders_profiles_embeddings --file ../../data/builder_profiles.json

# Import builder services
python -m jobs.backfill_builder_services --file ../../data/builder_services.json
```

## Architecture Overview

### Before (MongoDB Atlas Vector Search)
```
User Query → Embedding → MongoDB $vectorSearch → Results
```

### After (Qdrant + MongoDB)
```
User Query → Embedding → Qdrant Search → Get IDs → MongoDB Fetch → Results
```

### Data Flow

1. **Storing Data:**
   - Data stored in MongoDB (as before)
   - Embedding generated
   - Embedding stored in Qdrant with metadata (city, price, etc.)

2. **Searching:**
   - Query converted to embedding
   - Qdrant performs vector search, returns IDs + scores
   - MongoDB fetches full documents using IDs
   - Results sorted by Qdrant scores

## Key Benefits

1. ✅ **No Collection Limit** - Qdrant has no limit on collections
2. ✅ **Better Performance** - Optimized for vector search
3. ✅ **Scalability** - Can handle millions of vectors
4. ✅ **Backward Compatible** - MongoDB embeddings still stored (optional)

## Troubleshooting

### Qdrant Not Connecting

**Error:** `Connection refused` or `Cannot connect to Qdrant`

**Solution:**
1. Check if Qdrant is running: `docker ps | grep qdrant`
2. Verify `QDRANT_URL` in `.env` file
3. For cloud: Check `QDRANT_API_KEY` is correct

### No Search Results

**Error:** Searches return empty results

**Solution:**
1. Run migration: `python -m jobs.migrate_to_qdrant`
2. Check Qdrant has data: http://localhost:6333/dashboard
3. Verify embeddings exist in MongoDB

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'qdrant_client'`

**Solution:**
```bash
pip install qdrant-client
```

## Files Modified

### New Files
- `apps/backend/common/qdrant.py`
- `apps/backend/services/vector_search/qdrant_service.py`
- `apps/backend/services/vector_search/__init__.py`
- `apps/backend/jobs/init_qdrant_collections.py`
- `apps/backend/jobs/migrate_to_qdrant.py`
- `docs/QDRANT_MIGRATION_GUIDE.md`

### Modified Files
- `apps/backend/common/config.py` - Added Qdrant settings
- `apps/backend/api/search/router.py` - Uses Qdrant
- `apps/backend/api/builder/router.py` - Uses Qdrant
- `apps/backend/agents/listing/tools/property_search.py` - Uses Qdrant
- `apps/backend/agents/builder/tools/builder_search.py` - Uses Qdrant
- `apps/backend/jobs/backfill_property_embeddings.py` - Stores in Qdrant
- `apps/backend/jobs/backfill_builders_profiles_embeddings.py` - Stores in Qdrant
- `apps/backend/jobs/backfill_builder_services.py` - Stores in Qdrant

## Next Steps

1. ✅ Install Qdrant (Docker or Cloud)
2. ✅ Install `qdrant-client` package
3. ✅ Add Qdrant config to `.env`
4. ✅ Initialize collections
5. ✅ Migrate existing data
6. ✅ Test search functionality
7. ✅ Monitor Qdrant dashboard

## Support

For issues or questions:
1. Check Qdrant logs: `docker logs <qdrant-container>`
2. Check Qdrant dashboard: http://localhost:6333/dashboard
3. Review migration guide: `docs/QDRANT_MIGRATION_GUIDE.md`

## Rollback (If Needed)

If you need to rollback:
1. MongoDB embeddings are still stored (for backward compatibility)
2. Revert search functions to use `$vectorSearch`
3. Ensure MongoDB Atlas indexes are still configured

The code maintains backward compatibility, so rollback is straightforward.

