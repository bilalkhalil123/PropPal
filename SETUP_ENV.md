# 🔧 Environment Setup - Quick Fix

## The Problem
You're seeing: `"Database client not initialized"` because the MongoDB connection string is not configured.

## ✅ Quick Fix (5 minutes)

### Step 1: Open Your `.env` File

```bash
# Navigate to backend directory
cd apps/backend

# Open .env file in your editor
code .env
# OR
notepad .env
```

### Step 2: Get Your MongoDB Atlas Connection String

1. Go to **MongoDB Atlas**: https://cloud.mongodb.com
2. Click **"Connect"** on your cluster
3. Choose **"Connect your application"**
4. Copy the connection string (looks like this):
   ```
   mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
   ```

### Step 3: Update Your `.env` File

Replace the contents with your actual connection string:

```env
# Replace these values with your actual MongoDB Atlas credentials
MONGODB_URL=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@YOUR_CLUSTER.mongodb.net/proppal?retryWrites=true&w=majority
MONGODB_DB_NAME=proppal
ENVIRONMENT=development
LOG_LEVEL=info
ALLOWED_ORIGINS=http://localhost:3000
```

**Important replacements:**
- `YOUR_USERNAME` → Your MongoDB Atlas username
- `YOUR_PASSWORD` → Your MongoDB Atlas password (URL-encoded if it has special characters)
- `YOUR_CLUSTER` → Your cluster address (e.g., `cluster0.abc123.mongodb.net`)

### Step 4: Restart Your Backend Server

**If running with Docker:**
```bash
# From project root
npm run docker:down
npm run docker:up
```

**If running locally:**
```bash
# Stop the current server (Ctrl+C)
# Then restart:
cd apps/backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn services.main:app --reload
```

### Step 5: Verify the Connection

```bash
# Test the database health endpoint
curl http://localhost:8000/health/database
```

**Expected Success Response:**
```json
{
  "status": "ok",
  "connected": true,
  "database": "proppal",
  "mongodb_version": "7.0.x",
  "collections_count": 0,
  "collections": []
}
```

---

## 🆘 Still Not Working?

### Check 1: MongoDB Atlas IP Whitelist

1. Go to MongoDB Atlas
2. Navigate to **Network Access**
3. Click **"Add IP Address"**
4. Add `0.0.0.0/0` (allows all IPs - for development only)
5. Click **"Confirm"**

### Check 2: Database User Exists

1. Go to **Database Access** in Atlas
2. Ensure your user exists
3. Verify it has **"Read and write to any database"** permissions

### Check 3: Check Server Logs

Look for this message when starting the server:

**✅ Success:**
```
✅ Successfully connected to MongoDB database: proppal
```

**❌ Error:**
```
❌ Failed to connect to MongoDB: [Error details here]
⚠️  WARNING: MONGODB_URL not set in environment variables
```

### Check 4: Verify `.env` File Location

The `.env` file MUST be in: `apps/backend/.env`

```
PropPal/
└── apps/
    └── backend/
        ├── .env          ← Must be here!
        ├── .env.example
        └── services/
            └── main.py
```

### Check 5: Test MongoDB Connection String

Test your connection string directly with Python:

```bash
cd apps/backend
source venv/bin/activate
python
```

Then in Python:
```python
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("MONGODB_URL")
print(f"Connection string: {url}")

try:
    client = MongoClient(url)
    client.admin.command('ping')
    print("✅ Connection successful!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

---

## 📝 Common Issues

### Issue: "Authentication failed"
**Solution:** Check username/password in connection string

### Issue: "Connection timeout"
**Solution:** 
1. Check internet connection
2. Add `0.0.0.0/0` to IP whitelist
3. Verify cluster is running in Atlas

### Issue: "MONGODB_URL not set"
**Solution:**
1. Ensure `.env` file exists in `apps/backend/`
2. Check file has the correct `MONGODB_URL=...` line
3. Restart the server

### Issue: Special characters in password
**Solution:** URL-encode special characters:
- `@` → `%40`
- `#` → `%23`
- `$` → `%24`
- `%` → `%25`
- `&` → `%26`

Or use MongoDB's connection string builder in Atlas.

---

## 🎯 Quick Checklist

- [ ] `.env` file exists in `apps/backend/`
- [ ] `MONGODB_URL` is set with valid connection string
- [ ] Username and password are correct
- [ ] IP whitelist includes `0.0.0.0/0` or your IP
- [ ] Database user has read/write permissions
- [ ] Backend server has been restarted
- [ ] No typos in the connection string

---

## 🚀 Next Steps

Once connected successfully:

1. **Test insertion:**
   ```bash
   curl -X POST http://localhost:8000/test/insert
   ```

2. **View in MongoDB Atlas:**
   - Go to Atlas → Browse Collections
   - You should see `proppal` database with `test_collection`

3. **Start building:**
   - Ready to implement agents!
   - Ready to create real collections!

---

**Need more help?** Check `docs/DATABASE_TESTING.md` for comprehensive testing guide.

