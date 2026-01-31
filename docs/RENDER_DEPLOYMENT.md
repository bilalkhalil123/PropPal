# PropPal: Merge dev → main & Deploy Backend to Render

This guide covers:
1. **Part A** – Merging your current branch (`dev`) into `main`
2. **Part B** – Deploying the backend to Render (full detail)

---

# Part A: Merge `dev` into `main`

You are currently on branch **`dev`** with uncommitted changes. Follow these steps in order.

## Step 1: Commit your current changes on `dev`

Your uncommitted files:
- `.gitignore`
- `apps/backend/requirements.runtime.txt`
- `packages/schemas/generated/models.ts`
- `packages/schemas/package.json`

Run (from repo root `PropPal`):

```powershell
cd "D:\8th Semester\FYP\PropPal"

# Stage all changes
git add .gitignore apps/backend/requirements.runtime.txt packages/schemas/generated/models.ts packages/schemas/package.json

# Or stage everything
git add -A

# Commit with a clear message
git commit -m "chore: python-jose fix, schemas generate path, prep for Render deploy"
```

## Step 2: Push `dev` to the remote

```powershell
git push origin dev
```

If the remote rejects (e.g. non-fast-forward), pull first:

```powershell
git pull origin dev --rebase
git push origin dev
```

## Step 3: Switch to `main` and update it

```powershell
git checkout main
git pull origin main
```

## Step 4: Merge `dev` into `main`

```powershell
git merge dev -m "Merge dev into main for Render deployment"
```

If you see “Already up to date,” then `main` already has everything from `dev`.  
If Git reports merge conflicts, fix them in the listed files, then:

```powershell
git add .
git commit -m "Merge dev into main (resolve conflicts)"
```

## Step 5: Push `main` to the remote

```powershell
git push origin main
```

## Step 6: (Optional) Switch back to `dev` for further work

```powershell
git checkout dev
```

---

# Part B: Deploy Backend to Render (Full Detail)

## Prerequisites

- GitHub repo: **PropPal** (with `main` up to date after Part A)
- Accounts (all free tiers are fine for now):
  - [Render](https://render.com) – backend
  - [Neon](https://neon.tech) – Postgres (you already have `DATABASE_URL`)
  - [Qdrant Cloud](https://qdrant.tech) – vector DB (you already have `QDRANT_URL` / `QDRANT_API_KEY`)
  - [Clerk](https://clerk.com) – auth (existing keys)
  - [Backblaze B2](https://www.backblaze.com/b2/) – storage (existing keys)
  - [GROQ](https://console.groq.com/) – API key for agents

## B.1 Create a Render account and connect GitHub

1. Go to [https://render.com](https://render.com) and sign up (or log in).
2. **Dashboard** → **Account Settings** (or **Connect account**) → connect your **GitHub** account and authorize Render to access your repositories.
3. Ensure Render can see the repo that contains PropPal (e.g. `FYP` or the repo that has `PropPal` as root or as a subfolder).

## B.2 Create a new Web Service (backend)

1. In Render Dashboard click **New +** → **Web Service**.
2. **Connect a repository**:
   - Select the GitHub account/org and the repository that contains PropPal.
   - If PropPal is the **root** of the repo, choose that repo. If PropPal is inside a monorepo, choose the repo; we’ll set the root directory in the next step.
3. Configure the service:

| Field | Value |
|--------|--------|
| **Name** | `proppal-backend` (or any name you like) |
| **Region** | Choose closest to your users (e.g. **Oregon (US West)** or **Frankfurt (EU Central)**) |
| **Branch** | `main` |
| **Root Directory** | Leave blank if the repo root is PropPal. If your repo root is **above** PropPal, set: `PropPal` (or the path to the folder that contains `apps/backend`). |
| **Runtime** | **Docker** |
| **Dockerfile Path** | If repo root is PropPal: `apps/backend/Dockerfile`. If root is above PropPal: `PropPal/apps/backend/Dockerfile`. |
| **Docker Context** | Same as Root Directory: leave blank if PropPal is repo root, otherwise e.g. `PropPal` so the Docker build context is the monorepo root (needed if Dockerfile copies from `apps/backend`). |

Important: Render runs `docker build` from the **root directory** you set. So:

- If **Root Directory** = blank (repo root = PropPal):  
  - **Dockerfile Path**: `apps/backend/Dockerfile`  
  - **Docker Context**: blank (defaults to repo root = PropPal; Dockerfile’s `COPY` paths are relative to that, so `COPY . .` copies PropPal root, not backend only – see B.3 below.)
- If **Root Directory** = `PropPal`:  
  - **Dockerfile Path**: `PropPal/apps/backend/Dockerfile`  
  - **Docker Context**: `PropPal`

If your repo is **only** the PropPal project (no parent folder), use:

- **Root Directory**: blank  
- **Dockerfile Path**: `apps/backend/Dockerfile`  
- **Docker Context**: `apps/backend` (so `COPY . .` only copies backend; recommended so you don’t copy the whole monorepo into the image).

## B.3 Docker build context (recommended)

So that the image only contains the backend (and builds faster), set:

- **Root Directory**: leave blank if PropPal is repo root.
- **Dockerfile Path**: `apps/backend/Dockerfile`
- **Docker Context**: `apps/backend`

Then the Dockerfile’s `COPY . .` is run from `apps/backend`, which is what the Dockerfile expects. If you don’t set Docker Context, Render may use repo root and the build might fail or copy unnecessary files. After creating the service, if the build fails with “file not found,” set **Docker Context** to `apps/backend` and **Dockerfile Path** to `Dockerfile` (relative to that context), i.e. path from context = `Dockerfile`.

Summary for a repo where PropPal is the root:

- **Root Directory**: *(blank)*  
- **Dockerfile Path**: `apps/backend/Dockerfile`  
- **Docker Context**: `apps/backend`  

Render will `cd` into `apps/backend` and run `docker build -f Dockerfile .` there.

## B.4 Instance type (free tier)

- **Plan**: **Free**.
- Free tier has **512 MB RAM**; your app uses `torch` and `sentence-transformers`, so the first deploy may **run out of memory** or be slow. If the build or start fails with an OOM error, see the “Lite backend” note at the end.

## B.5 Environment variables

In the Render Web Service → **Environment** tab, add these. Use **Add Environment Variable** and paste names/values (no quotes in the value unless the value itself must contain quotes).

**Required (from your `.env` and config):**

| Key | Value | Notes |
|-----|--------|--------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Your Neon connection string (same as in backend `.env`). Must be `postgresql+asyncpg://` for async. |
| `SECRET_KEY` | (same as local) | JWT/session secret; use a long random string in production. |
| `CLERK_SECRET_KEY` | (same as local) | From Clerk dashboard. |
| `CLERK_WEBHOOK_SECRET` | (same as local) | For webhooks. |
| `CLERK_JWKS_URL` | (same as local) | e.g. `https://national-kit-31.clerk.accounts.dev/.well-known/jwks.json` |
| `ALLOWED_ORIGINS` | Your frontend URLs | Comma-separated. For Vercel: `https://your-app.vercel.app`, and add `https://proppal-backend.onrender.com` if you call the API from the browser (or the exact Render URL you get). |
| `QDRANT_URL` | (same as local) | Qdrant Cloud URL. |
| `QDRANT_API_KEY` | (same as local) | Qdrant API key. |
| `GROQ_API_KEY` | (same as local) | From GROQ console. |
| `B2_ENDPOINT` | (same as local) | Backblaze S3 endpoint. |
| `B2_ACCESS_KEY` | (same as local) | Backblaze key. |
| `B2_SECRET_KEY` | (same as local) | Backblaze secret. |
| `B2_BUCKET` | (same as local) | Bucket name. |

**Optional but recommended:**

| Key | Value |
|-----|--------|
| `ENVIRONMENT` | `production` |
| `LOG_LEVEL` | `info` |
| `PYTHONUNBUFFERED` | `1` |

Do **not** put `.env` in the repo or paste real secrets into this doc; only add them in Render’s UI.

After you deploy, copy the **Render URL** (e.g. `https://proppal-backend.onrender.com`) and add it to `ALLOWED_ORIGINS` if needed, and use it as `NEXT_PUBLIC_API_URL` (or equivalent) in the Vercel frontend.

## B.6 Build and start commands (Docker)

For **Docker** runtime, Render uses:

- **Build**: `docker build` from the Docker Context, using the Dockerfile you set. No extra build command needed.
- **Start**: The **CMD** in the Dockerfile runs uvicorn. The PropPal Dockerfile is already set to use the **PORT** environment variable (Render sets `PORT=10000`), so no extra config is needed.

## B.7 Create the service and first deploy

1. Click **Create Web Service**.
2. Render will clone the repo, run the Docker build, then start the container. The first build can take **10–20+ minutes** because of `torch` and `sentence-transformers`.
3. Watch the **Logs** tab for errors. If you see **out of memory** during build or start, the free instance is too small; see “If the free tier runs out of memory” below.

## B.8 Get the backend URL and use it in the frontend

1. In the service page, open **Settings** and copy the **URL** (e.g. `https://proppal-backend.onrender.com`).
2. In **Environment**, add/update:
   - `ALLOWED_ORIGINS`: include this URL and your Vercel frontend URL (e.g. `https://your-app.vercel.app,https://proppal-backend.onrender.com`).
3. In your **Vercel** frontend app, set the API base URL to this Render URL (e.g. `NEXT_PUBLIC_API_URL=https://proppal-backend.onrender.com`), then redeploy the frontend.

## B.9 Free tier: spin-down and cold starts

- Render free tier **spins down** the service after about **15 minutes** of no requests.
- The next request will trigger a **cold start** (restart); with a heavy stack it can take **1–3+ minutes** before the first response.
- This is normal on the free tier.

---

## If the free tier runs out of memory

- **During build**: Build fails with “Killed” or “out of memory.”  
  - Reduce image size: use a multi-stage Docker build that only installs runtime deps and copies in a pre-built wheel for `torch` if possible, or remove `torch`/`sentence-transformers` from the Render deploy and use a “lite” backend that calls an external API for embeddings.
- **During start**: Service repeatedly restarts or crashes.  
  - Free instance is 512 MB; your app may need 1 GB+. Options: deploy a **lite** backend (no local ML) on Render and use external APIs for AI, or upgrade to a paid plan (e.g. 512 MB–1 GB) for a few dollars/month.

---

## Checklist before deploy

- [ ] Part A: `dev` merged into `main`, `main` pushed.
- [ ] GitHub connected to Render; repo and branch `main` selected.
- [ ] Root Directory / Dockerfile Path / Docker Context set so Docker build runs from `apps/backend`.
- [ ] All environment variables set in Render (no secrets in the repo).
- [ ] App listens on `PORT` (Render sets 10000); Dockerfile or start command uses `PORT`.
- [ ] After first deploy: backend URL added to `ALLOWED_ORIGINS` and to frontend API URL (e.g. Vercel env).

---

## Quick reference: Render fields (PropPal repo root = GitHub repo root)

| Field | Value |
|--------|--------|
| Name | `proppal-backend` |
| Branch | `main` |
| Root Directory | *(blank)* |
| Runtime | Docker |
| Dockerfile Path | `apps/backend/Dockerfile` |
| Docker Context | `apps/backend` |
| Plan | Free |
| Env vars | As in table in B.5; add `PORT` if your CMD doesn’t use it. |

You’re done. After the first successful deploy, use the Render URL in the frontend and in Clerk if you use backend auth webhooks.
