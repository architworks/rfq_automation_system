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

## Verify

```bash
pnpm lint
pnpm test
pnpm build
```

## Environment Variables

- `NEXT_PUBLIC_API_BASE_URL`: FastAPI base URL, default `http://localhost:8000`

## Test Coverage

Current component tests cover:

- seeded RFQ load
- RFQ edit persistence across navigation and refresh in the same session
- generation error retry behavior without losing RFQ input
- field-level lock validation error rendering
