# TenderLens Docs

Standalone Docusaurus site for the TenderLens submission documentation.

## Purpose
- evaluator-facing submission overview, not a frontend user guide
- clean separation between high-level narrative and technical appendix
- fully standalone folder that can be moved into another repo or deployed as its own Vercel project

## Local commands
```bash
pnpm install
pnpm dev
pnpm build
pnpm serve
```

## Deployment shape
- deploy `tenderlens-docs/` as a separate Vercel project
- set the Vercel project root to this folder
- the generated static output is written to `build/`

## Production note
Before deploying publicly, update the `url` field in `docusaurus.config.ts` to the final docs domain.
