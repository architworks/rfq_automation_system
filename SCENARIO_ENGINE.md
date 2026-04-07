# Scenario Engine

## Current Model
The product has two layers of decision support:

1. A formal award engine with one official basis for the prototype: `QCBS 70/30`.
2. An advisory scenario engine that includes `LCS`, `QBS`, and RFQ-specific AI-generated scenarios.

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

### Standard Advisory Comparisons
- Decision: The advisory layer should always include `LCS` and `QBS` views alongside the official `QCBS 70/30` result, plus RFQ-specific AI-generated scenarios.
- Why This Approach: It gives the buyer consistent baseline comparisons while preserving room for context-aware AI insight.
- Rejected Alternatives:
  - AI-generated scenarios only.
  - Price-first advisory views without a quality-first comparison.
- Implications:
  - Advisory output includes both standard and RFQ-specific scenario lenses.

### AI-Generated Scenarios Are Contextual
- Decision: The product should support AI-generated scenarios that emerge from the RFQ context rather than a fixed hardcoded list.
- Why This Approach: The assignment examples such as fastest delivery or best compliance are examples, not the entire scenario model.
- Rejected Alternatives:
  - Hardcode a permanent small set of scenarios and treat them as universal.
  - Turn every example from the assignment into a mandatory system requirement.
- Implications:
  - The scenario engine must inspect the RFQ and qualified vendor data.
  - Different RFQs may yield different scenario sets.

### Scenarios Bound To Locked Dimensions
- Decision: Advisory scenarios must remain bound to the dimensions already locked in the rubric before bids are received.
- Why This Approach: The system may reinterpret value, but it should not invent new evaluation dimensions after seeing vendor responses.
- Rejected Alternatives:
  - Fully emergent post-bid scenario logic.
  - Scenarios introducing new criteria not present in the locked framework.
- Implications:
  - Scenarios may reweight or recombine locked dimensions.
  - Scenario winners must still come from the technically qualified pool.

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

### Split Award Is Advisory
- Decision: Split-award outcomes remain advisory only in the current model.
- Why This Approach: The formal prototype award basis is a single-winner `QCBS 70/30` result, while split award is better treated as a strategic alternative.
- Rejected Alternatives:
  - Make split award part of the default formal award engine.
  - Allow split-award outcomes to override the official QCBS result.
- Implications:
  - Split award can appear as an AI insight when justified by the RFQ and vendor mix.
  - It does not change the formal prototype winner.

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
- How many AI-generated scenarios should be surfaced by default?
- Should the buyer be able to adjust scenario weights interactively after seeing results?
