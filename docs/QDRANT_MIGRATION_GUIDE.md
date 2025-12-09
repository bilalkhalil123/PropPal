# Qdrant Migration Guide

This guide explains how to migrate from MongoDB Atlas Vector Search to Qdrant for vector similarity search.

## Overview

The system has been migrated from MongoDB Atlas Vector Search (which has a 3-table limit) to a hybrid architecture:
- **MongoDB Atlas**: Stores all actual data (properties, builder profiles, builder services, users)
- **Qdrant**: Stores and retrieves embeddings for vector similarity search

## Architecture

### Before (MongoDB Atlas Vector Search)
- Embeddings stored in MongoDB alongside data
- Vector search performed using MongoDB `$vectorSearch` aggregation
- Limited to 3 vector search indexes

### After (Qdrant + MongoDB)
- Embeddings stored in Qdrant
- Actual data remains in MongoDB
- Vector search performed in Qdrant, then full documents fetched from MongoDB
- No limit on number of collections

## Prerequisites

1. **Install Qdrant**
   - Local: `docker run -p 6333:6333 qdrant/qdrant`
   - Cloud: Sign up at https://cloud.qdrant.io/

2. **Install Python Dependencies**
   ```bash
   pip install qdrant-client
   ```

3. **Configure Environment Variables**
   Add to your `.env` file:
   ```env
   # Qdrant Configuration
   QDRANT_URL=http://localhost:6333  # or your Qdrant cloud URL
   QDRANT_API_KEY=your-api-key  # Optional, only for cloud instances
   ```

## Migration Steps

### Step 1: Initialize Qdrant Collections

Create the required Qdrant collections:

```bash
cd apps/backend
python -m jobs.init_qdrant_collections
```

This creates three collections:
- `properties` - Property embeddings
- `builder_profiles` - Builder profile embeddings
- `builder_services` - Builder service embeddings

### Step 2: Migrate Existing Data

If you have existing embeddings in MongoDB, migrate them to Qdrant:

```bash
# Migrate all collections
python -m jobs.migrate_to_qdrant

# Or migrate specific collection
python -m jobs.migrate_to_qdrant --collection properties
python -m jobs.migrate_to_qdrant --collection builder_profiles
python -m jobs.migrate_to_qdrant --collection builder_services
```

### Step 3: Update Your Data Import Jobs

All backfill jobs have been updated to automatically store embeddings in Qdrant:

- `backfill_property_embeddings.py` - Now stores in both MongoDB (for backward compatibility) and Qdrant
- `backfill_builders_profiles_embeddings.py` - Now stores in both MongoDB and Qdrant
- `backfill_builder_services.py` - Now stores in both MongoDB and Qdrant

When you run these jobs, embeddings will automatically be stored in Qdrant.

## How It Works

### Storing Embeddings

When data is inserted or updated:

1. Embedding is generated using the embedding service
2. Data is stored in MongoDB (without embedding or with embedding for backward compatibility)
3. Embedding is stored in Qdrant with metadata (e.g., city, price)

### Searching

When performing a vector search:

1. Query text is converted to an embedding
2. Qdrant performs vector similarity search and returns matching IDs with scores
3. Full documents are fetched from MongoDB using the IDs
4. Results are sorted by Qdrant scores and returned

## Code Changes

### Search Functions Updated

All search functions now use Qdrant:

- `apps/backend/api/search/router.py` - Property search API
- `apps/backend/api/builder/router.py` - Builder profile search API
- `apps/backend/agents/listing/tools/property_search.py` - Property search tool
- `apps/backend/agents/builder/tools/builder_search.py` - Builder search tools

### New Services

- `apps/backend/common/qdrant.py` - Qdrant client singleton
- `apps/backend/services/vector_search/qdrant_service.py` - Qdrant vector search service

## Benefits

1. **No Collection Limit**: Qdrant has no limit on the number of collections
2. **Better Performance**: Qdrant is optimized for vector search
3. **Scalability**: Qdrant can handle millions of vectors efficiently
4. **Flexibility**: Can add more collections without hitting MongoDB Atlas limits

## Troubleshooting

### Qdrant Connection Issues

If you get connection errors:
1. Ensure Qdrant is running: `docker ps | grep qdrant`
2. Check QDRANT_URL in your `.env` file
3. For cloud instances, verify QDRANT_API_KEY is set

### Missing Embeddings

If searches return no results:
1. Run the migration script: `python -m jobs.migrate_to_qdrant`
2. Check Qdrant collections: Use Qdrant dashboard at http://localhost:6333/dashboard
3. Verify embeddings exist in MongoDB: Check `embedding` or `embeddings` fields

### Performance Issues

If searches are slow:
1. Check Qdrant resource usage
2. Consider using Qdrant Cloud for better performance
3. Optimize batch sizes in migration scripts

## Maintenance

### Adding New Collections

To add a new collection for vector search:

1. Add collection name to `common/qdrant.py`
2. Create upsert and search functions in `services/vector_search/qdrant_service.py`
3. Update jobs to store embeddings in Qdrant
4. Update search functions to use Qdrant

### Monitoring

Monitor Qdrant:
- Dashboard: http://localhost:6333/dashboard
- Metrics: http://localhost:6333/metrics
- Health: http://localhost:6333/health

## Rollback Plan

If you need to rollback to MongoDB Atlas Vector Search:

1. The MongoDB embeddings are still stored (for backward compatibility)
2. Revert the search functions to use `$vectorSearch` aggregation
3. Ensure MongoDB Atlas vector search indexes are still configured

Note: The code keeps embeddings in MongoDB for backward compatibility, so rollback is straightforward.

