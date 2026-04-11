# Vercel Deployment

This repo is now prepared for a single Vercel project using `Services`:

- one Vercel project
- project root directory: repository root
- `apps/web` is the Next.js frontend service
- `apps/api/main.py` is the FastAPI backend service entrypoint
- the backend is mounted at `/api`

## Deployment Shape

The deployed app should be configured as a single Git-linked Vercel project:

- repository: `architworks/rfq_automation_system`
- production branch: `prod`
- root directory: repository root
- framework preset: `Services`

## How The Services Setup Works

### Frontend service

- `apps/web` remains the Next.js app
- the browser still calls the same public backend paths such as:
  - `/sessions`
  - `/sessions/{session_id}`
  - `/sessions/{session_id}/rubric/generate`
- production rewrites in `apps/web/next.config.ts` continue to map those browser-facing paths to `/api/...`

### Backend service

- `apps/api/main.py` is the Vercel service entrypoint
- it adds `apps/api/src` to `sys.path`
- it imports the existing FastAPI application from `rfq_api.main`
- Vercel mounts the backend service at `/api`

### Root config

- the repo root `vercel.json` defines:
  - `web` -> `apps/web` at `/`
  - `api` -> `apps/api/main.py` at `/api`

## Files Used For This Setup

- `vercel.json`
  - root Services config
- `apps/api/main.py`
  - FastAPI service entrypoint for Vercel
- `apps/web/next.config.ts`
  - keeps local-dev rewrites to the standalone FastAPI server
  - keeps production rewrites from `/sessions...` to `/api/sessions...`

## Environment Variables

Set these on the single Vercel project.

### Required

- `FRONTEND_ORIGIN`
  - set this to the production frontend URL
- `SESSION_TTL_SECONDS`
  - `7200`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_MODEL`
- `AZURE_OPENAI_TIMEOUT_SECONDS`
  - `300`

### Optional

- `NEXT_PUBLIC_API_BASE_URL`
  - normally leave unset
  - only set this if the frontend should call an external backend instead of same-origin routes
- `LOCAL_API_ORIGIN`
  - optional for local Next.js development
  - default is `http://127.0.0.1:8000`

## Required Vercel Dashboard Settings

Update the existing Vercel project to:

- root directory: repository root
- framework preset: `Services`

The previous `apps/web` root-directory setup is no longer valid for deployment.

## Local Development

Local development does not change:

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

## Follow-Up For True Production Readiness

To make this architecture reliable on Vercel later, replace process-local state with durable external systems:

- database or remote cache for session state
- object storage for uploaded vendor documents
- durable storage for extracted artifacts and locked framework outputs
