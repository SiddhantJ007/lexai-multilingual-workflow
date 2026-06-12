# LexAi Frontend

Static frontend-only Vercel deployment for the public LexAi live demo.

## What this frontend is

This repo contains the public recruiter-facing frontend for LexAi:

- `index.html`: landing page
- `trans.html`: multilingual translation and rewrite workflow
- `emails-demo.html`: email drafting demo
- `script.js`: frontend logic for the translation workflow
- `config.js`: deployed backend URL
- `config.example.js`: placeholder backend URL template

## Backend URL used

Production backend:

```js
window.LEXAI_API_BASE = "https://lexai-backend-vercel.vercel.app";
```

## Sanitization note

Sanitized live demo. Private keys, client data, and original deployment details have been removed.

## Local run

```bash
python3 -m http.server 5500
```

Then open:

- `http://127.0.0.1:5500/index.html`
- `http://127.0.0.1:5500/trans.html`
- `http://127.0.0.1:5500/emails-demo.html`

## Vercel deploy settings

- Framework Preset: `Other`
- Build Command: empty
- Output Directory: default / empty
- Root Directory: blank

## QA checklist

- landing page loads
- landing page links to `trans.html` and `emails-demo.html`
- translation page shows backend status
- translation page can translate
- translation page can rephrase
- translation page shows backend errors clearly when unavailable
- feedback save/list/download/clear works
- regeneration works
- email demo shows backend status
- email demo generates five outputs
- no mock or fake fallback content appears when backend is unavailable
