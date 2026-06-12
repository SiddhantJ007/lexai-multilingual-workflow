# Deployment Notes

This project was moved to Vercel so the public demo could be used without needing to run anything locally or depend on the old Amplify and EC2 setup. The goal was a cleaner deployment story: one static frontend, one FastAPI backend, both easy to redeploy, and both separated from the original private infrastructure.

## Why Vercel

Vercel was the practical choice for this public version for a few reasons:

- it is fast to deploy and easy to keep updated from GitHub
- static frontend hosting is simple and reliable
- the backend can run as a Python serverless function without keeping the old EC2 machine alive
- it is easy to share one public URL with recruiters

## Live Setup

- Frontend: static Vercel project from `lexai-frontend-vercel/`
- Backend: Python Vercel project from `lexai-backend/`
- Database: Supabase / Postgres-compatible database for feedback persistence

## Frontend Build Command

The frontend is static HTML, CSS, and vanilla JavaScript, so there is no build step.

- Framework Preset: `Other`
- Build Command: leave empty
- Output Directory: default / root
- Root Directory: `lexai-frontend-vercel`

The frontend reads the backend URL from:

- [`lexai-frontend-vercel/config.js`](../lexai-frontend-vercel/config.js)

Example:

```js
window.LEXAI_API_BASE = "https://lexai-backend-vercel.vercel.app";
```

## Backend Serverless Function Structure

The backend is a FastAPI app deployed as a Python serverless function on Vercel.

Key files:

- [`lexai-backend/index.py`](../lexai-backend/index.py)
- [`lexai-backend/app/main.py`](../lexai-backend/app/main.py)

`index.py` exposes the FastAPI app object:

```python
from app.main import app
```

That keeps the Vercel entrypoint simple and lets the actual application logic stay inside `app/main.py`.

## Environment Variables

Backend variables used in production:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
ALLOWED_MODELS=gpt-4.1-mini,gpt-4o-mini,gpt-4o
DEEPL_API_KEY=your_deepl_api_key
DEEPL_API_URL=https://api-free.deepl.com/v2/translate
DATABASE_URL=postgresql://user:password@host:5432/database
SUPABASE_DB_URL=postgresql://user:password@host:5432/database
FRONTEND_ORIGIN=https://lexai-frontend-vercel.vercel.app
CORS_ALLOWED_ORIGINS=https://lexai-frontend-vercel.vercel.app,http://127.0.0.1:5500,http://localhost:5500
ANON_QUOTA_DAY=10000
```

Notes:

- set either `DATABASE_URL` or `SUPABASE_DB_URL`
- for DeepL, make sure the key matches the correct endpoint:
  - Free: `https://api-free.deepl.com/v2/translate`
  - Pro: `https://api.deepl.com/v2/translate`

Frontend variables:

- no secret env vars are required for the static frontend
- only the public backend URL is stored in `config.js`

## Known Limitations

- OCR is intentionally limited in the public deployment
- text-based PDFs can work, but scanned PDF OCR and image OCR are not enabled in this Phase 1 setup
- Vercel serverless is fine for short requests, but it is not a great fit for heavy native OCR or long-running background work
- feedback persistence depends on the database being reachable from the serverless runtime
- the public demo is session-scoped, not full account-based multi-user product infrastructure

## Cold Start Note

Because the backend runs on serverless infrastructure, the first request after some idle time can feel slower than the next few requests. That is normal. It does not usually mean the app is broken. The most useful quick check is:

```text
https://lexai-backend-vercel.vercel.app/healthz
```

If that responds, the backend is up and the slower response is likely just a cold start.

## How To Redeploy

Frontend:

1. Push changes to the branch connected to the Vercel project.
2. Vercel will usually start a new deployment automatically.
3. If needed, open the Vercel dashboard for the frontend project and click `Redeploy`.

Backend:

1. Push changes to the branch connected to the Vercel project.
2. Confirm backend environment variables are still present.
3. Let Vercel build a new deployment or trigger `Redeploy` from the dashboard.
4. Test `/healthz` before checking the frontend flow.

Practical deploy order:

1. Deploy backend first
2. Verify backend health
3. Deploy frontend if the public URL or UI changed

## How To Debug Deployment Failures

If a deployment fails, check these in order:

1. Vercel build logs
2. Vercel runtime logs
3. `GET /healthz`
4. browser network tab on the frontend

Common failure patterns:

- `DeepL request failed`
  - usually a key or endpoint mismatch
- CORS errors in the browser
  - often caused by a real backend failure underneath, or by missing frontend origin values in backend env vars
- database connection errors
  - check `DATABASE_URL` / `SUPABASE_DB_URL`
  - use a Supabase pooler / serverless-friendly Postgres connection string
- `Failed to fetch`
  - inspect the actual backend response and Vercel logs before assuming it is only CORS
- Python import or startup failures
  - confirm `index.py` still exposes `app`
  - confirm runtime dependencies are listed in `lexai-backend/requirements.txt`

Useful checks after deploy:

```text
https://lexai-backend-vercel.vercel.app/healthz
https://lexai-frontend-vercel.vercel.app
```

If the backend is healthy but the UI still fails, the next place to look is usually the frontend network tab and the backend request logs for the matching route.
