# Architecture

## Current Status
No implementation architecture has been locked yet. We have intentionally prioritized the functional model before choosing technical architecture.

## What Is Already Constrained By Product Decisions
- The system must support an end-to-end RFQ to award workflow.
- The system must process messy multi-format vendor documents.
- The system must preserve evidence traceability.
- The system must support a formal award engine plus an advisory scenario engine.

## Decisions Made
- Decision: Architecture choices are deferred until the product model is more stable.
- Why This Approach: Premature architecture discussion would create false precision before the evaluation model is settled.
- Rejected Alternatives:
  - Start with stack choices before locking the evaluation logic.
  - Let implementation convenience shape the procurement model.
- Implications:
  - Architecture should be discussed after the core RFQ and evaluation documents are more stable.

## Open Questions
- How should document ingestion, extraction, scoring, and recommendation components be separated?
- What should be deterministic logic versus model-driven logic?
- How should evidence and provenance be stored?
- How should scenario computation and scoring be versioned?
