# RFQ Prototype

Documentation and assignment/reference material live under `docs/`. Start with `docs/DOC_MAP.md` for the product documentation set.

Phase 1 implements the seeded RFQ to locked-rubric flow:

- buyer starts from the sample 8-item RFQ
- buyer edits the RFQ draft
- backend generates an AI rubric proposal
- buyer edits the proposal
- buyer locks the framework and downloads a JSON artifact

## Stack

- `apps/web`: Next.js App Router, TypeScript
- `apps/api`: FastAPI, Pydantic v2
- browser session state: `sessionStorage`
- backend session state: in-memory TTL store, no database
- AI integration: Azure-hosted OpenAI model via the OpenAI Python SDK `OpenAI` client
- rubric generation uses the Responses API with Structured Outputs bound to the `RubricProposal` Pydantic schema

## Local Run

Prerequisites:

- `pnpm`
- `uv`
- Python 3.12+
- Node.js 20+

Install dependencies:

```bash
pnpm install
cd apps/api && uv sync
```

Set environment files:

```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
```

Start the API:

```bash
cd apps/api
uv run uvicorn rfq_api.main:app --app-dir src --reload
```

Start the web app:

```bash
cd apps/web
pnpm dev
```

Open `http://localhost:3000`.

## Verification

Backend tests:

```bash
cd apps/api
uv run pytest
```

Frontend lint, tests, and build:

```bash
cd apps/web
pnpm lint
pnpm test
pnpm build
```

Regenerate the checked-in OpenAPI types:

```bash
pnpm generate:types
```

## Notes

- The API returns `503` on rubric generation if Azure OpenAI environment variables are not configured.
- Rubric generation does not rely on prompt-only JSON formatting. The backend uses `responses.parse(...)` with the `RubricProposal` schema as the structured output contract.
- The only durable phase 1 output is the locked framework JSON artifact downloaded by the buyer.
