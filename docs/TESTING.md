# Testing Notes

This project does not need a huge test pyramid to make a good impression, but it does need a credible baseline. The goal here is simple: show that the repo is not being shipped blind.

## What Is Covered

At minimum, the current setup covers:

- a frontend smoke test
- backend API tests
- input validation checks
- error handling checks
- one manual end-to-end checklist

## Frontend Smoke Test

The frontend is static HTML, CSS, and vanilla JavaScript, so there is no real build pipeline to unit test in the usual React or TypeScript sense.

Instead, the smoke check verifies that:

- the key public files exist
- `trans.html` loads `config.js`
- `trans.html` loads `script.js`
- the runtime config still exposes `window.LEXAI_API_BASE`
- the frontend still checks backend health

That is handled by:

- [`tools/check_frontend_smoke.py`](../tools/check_frontend_smoke.py)

Run it locally:

```bash
python3 tools/check_frontend_smoke.py
```

## Backend API Test

The backend test suite uses FastAPI’s test client and focuses on a few high-signal checks rather than trying to mock the entire product.

Current coverage includes:

- health endpoint smoke test
- successful `POST /full-process/` path with mocked AI helpers
- request validation failure for invalid input
- feedback route error handling when storage is unavailable
- honest OCR-unavailable response for image upload

Test file:

- [`lexai-backend/tests/test_api.py`](../lexai-backend/tests/test_api.py)

Run locally:

```bash
cd lexai-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## Input Validation Test

Input validation is covered through FastAPI request-model enforcement. A simple example already in the suite checks that an empty `prompt` sent to `POST /full-process/` returns a validation error instead of being processed.

That matters because the public demo should fail in predictable ways, not in confusing or partially successful ways.

## Error Handling Test

The current backend tests also cover one useful failure path: feedback history access when storage is unavailable.

Instead of letting that turn into a stack trace or generic crash, the route should return a clear `503` response. That is the kind of behavior recruiters usually will not inspect directly, but it reflects whether the app was built with operational discipline.

## End-To-End Manual Checklist

This is the fastest realistic manual pass after a deploy:

1. Open the frontend landing page.
2. Open the translation workflow.
3. Confirm the backend status indicator becomes connected.
4. Submit a translation request.
5. Confirm the spinner appears and the result scrolls into view.
6. Click `Good` and confirm feedback saves.
7. Generate 5 alternatives and confirm the spinner appears.
8. Rate one alternative and confirm it appears in feedback history.
9. Click `Bad` on the main result, enter critique, and confirm regeneration completes.
10. Download the feedback export and confirm the saved rows are present.
11. Upload a small text-based PDF and confirm text extraction works.
12. Upload an image and confirm the app returns the honest OCR-unavailable message.

## CI Baseline

GitHub Actions is used as a lightweight CI check. It does not try to be fancy. It simply proves that the repository can:

- install dependencies
- lint the backend Python code
- run backend tests
- run a frontend smoke check

There is no separate type-check step right now because the project does not currently use TypeScript or a static Python typing workflow.

That is still enough to communicate something important: changes are checked automatically before they are treated as trustworthy.
