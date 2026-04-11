# Vercel Deployment

This repo is now prepared for the Vercel Knowledge Base pattern of using Python and JavaScript in the same application:

- one Vercel project
- project root directory: `apps/web`
- Next.js serves the frontend
- Python serverless functions live under `apps/web/api`
- the Python entrypoint imports the existing FastAPI backend from `apps/api/src`

## Deployment Shape

The deployed app should be configured as a single Git-linked Vercel project:

- repository: `architworks/rfq_automation_system`
- production branch: `prod`
- root directory: `apps/web`
- framework preset: Next.js

## How The Mixed Runtime Setup Works

### Frontend

- `apps/web` remains the Next.js app
- the browser still calls the same public backend paths such as:
  - `/sessions`
  - `/sessions/{session_id}`
  - `/sessions/{session_id}/rubric/generate`

### Python backend

- `apps/web/api/index.py` is the Vercel Python entrypoint
- it adds `apps/api/src` to `sys.path`
- it imports the existing FastAPI application from `rfq_api.main`

### Routing

To avoid changing the frontend API contract, `apps/web/next.config.ts` rewrites requests as follows:

- in local development:
  - `/sessions...` -> `http://127.0.0.1:8000/sessions...`
  - `/healthz` -> `http://127.0.0.1:8000/healthz`
- in deployed environments:
  - `/sessions...` -> `/api/sessions...`
  - `/healthz` -> `/api/healthz`

This keeps the public browser-facing endpoints stable while routing them to Python functions in production.

## Files Added For This Setup

- `apps/web/api/index.py`
  - Python function entrypoint for Vercel
- `apps/web/requirements.txt`
  - Python dependencies for the Vercel Python runtime
- `apps/web/vercel.json`
  - function bundling config so the Python function includes `../api/src/**`

## Required Vercel Project Setting

Because the Vercel project root is `apps/web` but the FastAPI source code lives in `apps/api/src`, the Vercel project should enable monorepo source access:

- `sourceFilesOutsideRootDirectory = true`

This is a Vercel project setting, not a repo file.

## Environment Variables

Set these on the single Vercel project.

### Required

- `FRONTEND_ORIGIN`
  - set this to the production frontend URL for the Vercel project
- `SESSION_TTL_SECONDS`
  - `7200`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_MODEL`
- `AZURE_OPENAI_TIMEOUT_SECONDS`
  - `300`

### Optional

- `NEXT_PUBLIC_API_BASE_URL`
  - normally leave unset for the single-project deployment
  - only set this if you intentionally want the frontend to call some external backend
- `LOCAL_API_ORIGIN`
  - optional for local Next.js development
  - default is `http://127.0.0.1:8000`

## Local Development

The mixed-runtime deployment prep does not change local development responsibilities:

1. run FastAPI separately from `apps/api`
2. run Next.js from `apps/web`
3. Next.js rewrites `/sessions...` to the local Python server automatically in development

## Important Limitation

The current backend is still not production-grade for Vercel serverless execution because it uses:

- in-memory session state
- temp-directory file storage for uploads and derived artifacts

That means:

- the deployment is suitable for demo usage
- session continuity is not guaranteed across cold starts or instance changes
- uploaded files and in-memory state are ephemeral

This limitation exists regardless of whether we deploy as one Vercel project or two.

## Follow-Up For True Production Readiness

To make this architecture reliable on Vercel later, replace process-local state with durable external systems:

- database or remote cache for session state
- object storage for uploaded vendor documents
- durable storage for extracted artifacts and locked framework outputs
