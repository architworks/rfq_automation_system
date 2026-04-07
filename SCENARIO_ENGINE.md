# Scenario Engine

## Current Model
The product has two layers of decision support:

1. A formal award engine with one official basis for the prototype: `QCBS 70/30`.
2. An advisory scenario engine that helps the buyer explore alternate definitions of value.

The advisory layer should never be confused with the formal award basis.

## Why The Scenario Engine Exists
Procurement teams may not be fully sure which value lens matters most for a given RFQ. The system should help them inspect different trade-offs without weakening the official award logic.

## Decisions Made

### Standard First, AI Second
- Decision: Scenario analysis should sit on top of the standard procurement evaluation, not replace it.
- Why This Approach: AI adds value when it helps interpret trade-offs, not when it dissolves the distinction between policy and analysis.
- Rejected Alternatives:
  - Use AI scenarios as the sole award mechanism.
  - Let advisory scenarios silently override the formal basis.
- Implications:
  - The product needs a clear distinction between official result and AI insight.
  - Standard procurement protocols remain the foundation.

### AI-Generated Scenarios Are Contextual
- Decision: The product should support AI-generated scenarios that emerge from the RFQ context rather than a fixed hardcoded list.
- Why This Approach: The assignment examples such as fastest delivery or best compliance are examples, not the entire scenario model.
- Rejected Alternatives:
  - Hardcode a permanent small set of scenarios and treat them as universal.
  - Turn every example from the assignment into a mandatory system requirement.
- Implications:
  - The scenario engine must inspect the RFQ and qualified vendor data.
  - Different RFQs may yield different scenario sets.

### Scenario Winners Must Still Be Qualified
- Decision: Scenario comparisons may use alternate value lenses, but any recommended scenario winner should still come from the technically qualified pool.
- Why This Approach: Scenarios are supposed to reinterpret value, not waive technical eligibility.
- Rejected Alternatives:
  - Include technically disqualified vendors as scenario winners because they are cheaper.
  - Treat failed technical vendors as valid alternates for award.
- Implications:
  - The qualified pool is the universe for scenario ranking.
  - Disqualified vendors may still appear as benchmarks or anomaly references.

### Disqualified Vendors As Benchmarking Data
- Decision: Disqualified vendors may be shown in advisory analysis to explain market range, price anomalies, or why the official winner costs more.
- Why This Approach: They still provide context, but they should not contaminate award eligibility.
- Rejected Alternatives:
  - Hide disqualified vendors completely.
  - Keep disqualified vendors fully active in the recommendation engine.
- Implications:
  - The UI and explanations need a clear status distinction.
  - The reasoning engine can reference them for contrast, not selection.

## Why This Approach
- It preserves procurement defensibility while keeping the AI layer genuinely useful.
- It lets the system answer both questions:
  - "Who formally wins?"
  - "How would the answer change if we care more about a different value lens?"

## Rejected Alternatives
- Treating scenario modeling as the official procurement rule.
- Hardcoding example scenarios from the assignment into a fixed product menu.
- Using scenario analysis to keep non-compliant vendors alive in the decision set.

## Implications
- The product needs a strong explanation layer.
- Scenario outputs should be clearly labeled as advisory.
- The same normalized data model should feed both the formal award engine and the scenario engine.

## Open Questions
- Which standard advisory scenarios should always be shown, if any?
- Should the system propose scenario families before bids are received?
- How should split-award simulations be generated and constrained?
- Should the buyer be able to adjust scenario weights interactively after seeing results?
