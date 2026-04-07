# Open Questions

## RFQ Model
- Which specific criteria in a given RFQ should be `MAC`, `critical cutoff`, or `scored only`?

## Evaluation Framework
- Should split-award logic ever be part of the formal award engine, or remain advisory?
- Which technical parameters in a given RFQ should have individual minimum cutoffs in addition to the aggregate threshold?

## Scenario Engine
- How many AI-generated scenarios should be surfaced by default?
- Should buyers be able to tune advisory scenario weights interactively?

## Extraction And Normalization
- Should the internal model be built explicitly around claims, evidence, and confidence?
- How should conflicting evidence be represented?
- How should taxes, currencies, and unclear commercial units be normalized?

## Architecture
- How should the system separate deterministic rules from model-driven reasoning?
- What are the core services or modules in the eventual implementation?
- How should provenance and evidence be stored for auditability?

## UI
- What is the best workflow for rubric review and lock?
- How much detail should be visible by default versus drill-down?
- How should the UI communicate "official result" versus "AI insight" with no ambiguity?
