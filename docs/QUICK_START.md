# 🚀 PropPal Quick Start Guide

Get PropPal backend services running in 5 minutes!

## Prerequisites

✅ Node.js >= 18.0.0  
✅ Python >= 3.13  
✅ Docker & Docker Compose  
✅ MongoDB Atlas account

---

## Setup in 4 Steps

### 1️⃣ Clone & Install

```bash
git clone https://github.com/bilalrana8718/PropPal.git
cd PropPal
npm install
```

### 2️⃣ Setup Python Environment

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

### 3️⃣ Configure MongoDB Atlas

```bash
# Copy environment file
cp .env.example .env

# Edit .env and add your MongoDB Atlas connection string
# MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/proppal?retryWrites=true&w=majority
```

**Get your MongoDB Atlas URL:**
1. Go to https://cloud.mongodb.com
2. Create a cluster (free tier available)
3. Click "Connect" → "Connect your application"
4. Copy the connection string
5. Replace `<username>` and `<password>`

### 4️⃣ Start Backend Services

```bash
npm run docker:up
```

**That's it!** 🎉

---

## Access Your Services

| Service | URL | Description |
|---------|-----|-------------|
| 🔌 Gateway API | http://localhost:8000 | FastAPI Gateway |
| 📖 API Docs | http://localhost:8000/docs | Swagger UI |
| 🧪 Test Endpoint | http://localhost:8000 | Health check |

---

## Quick Commands

```bash
# Start services
npm run docker:up

# Stop services
npm run docker:down

# View logs
npm run docker:logs

# Restart services
npm run docker:down && npm run docker:up
```

---

## Verify Installation

### Test the API

```bash
# Health check
curl http://localhost:8000

# Should return: {"status":"ok"}
```

### Check logs

```bash
npm run docker:logs
```

### Check containers

```bash
docker ps
```

You should see:
- `proppal-gateway` running on port 8000

---

## Development Workflow

### Backend Development

```bash
# Services auto-reload on code changes
npm run docker:up

# Edit apps/backend/services/main.py
# Changes reflect immediately
```

### Frontend Development (Local)

```bash
cd apps/web
npm run dev
# Visit http://localhost:3000
```

### Build Schemas

```bash
cd packages/schemas
npm run build
```

---

## Common Issues

### Port 8000 Already in Use

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9
```

### MongoDB Connection Failed

1. Check `.env` file - verify `MONGODB_URL`
2. Ensure Atlas cluster is running
3. Add `0.0.0.0/0` to IP whitelist (for development)
4. Check container logs: `npm run docker:logs`

### Docker Build Failed

```bash
# Clean rebuild
docker compose -f infra/docker/docker-compose.yml down
docker system prune -f
docker compose -f infra/docker/docker-compose.yml build --no-cache
docker compose -f infra/docker/docker-compose.yml up -d
```

---

## What's Next?

✅ **Add API Routes**: Edit `apps/backend/services/main.py`  
✅ **Create Agents**: Implement Listing, Builder, NLP agents  
✅ **Use Schemas**: Import from `@proppal/schemas`  
✅ **Develop Frontend**: Run Next.js locally  
✅ **Deploy**: Push to production when ready

---

## More Information

📖 **[Complete Setup Guide](./PHASE0_SETUP.md)** - Detailed documentation  
📖 **[Development Guide](./DEVELOPMENT.md)** - Development workflows  
📖 **[Contributing](./CONTRIBUTING.md)** - How to contribute

---

**Happy Coding! 🏠✨**

