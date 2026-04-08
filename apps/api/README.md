# RFQ Rubric API

FastAPI backend for phase 1 of the RFQ prototype.

## Responsibilities

- create or hydrate browser-owned sessions
- store RFQ drafts and rubric proposals in memory
- generate rubric proposals through the OpenAI Python SDK using the Responses API
- validate and lock the final framework
- return the downloadable locked artifact JSON

## Setup

Prerequisites:

- `uv`
- Python 3.12+

Install dependencies:

```bash
uv sync
```

Copy the example env file:

```bash
cp .env.example .env
```

## Run

```bash
uv run uvicorn rfq_api.main:app --app-dir src --reload
```

The API runs on `http://localhost:8000` by default.

## Test

```bash
uv run pytest
```

## OpenAPI Export

```bash
uv run python -m rfq_api.tools.export_openapi ../openapi.json
```

## LLM Contract

- the backend uses `from openai import OpenAI`, not the Azure SDK client
- Azure hosting is handled through `base_url` plus `api_key`
- rubric generation uses `client.responses.parse(...)`
- output shape is enforced through Structured Outputs with the `RubricProposal` Pydantic model
- prompt text still carries procurement logic, but output conformance does not depend on asking the model to "return JSON"

## Environment Variables

- `FRONTEND_ORIGIN`: allowed browser origin for CORS, default `http://localhost:3000`
- `SESSION_TTL_SECONDS`: in-memory session TTL, default `7200`
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI base URL, for example `https://<resource>.openai.azure.com/openai/v1/`
- `AZURE_OPENAI_API_KEY`: Azure OpenAI key
- `AZURE_OPENAI_MODEL`: the model or deployment identifier passed in the OpenAI request
- `AZURE_OPENAI_TIMEOUT_SECONDS`: request timeout, default `60`

If Azure variables are missing, `/sessions/{session_id}/rubric/generate` returns `503`.
