# PropPal Docker Infrastructure

This directory contains Docker configuration for PropPal backend services.

## Services

### Gateway Service (Port 8000)
FastAPI gateway - main API entry point for the platform.

### NLP Service (Port 8001) - Optional
NLP/RAG module placeholder - enabled with `--profile nlp`

## Usage

### Start Services

```bash
# From project root
npm run docker:up

# Or directly
docker compose -f infra/docker/docker-compose.yml up -d
```

### Start with NLP Service

```bash
docker compose --profile nlp -f infra/docker/docker-compose.yml up -d
```

### Stop Services

```bash
npm run docker:down

# Or directly
docker compose -f infra/docker/docker-compose.yml down
```

### View Logs

```bash
npm run docker:logs

# Or specific service
docker compose -f infra/docker/docker-compose.yml logs -f gateway
```

### Rebuild Services

```bash
docker compose -f infra/docker/docker-compose.yml build --no-cache
docker compose -f infra/docker/docker-compose.yml up -d
```

## Environment Variables

Services use environment variables from `.env` file in the project root.

Required variables:
- `MONGODB_URL` - MongoDB Atlas connection string
- `MONGODB_DB_NAME` - Database name (default: proppal)

Optional variables:
- `ENVIRONMENT` - Environment (development/production)
- `LOG_LEVEL` - Logging level (debug/info/warning/error)
- `ALLOWED_ORIGINS` - CORS origins
- `OPENAI_API_KEY` - OpenAI API key for NLP service

## Architecture

```
┌─────────────────┐
│  Gateway:8000   │ ──┐
└─────────────────┘   │
                      ├──> MongoDB Atlas (External)
┌─────────────────┐   │
│ NLP Service:8001│ ──┘
└─────────────────┘
```

**Note:** MongoDB is external (Atlas), not running in Docker.

## Networking

All services are connected via the `proppal-network` bridge network.

Services can communicate using service names:
- `gateway` → `http://gateway:8000`
- `nlp-service` → `http://nlp-service:8001`

## Health Checks

Gateway service includes health check:
- Endpoint: `http://localhost:8000/`
- Interval: 30s
- Timeout: 10s
- Retries: 3

Check health status:
```bash
docker ps
# Look for "healthy" in STATUS column
```

## Development

Services use volume mounts for hot reload:
- Backend code: `../../apps/backend:/app`
- Python venv excluded: `/app/venv`

Changes to Python code automatically reload the service.

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose -f infra/docker/docker-compose.yml logs gateway

# Check if port is in use
netstat -ano | findstr :8000  # Windows
lsof -ti:8000                 # macOS/Linux
```

### MongoDB connection issues

1. Verify `.env` has correct `MONGODB_URL`
2. Check Atlas cluster is running
3. Ensure IP whitelist includes your IP or `0.0.0.0/0`
4. Test connection from container:
   ```bash
   docker exec -it proppal-gateway python -c "from pymongo import MongoClient; print(MongoClient('$MONGODB_URL').server_info())"
   ```

### Clean slate

```bash
# Stop and remove everything
docker compose -f infra/docker/docker-compose.yml down -v

# Remove all PropPal images
docker images | grep proppal | awk '{print $3}' | xargs docker rmi -f

# Rebuild
docker compose -f infra/docker/docker-compose.yml build --no-cache
docker compose -f infra/docker/docker-compose.yml up -d
```

