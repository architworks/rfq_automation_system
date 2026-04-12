# UI Notes

## Current Status
No detailed UI decisions have been locked yet. We have intentionally kept UI secondary while aligning on the functional model.

## What Is Already Constrained By Product Decisions
- The UI must clearly distinguish the formal award from advisory AI insights.
- Buyers must be able to inspect evidence behind scores and recommendations.
- Technical qualification status must be visible.
- Scenario outputs must not be confused with the official award outcome.

## Decisions Made
- Decision: UI decisions are deferred until the product model is more stable.
- Why This Approach: The product should not be shaped by presentation concerns before the evaluation logic is coherent.
- Rejected Alternatives:
  - Design polished screens before the system logic is settled.
  - Collapse technical, commercial, and advisory outputs into one undifferentiated view.
- Implications:
  - UI work should follow the current documentation set rather than lead it.
- Decision: Once the framework is locked, the buyer must be able to export a vendor-facing RFQ document from the browser.
- Why This Approach: The generated questionnaire and schedules are not useful unless they can be packaged into the actual document sent to vendors.
- Rejected Alternatives:
  - Expose only JSON and expect the buyer to manually assemble the outbound RFQ.
  - Reuse the internal buyer preview as-is even though it contains evaluation linkage details the vendor should not see.
- Implications:
  - The export should include only vendor-visible content such as RFQ header details, scope, timelines, line items, response instructions, questionnaire text, and schedules.
  - Internal scoring logic, thresholds, evidence checks, and criteria linkages should remain buyer-side only.
- Decision: The buyer should review a read-only normalization basis, not enter manual comparison settings.
- Why This Approach: FX and allowed UOM math are part of system governance for the prototype, not ad hoc buyer input. The buyer still needs to see the basis being applied, but should not have to configure it before evaluation.
- Rejected Alternatives:
  - Present editable FX-rate and UOM-override forms before results.
  - Hide normalization assumptions completely and expose only final commercial scores.
- Implications:
  - The review step should show the RFQ base currency, FX snapshot date, and the deterministic UOM policy.
  - The UI should explain that `Lot` and `Count` do not convert, while weight and volume units do.
  - Missing or unsupported currencies should surface as evaluation blockers, not as an invitation for the buyer to patch hidden system settings.
- Decision: Review and results screens should use procurement language instead of backend labels such as `base currency total`, raw criterion IDs, or evidence reference IDs in the primary view.
- Why This Approach: Buyers need to understand what was quoted, how it was normalized, what parameter was judged, and why the vendor passed or failed without first learning internal data-model jargon.
- Rejected Alternatives:
  - Keep exposing internal labels such as `base currency total`, `evidence refs`, and raw criterion IDs in the main scoring cards.
  - Show only the final scores and hide the RFQ-vs-vendor transformation and criterion logic.
- Implications:
  - Normalized pricing should clearly show vendor quoted price, vendor currency, vendor UOM, RFQ currency, RFQ UOM, converted RFQ-currency price, and buyer-readable blockers or notes.
  - Technical result cards should show criterion type, score, cutoff when relevant, the criterion description, the vendor-facing question, the evaluation summary, buyer-readable evidence snippets, and risks.
  - Internal evidence IDs and scoring traces should move into a collapsed detail section rather than the main view.

## Open Questions
- How should the buyer review and lock the evaluation framework?
- How should evidence be surfaced without overwhelming the user?
- How should qualified and disqualified vendors be displayed?
- How should advisory scenarios be compared against the formal recommendation?
