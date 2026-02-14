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
