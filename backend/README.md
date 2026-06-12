# LexAi Backend

Backend-only FastAPI deployment repo for the public LexAi recruiter demo.

## Structure

- `index.py`: Vercel/Python entrypoint exposing `app`
- `app/`: FastAPI application modules
- `requirements.txt`
- `.python-version`
- `.env.example`

## Supported Routes

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
- `GET /quota`
- `GET /healthz`
- `GET /health`

## Phase 1 OCR Behavior

- small text-based PDFs can be parsed
- scanned/image-based PDFs return an honest OCR-unavailable message
- image OCR returns an honest unavailable message

## Environment Variables

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
ANON_QUOTA_DAY=25000
```

For Vercel serverless deployments, a Supabase transaction/pooler-style Postgres connection string is recommended over a direct long-lived database host connection.
If DeepL returns `403`, verify that the Vercel project is using the correct endpoint for the deployed key:

- DeepL Free keys usually require `https://api-free.deepl.com/v2/translate`
- DeepL Pro keys use `https://api.deepl.com/v2/translate`

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn index:app --reload
```

## Vercel

- Framework Preset: `Other`
- Root Directory: repo root
- No `vercel.json` required for the first deployment attempt
- Python entrypoint: `index.py`

## Health Check

After deploy:

```text
https://your-backend-project.vercel.app/healthz
```
