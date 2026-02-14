# Jobs

## Weekly property scrape

The script `weekly_property_scrape.py` orchestrates the weekly scrape workflow:

1. Fetch 200 URLs per city (Lahore, Karachi, Islamabad)
2. Remove sold/expired properties
3. Filter already-present URLs
4. Ingest new URLs into the database

### Configuration

- `BACKEND_API_BASE_URL` (optional): Base URL for the API service. Defaults to `http://{HOST}:{PORT}` from `common.config`.

### Scheduling (example)

Use your scheduler of choice. For cron (Linux):

```
# Every Sunday at 02:00
0 2 * * 0 cd /path/to/apps/backend && python -m jobs.weekly_property_scrape
```

## Reset and backfill Qdrant embeddings

The script `reset_and_backfill_qdrant_embeddings.py`:

1. Drops Qdrant collections to remove old embeddings
2. Removes properties outside Lahore/Karachi/Islamabad
3. Calls the cleanup-sold endpoint
4. Rebuilds embeddings for builder profiles, builder services, and properties

This script expects the API to be running for the cleanup-sold call. You can override the API base URL:

```
# Example
BACKEND_API_BASE_URL=http://localhost:8000 python -m jobs.reset_and_backfill_qdrant_embeddings
```
