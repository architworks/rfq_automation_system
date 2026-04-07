# Open Questions

## RFQ Model
- How much editing power should the buyer have over AI-proposed criteria, weights, and cutoffs before lock?
- Should the system generate only questions, or also structured response schedules and templates?
- How granular should the rubric be for large scopes of work?

## Evaluation Framework
- What exact technical threshold should the prototype use?
- Should some technical parameters have individual minimum cutoffs in addition to an aggregate threshold?
- How should dual-purpose criteria be represented when they have both a mandatory floor and a scored upside?
- Should split-award logic ever be part of the formal award engine, or remain advisory?

## Scenario Engine
- Which standard scenarios, if any, should always be included alongside AI-generated ones?
- Should the system define a scenario family before bids are received?
- Should buyers be able to tune scenario weights interactively?

## Extraction And Normalization
- Should the internal model be built explicitly around claims, evidence, and confidence?
- How should conflicting evidence be represented?
- How should missing vendor responses be separated from extraction failure?
- How should taxes, currencies, and unclear commercial units be normalized?

## Architecture
- How should the system separate deterministic rules from model-driven reasoning?
- What are the core services or modules in the eventual implementation?
- How should provenance and evidence be stored for auditability?

## UI
- What is the best workflow for rubric review and lock?
- How much detail should be visible by default versus drill-down?
- How should the UI communicate "official result" versus "AI insight" with no ambiguity?
