# Next Steps After Backend on Render

Your backend is live at **https://proppal.onrender.com**. Follow these steps to go fully live with the frontend and CORS/auth.

---

## 1. Deploy the frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in (GitHub).
2. **Add New** → **Project** → import the same repo (**bilalrana8718/PropPal**).
3. **Before deploying**, set these so the build does not fail:
   - **Root Directory:** click **Edit** and set to **`apps/web`** (required so Vercel builds only the Next.js app, not the whole monorepo/turbo).
   - **Framework Preset:** Next.js (auto-detected).
   - **Build Command:** leave default **`npm run build`** (runs `next build` in `apps/web`).
   - **Output Directory:** leave default.
4. **Environment Variables** (add before first deploy; required for build and runtime):
   - **`NEXT_PUBLIC_API_URL`** = **`https://proppal.onrender.com`** (no trailing slash).  
     If this is missing, the build will fail with "NEXT_PUBLIC_API_URL environment variable is not set".
   - Copy all other **`NEXT_PUBLIC_*`** from your `apps/web/.env.local` (Clerk keys, sign-in URLs, etc.).
5. Click **Deploy**. Note the Vercel URL (e.g. `https://proppal-xxx.vercel.app`).

**If the build still fails:** check the **full** error in the build logs (scroll to the bottom). Common causes: Root Directory not set to `apps/web`, or a missing `NEXT_PUBLIC_*` env var.

---

## 2. Allow the frontend in the backend (CORS)

1. Open [Render Dashboard](https://dashboard.render.com) → your **PropPal** service → **Environment**.
2. Edit **ALLOWED_ORIGINS** and add your Vercel URL, comma-separated, for example:
   ```text
   https://proppal.onrender.com,https://proppal-xxx.vercel.app
   ```
   Or if you already have values:
   ```text
   https://proppal-xxx.vercel.app,https://proppal.onrender.com
   ```
3. Save. Render will redeploy with the new env (or do a manual redeploy if needed).

---

## 3. Clerk (auth)

- If you keep using **Clerk test/dev** keys: ensure in Clerk Dashboard the allowed origins include your Vercel URL (e.g. `https://proppal-xxx.vercel.app`).
- If you add **Clerk webhooks** (e.g. user sync): set the webhook URL to `https://proppal.onrender.com/api/auth/webhook` (or your actual webhook path) and use the same `CLERK_WEBHOOK_SECRET` you set on Render.
- When you move to **production Clerk**: create a production instance, swap keys in Vercel and Render, and update allowed origins again.

---

## 4. Test the full flow

1. Open your Vercel URL (e.g. `https://proppal-xxx.vercel.app`).
2. Sign in with Clerk.
3. Try: dashboard, property search, chat, create listing, etc. Each of these calls `NEXT_PUBLIC_API_URL` (your Render backend).
4. If something fails: check browser Network tab (CORS errors = add Vercel URL to ALLOWED_ORIGINS); check Render Logs for 5xx or auth errors.

---

## 5. Optional improvements

- **Custom domain:** In Vercel, add your domain and (if you want) point the backend subdomain to Render or keep API at `https://proppal.onrender.com`.
- **Health check:** If Render’s default health check causes noise (e.g. HEAD / 405), you can add a GET `/health` route on the backend and point Render’s health check URL to it.
- **Cold starts:** On Render free tier the backend sleeps after ~15 min; first request after that can take 1–3 minutes. Consider a paid instance or a “lite” backend if that’s a problem.

---

## Checklist

- [ ] Frontend deployed on Vercel (`apps/web` as root).
- [ ] `NEXT_PUBLIC_API_URL=https://proppal.onrender.com` set in Vercel.
- [ ] Vercel URL added to backend **ALLOWED_ORIGINS** on Render.
- [ ] Clerk allowed origins include Vercel URL (and webhook URL if used).
- [ ] Full flow tested (sign-in, API calls from frontend to backend).
