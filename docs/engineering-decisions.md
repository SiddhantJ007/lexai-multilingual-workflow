# Engineering Decisions

This document is a short record of the main engineering decisions behind the public LexAi portfolio version. It is not meant to read like a formal ADR system. The point is simpler: show how the project changed, why those choices were made, and what tradeoffs came with them.

## Decision 1: Use Vercel for the live demo

Problem:
To show recruiters a working demo, not just a source repo that only made sense when run locally.

Options considered:
Vercel, Netlify, Render, Railway, or leaving the demo as local-only.

Choice:
Vercel.

Reason:
It gave the cleanest path to a public frontend and a working backend without reviving the old private infrastructure. It was also straightforward to connect to GitHub and redeploy quickly.

Tradeoff:
Serverless cold starts and tighter runtime limits than a persistent backend service.

Future improvement:
If usage grows or longer-running tasks become important, move the backend to a persistent service with more predictable runtime behavior.

## Decision 2: Split the live demo into separate frontend and backend deployments

Problem:
The original project structure and earlier monorepo deployment attempts created unnecessary friction, especially around Vercel backend entrypoints.

Options considered:
One monorepo-style Vercel setup, one combined app deployment, or separate deployable frontend and backend projects.

Choice:
Separate frontend and backend deployments.

Reason:
It made the deployment story easier to reason about. The frontend could stay static, while the backend could be treated as its own FastAPI deployment with its own environment variables and logs.

Tradeoff:
Two deployments means two dashboards, two sets of settings, and one extra point of coordination.

Future improvement:
If the repo is restructured later, a cleaner shared monorepo deployment pattern could be reconsidered.

## Decision 3: Keep the public repo focused on the workflow, not the original business website

Problem:
The older version included landing pages, auth flows, marketing surfaces, business branding, and other content that did not belong in a public portfolio repo.

Options considered:
Publish the full older site, heavily redact the full site, or extract only the workflow that demonstrates the core product logic.

Choice:
Keep only the workflow-focused public demo.

Reason:
That made the repo cleaner, more honest, and easier for a recruiter to understand. It also reduced the risk of exposing branding, private context, and irrelevant business pages.

Tradeoff:
Some original product context was removed, including parts of the broader user journey.

Future improvement:
Add screenshots or a short product walkthrough if more narrative context is needed without restoring private surfaces.

## Decision 4: Preserve real API behavior instead of mocking the demo

Problem:
A portfolio demo can look polished while secretly using fake responses, but that weakens the credibility of the project.

Options considered:
Mock responses, partially mock unsupported flows, or keep the supported public flows real.

Choice:
Keep the supported flows real.

Reason:
The translation, rewriting, feedback, regeneration, and export paths were important enough that they needed to actually work.

Tradeoff:
Real deployments are more fragile than mock demos because external services, environment variables, and rate limits can fail.

Future improvement:
Add deeper automated monitoring and safer operational fallbacks without turning the product into a fake demo.

## Decision 5: Keep OCR honest instead of pretending unsupported OCR works

Problem:
The older project used OCR paths that were not a good fit for the Vercel serverless environment, especially anything depending on native Tesseract.

Options considered:
Fake OCR output, keep broken OCR routes, remove OCR entirely, or keep only what was safe and explicitly reject unsupported paths.

Choice:
Support small text-based PDF extraction and return honest unavailable messages for image OCR and scanned-PDF OCR.

Reason:
That preserved the shape of the workflow without lying about what the public deployment can really do.

Tradeoff:
The public demo is less feature-complete than the older local or private version.

Future improvement:
Integrate an external OCR or vision service that fits a serverless environment better.

## Decision 6: Replace local SQLite feedback storage with Postgres-compatible storage

Problem:
Local SQLite and filesystem persistence are not reliable for a public serverless deployment.

Options considered:
Keep SQLite, disable persistence, or move to a network database.

Choice:
Use Supabase / Postgres-compatible storage.

Reason:
Feedback history, exports, and session-scoped records needed to survive across requests. A database service was the most practical way to preserve that behavior.

Tradeoff:
The app now depends on external database connectivity and environment setup.

Future improvement:
Add migrations and stronger schema management beyond startup-time table creation.

## Decision 7: Keep session isolation without restoring full account-based auth

Problem:
The earlier product had login and signup, but the public portfolio version needed a lower-friction entry point.

Options considered:
Require auth, remove user separation entirely, or keep lightweight browser-session separation.

Choice:
Use browser-session-based isolation for the public demo.

Reason:
This kept the experience simple while still separating feedback history and quota usage per session.

Tradeoff:
It is not the same as a full authenticated multi-user product.

Future improvement:
If needed, document the original auth model separately rather than rebuilding it into the public demo.

## Decision 8: Keep DeepL as the main translation layer with OpenAI as the intelligence layer

Problem:
The app was not meant to be a generic direct-OpenAI translation demo. The stronger version of the workflow used OpenAI to refine and interpret user intent around a DeepL-centered translation path.

Options considered:
OpenAI-only translation, DeepL-only translation, or the original hybrid flow.

Choice:
Restore the hybrid flow.

Reason:
That was closer to how the original product actually behaved and better matched the workflow being presented publicly.

Tradeoff:
The integration became more operationally sensitive because it depends on two external providers instead of one.

Future improvement:
Add more explicit provider-level health checks and clearer provider-specific error handling.

## Decision 9: Use environment-driven configuration for secrets, origins, and provider settings

Problem:
The original private deployment assumptions could not be carried into a public repo safely.

Options considered:
Hardcode deployment settings, keep private config files, or move runtime settings into environment variables and examples.

Choice:
Use environment variables with placeholder examples only.

Reason:
That was necessary for a safe public repo and also made Vercel deployment more portable.

Tradeoff:
Misconfigured environments are now one of the main failure modes.

Future improvement:
Add a startup self-check or admin diagnostics page for faster configuration debugging.

## Decision 10: Harden backend startup so database issues do not crash the whole app

Problem:
A failing database connection during startup caused the backend to crash entirely in serverless deployment.

Options considered:
Fail hard on startup, ignore the database entirely, or keep the app alive while degrading feedback-dependent routes.

Choice:
Keep the app alive and degrade gracefully.

Reason:
Health endpoints and non-database-dependent routes should still be reachable even if the database is temporarily unavailable.

Tradeoff:
The app can be partially healthy instead of simply failing fast.

Future improvement:
Add structured health diagnostics and better operational alerts around degraded backend state.

## Decision 11: Keep the feedback loop and export flow in the public demo

Problem:
A simple translate-once demo would be easier to ship, but it would not show the more interesting product logic.

Options considered:
Reduce the demo to translation only, or keep the feedback, variants, regeneration, and export loop.

Choice:
Keep the loop.

Reason:
That workflow is one of the stronger signals in the project. It shows product thinking, not just API wiring.

Tradeoff:
It adds more moving parts to both the backend and frontend.

Future improvement:
Make the feedback table, filters, and export flows more robust and more explicitly test-covered.

## Decision 12: Add lightweight CI and testing instead of claiming quality without proof

Problem:
A public repo can say it is production-minded, but without tests or CI that claim is weak.

Options considered:
No CI, a very heavy CI pipeline, or a simple baseline workflow.

Choice:
Add a lightweight baseline workflow.

Reason:
Install, lint, run backend tests, and run a frontend smoke check is enough to show that changes are checked automatically.

Tradeoff:
Coverage is still limited, especially on the frontend.

Future improvement:
Add more route-level tests, stronger regression coverage, and possibly browser automation for the frontend workflow.

## Decision 13: Document the project like an engineering artifact, not just a code dump

Problem:
Without documentation, a recruiter would have to reverse-engineer the repo to understand what was built and why.

Options considered:
Minimal README only, scattered comments, or a small set of focused documents.

Choice:
Add focused documentation: architecture, deployment, testing, security, and this decision log.

Reason:
That makes the project easier to evaluate and shows how the technical decisions were made under constraints.

Tradeoff:
Documentation needs maintenance as the project changes.

Future improvement:
Keep the docs synced with the actual live deployment and trim anything that becomes outdated.
