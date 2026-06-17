# LexAi

LexAi is a sanitized public portfolio project that demonstrates a real AI-assisted multilingual content workflow. The public deployment target in Phase 1 is:

- static frontend on Vercel from `frontend/`
- FastAPI backend on Vercel from `backend/`
- Supabase/Postgres-compatible feedback storage

No fake or mock API responses are used in the supported public flows.

## Live Demo

- Frontend demo: `https://lexai-frontend-vercel.vercel.app`
- Backend health check: `https://lexai-backend-vercel.vercel.app/healthz`

<a href="https://www.loom.com/share/db24befd8f5b426d859e3fad80348a90">
  <img src="docs/assets/lexai/loom.png" alt="Watch the LexAi demo walkthrough on Loom" width="520">
</a>

## Demo Walkthrough

- Full walkthrough notes: [`docs/WALKTHROUGH.md`](docs/WALKTHROUGH.md)

## Screenshots

<table>
  <tr>
    <td width="50%">
      <img src="docs/assets/lexai/translation.png" alt="LexAi translation workflow page" width="100%">
    </td>
    <td width="50%">
      <img src="docs/assets/lexai/regeneration.png" alt="LexAi critique and regenerate prompt flow" width="100%">
    </td>
  </tr>
  <tr>
    <td width="50%">
      <img src="docs/assets/lexai/emails-tool.png" alt="LexAi email drafting demo" width="100%">
    </td>
    <td width="50%">
      <img src="docs/assets/lexai/alternatives.png" alt="LexAi alternative output generation and rating flow" width="100%">
    </td>
  </tr>
</table>

## Project Evolution

LexAi started as a multilingual AI content workflow built around a real product need: helping users generate, translate, refine, and export content without manually moving between multiple tools. The early version included login and signup flows so user activity and usage could be tracked through accounts.

After testing the workflow, the requirement changed: users were less likely to try the tool if they had to create an account first. I redesigned the flow to remove the login barrier while still keeping user sessions separated. The updated approach used browser-side session tracking so each browser session could keep its own usage state, history, and token limits without mixing data across users.

The translation workflow also evolved through feedback. A “good” response could generate alternative variants, while a “bad” response asked for feedback and resent that context into the AI flow for regeneration. The goal was not just to translate text once, but to create an iterative content workflow where users could improve outputs, compare variants, reuse feedback, and export structured results.

This public version keeps the core workflow and removes private branding, deployment details, credentials, and third-party business context. It is intended to show the product and engineering decisions behind the prototype: simplifying user access, preserving session isolation, building feedback loops, supporting OCR/file input, and making AI outputs easier to review and export.

## In Plain English

LexAi solves a fairly common workflow problem: translating and refining short-form content usually means bouncing between multiple tools, losing context, and manually tracking which version was actually better. This project brings that loop into one place.

The user is someone who needs to generate or improve multilingual copy quickly, review alternatives, give feedback on weak results, and keep a usable record of what worked. In practice that could be a marketer, founder, operator, or anyone working on product or promotional text.

The app takes source text, improves it in English when needed, translates it, lets the user rate the result, generates alternatives after a good result, and runs a critique-and-regenerate loop after a bad result. It also keeps session-scoped history so those results can be reviewed and exported later.

## Key features
## Supported In The Public Demo

- multilingual translation via `POST /full-process/`
- English rewrite via `POST /rephrase/`
- alternative output generation via `POST /copy-variants/`
- feedback save/list/clear/download
- critique-driven regeneration via `POST /feedback/regenerate`
- email generation via `POST /api/generate-emails`
- text-based PDF extraction for small PDFs under the Vercel-safe limit

## Phase 1 OCR Limitation

- `POST /upload-image/` does not perform OCR in the Vercel deployment
- scanned PDF OCR is not enabled in Phase 1
- the app returns an honest message instead of inventing OCR text

This keeps the deployment real while avoiding unsupported native OCR assumptions on Vercel Functions.

## Architecture

- Frontend: static HTML/CSS/vanilla JS in [`frontend/`](frontend)
- Backend: FastAPI in [`backend/app/main.py`](backend/app/main.py)
- Backend Vercel entry: [`backend/api/index.py`](backend/api/index.py)
- Feedback persistence: Postgres-compatible table accessed through [`backend/app/db.py`](backend/app/db.py)
- AI providers:
  - OpenAI for rewrite, translation fallback, regeneration, variants, and email generation
  - DeepL for translation when configured

## Testing

A lightweight testing and CI setup is included so the project is not treated as “push and hope.”

- Testing notes: [`docs/TESTING.md`](docs/TESTING.md)
- Deployment notes: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- Security and privacy notes: [`SECURITY.md`](SECURITY.md)

## What Was Removed Or Sanitized

- old Amplify/EC2 deployment assumptions
- private domains and business-specific branding
- local SQLite persistence as the deployment database
- native Tesseract-based OCR requirement in the public cloud deployment
- old login/signup/marketing/product surfaces not needed for the portfolio demo

## Environment Variables

Backend environment variables:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
ALLOWED_MODELS=gpt-4.1-mini,gpt-4o-mini,gpt-4o
DEEPL_API_KEY=your_optional_deepl_api_key
DEEPL_API_URL=https://api-free.deepl.com/v2/translate
DATABASE_URL=postgresql://user:password@host:5432/database
SUPABASE_DB_URL=postgresql://user:password@host:5432/database
FRONTEND_ORIGIN=https://your-frontend-project.vercel.app
CORS_ALLOWED_ORIGINS=https://your-frontend-project.vercel.app,http://127.0.0.1:5500,http://localhost:5500
```

Frontend runtime config:

```js
window.LEXAI_API_BASE = "https://your-backend-project.vercel.app";
```

Use [`frontend/config.example.js`](frontend/config.example.js) as the template and update [`frontend/config.js`](frontend/config.js).

## Database Schema

Run this in Supabase SQL editor or another Postgres-compatible database:

- Add automated tests around the FastAPI routes
- Add stronger validation and structured error handling in the frontend
- Replace prompt-based JSON parsing with stricter schema-based responses where appropriate
- Add a proper local development config for frontend API base URLs
- Add a small seed dataset or screenshots for portfolio presentation without requiring API keys

## Running Notes

The frontend is designed to run against the local FastAPI backend. The public repo does not include production deployment settings, API keys, or the original hosted environment. To test live AI calls, create a local `.env` file from `.env.example`, add valid API keys, start the backend with Uvicorn, and then serve the frontend locally.

Without API keys, the frontend and backend code can still be reviewed to understand the workflow structure, request flow, prompt/regeneration logic, OCR path, feedback handling, and CSV export behavior.
```sql
create table if not exists feedbacks (
  id bigserial primary key,
  session_id text not null,
  original_prompt text not null,
  translated_text text not null,
  target_language text not null,
  feedback text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_feedbacks_session_created
on feedbacks (session_id, created_at desc);
```

The backend also attempts `CREATE TABLE IF NOT EXISTS` on startup when database credentials allow it.

## Local Development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

### Frontend

Update `frontend/config.js` with your local backend URL if needed:

```js
window.LEXAI_API_BASE = "http://127.0.0.1:8000";
```

Then serve the frontend:

```bash
cd frontend
python3 -m http.server 5500
```

Open:

- `http://127.0.0.1:5500/index.html`
- `http://127.0.0.1:5500/trans.html`
- `http://127.0.0.1:5500/emails-demo.html`

## Vercel Deployment

### Backend Vercel project

1. Import this repo into Vercel.
2. Create a project with Root Directory set to `backend`.
3. Add backend environment variables listed above.
4. Deploy.
5. Verify:
   - `/healthz`
   - `/health`

### Frontend Vercel project

1. Create a second Vercel project from the same repo.
2. Set Root Directory to `frontend`.
3. Update `frontend/config.js` so `window.LEXAI_API_BASE` points at the deployed backend URL.
4. Deploy.

## Manual Test Checklist

Backend:

- `GET /healthz`
- `GET /health`
- `POST /full-process/`
- `POST /rephrase/`
- `POST /copy-variants/`
- `POST /feedback/`
- `POST /variant-feedback/`
- `GET /feedbacks/`
- `DELETE /feedbacks/clear`
- `GET /feedbacks/download`
- `POST /feedback/regenerate`
- `POST /api/generate-emails`

Uploads:

- upload a small text-based PDF under 4 MB
- upload an image and confirm the app returns the honest OCR-unavailable message
- upload a scanned PDF and confirm the app returns the honest OCR limitation message

Frontend:

- backend health indicator becomes connected
- translation result renders
- rewrite result renders
- good feedback saves
- variants generate after good feedback
- bad feedback triggers regeneration
- CSV download works
- email generation returns five methods

## Notes

- The frontend does not fake backend success if the backend is unreachable.
- Feedback persistence is no longer local filesystem state.
- This Phase 1 deployment is intentionally minimal and real, not a mock showcase.
