# Security and Privacy Notes

This public repo was prepared as a portfolio demo, so security and privacy mattered a lot during sanitization.

## What is not in this repo

- no production API keys
- no committed `.env` files
- no live client credentials
- no private AWS, EC2, or old deployment secrets
- no real customer or client data

Only placeholder configuration is included where needed.

## Environment variables

Secrets are expected to be provided through environment variables, not hardcoded into the repo.

Example templates are included through `.env.example` files so the expected variables are clear without exposing anything sensitive.

That applies in particular to:

- OpenAI API keys
- DeepL API keys
- database connection strings
- frontend/backend origin settings

## Sanitized public demo

The public demo is meant to show the workflow, not expose real business activity.

- real client data was removed
- private branding and business-specific content were removed
- the live demo uses sanitized inputs and sanitized public-facing copy

If someone explores the deployed version, they should be seeing the product workflow, not confidential project history.

## API key handling

The app is structured so API keys live in the backend environment and are never meant to be exposed in frontend code.

The static frontend only points to the backend URL. The backend is responsible for using provider credentials securely through environment configuration.

## Abuse and rate-limit considerations

Because this is an AI-powered public demo, abuse control matters even in a portfolio version.

Current protections are intentionally lightweight, but they are not ignored:

- session-scoped usage tracking is used for the public workflow
- request volume is constrained through a daily quota
- file uploads are limited in size
- unsupported OCR paths return honest errors instead of attempting unsafe fallbacks

This is not a full production abuse-prevention system. If the project were extended further, the next security-focused improvements would likely be:

- stronger per-IP or per-session rate limiting
- stricter bot and abuse detection
- more structured monitoring and alerting
- tighter request validation and provider usage controls

## Practical takeaway

This repo is intentionally public-friendly:

- secrets stay out of source control
- sensitive data was removed
- deployment config is environment-driven
- the demo remains real without exposing private infrastructure
