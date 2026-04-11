# RFQ Prototype Web

Next.js frontend for phase 1 of the RFQ prototype.

## Responsibilities

- bootstrap or rehydrate the browser session
- render the seeded RFQ input form
- call FastAPI to generate the AI rubric proposal
- allow buyer-side edits to the proposal
- surface validation issues on lock
- download the locked artifact JSON

## Setup

Prerequisites:

- `pnpm`
- Node.js 20+

Install dependencies from the repo root:

```bash
pnpm install
```

Copy the example env file:

```bash
cp .env.example .env.local
```

## Run

```bash
pnpm dev
```

Open `http://localhost:3000`.

In local development, the Next.js app rewrites `/sessions...` requests to the FastAPI server at `http://127.0.0.1:8000` by default.

## Verify

```bash
pnpm lint
pnpm test
pnpm build
```

## Environment Variables

- `NEXT_PUBLIC_API_BASE_URL`: optional explicit backend base URL override
- `LOCAL_API_ORIGIN`: optional local rewrite target for development, default `http://127.0.0.1:8000`

## Vercel

This app is prepared for a single-project Vercel deployment using mixed Next.js and Python runtimes:

- Vercel project root: `apps/web`
- Python entrypoint: `apps/web/api/index.py`
- FastAPI source imported from `apps/api/src`

See `docs/VERCEL_DEPLOYMENT.md` for the deployment shape and project settings.

## Test Coverage

Current component tests cover:

- seeded RFQ load
- RFQ edit persistence across navigation and refresh in the same session
- generation error retry behavior without losing RFQ input
- field-level lock validation error rendering
