# Extraction And Normalization

## Current Model
Vendor submissions are messy evidence sources. The system must extract structured data from them and normalize that data before evaluation.

At minimum, the normalized output should support:
- pricing
- commercial terms
- scope coverage
- delivery timelines
- key technical claims
- evidence snippets linked to source documents

Extraction should be guided by both the locked rubric and the linked response schedules.

## Decisions Made

### Extraction Serves Evaluation
- Decision: Extraction should be guided by the locked evaluation framework rather than treated as open-ended summarization.
- Why This Approach: The system needs to pull out the specific data required for qualification, scoring, and recommendation.
- Rejected Alternatives:
  - Read vendor documents and summarize them freely.
  - Score vendors directly from raw documents without an intermediate structure.
- Implications:
  - The extraction layer needs knowledge of the rubric, questionnaire intents, and linked schedule fields.
  - Missing evidence should be visible as a first-class outcome.

### Normalization Is Mandatory
- Decision: Extracted data must be converted into a shared comparable structure before technical or commercial comparison.
- Why This Approach: Vendor documents will differ in wording, format, completeness, and units.
- Rejected Alternatives:
  - Compare vendor outputs in their native wording.
  - Use side-by-side document summaries as the basis for evaluation.
- Implications:
  - The system needs alignment across names, line items, units, and pricing terminology.
  - Commercial analysis is not meaningful until normalization is done.

### Normalization Basis Is Automatic
- Decision: The buyer does not manually enter FX rates or UOM override factors in the prototype flow.
- Why This Approach: Manual comparison settings add UI friction and distract from the core pipeline. For the demo, the normalization basis should be stable, explainable, and ready immediately after lock.
- Rejected Alternatives:
  - Ask the buyer to type FX rates before commercial evaluation.
  - Ask the buyer to manually define UOM conversion rules case by case.
- Implications:
  - Currency normalization uses a checked-in ECB snapshot.
  - The RFQ base currency is taken from the RFQ header.
  - If a vendor quotes in an unsupported currency, that line remains commercially blocked rather than waiting for buyer repair input.

### Structured Monetary And Quantity Extraction
- Decision: Prices, quantities, currencies, and units must be extracted into separate structured fields, not left embedded inside prose.
- Why This Approach: Downstream comparison and deterministic conversion become unreliable if the model returns only narrative phrases such as “USD 100 per kg” without separating the amount and unit.
- Rejected Alternatives:
  - Depend on free-text extraction and parse the prose later.
  - Let the evaluator infer quantity or unit semantics during scoring.
- Implications:
  - `raw_value` preserves the source text.
  - `numeric_value`, `currency`, `quantity_value`, and `uom` are populated separately when explicit evidence exists.
  - Numeric technical questions still require explicit numeric evidence and are not inferred from prose.

### Controlled Currency And UOM Inputs
- Decision: RFQ currency and line-item UOMs are selected from controlled catalogs instead of free text.
- Why This Approach: The normalization engine can only be deterministic if the RFQ itself uses known currencies and allowed units.
- Rejected Alternatives:
  - Let the buyer type arbitrary currency codes.
  - Let the buyer type arbitrary UOM text and normalize it later by guesswork.
- Implications:
  - RFQ currencies are constrained to the stored FX snapshot coverage.
  - RFQ UOMs are constrained to `Lot`, `Count`, and the supported weight or volume units.
  - Extraction can be prompted with the same allowed UOM set so the structured output stays compatible with later math.

### UOM Conversion Is Narrow By Design
- Decision: Only weight and volume units convert mathematically. `Lot` and count-style units do not convert.
- Why This Approach: Weight and volume families have objective deterministic math. Service lots and count-based items should only compare when they already align semantically.
- Rejected Alternatives:
  - Apply buyer-entered override factors to service or count units.
  - Treat any textual unit mismatch as safely convertible.
- Implications:
  - `Lot` is the standard service UOM and is never mathematically converted.
  - Count-style units normalize only to the same count family token.
  - Non-convertible UOM mismatches remain commercially blocked and explainable.

### Evidence Must Travel With Data
- Decision: Important extracted fields should carry source evidence so the evaluation remains grounded.
- Why This Approach: The assignment explicitly values explainability and evidence-backed outputs.
- Rejected Alternatives:
  - Produce normalized data with no trace back to source.
  - Ask buyers to trust the AI's extraction blindly.
- Implications:
  - The product needs citation or snippet support in downstream evaluation screens.
  - Extraction quality is not only about field values, but also about traceability.

### Rule-Mapped Missing Data Handling
- Decision: Missing inputs should be handled according to the criterion type they support, not by a blanket policy.
- Why This Approach: The significance of a missing field depends on whether it affects qualification, a cutoff, or only comparative scoring.
- Rejected Alternatives:
  - Auto-fail any missing field.
  - Treat all missing fields as low-impact scoring issues.
- Implications:
  - Missing evidence for a `MAC` can fail qualification.
  - Missing evidence for a cutoff-backed criterion can fail the cutoff.
  - Missing evidence for a scored-only criterion reduces score and confidence without auto-disqualification.

### Response State Distinctions
- Decision: The system should explicitly distinguish between missing vendor response, missing extractable evidence, and conflicting evidence.
- Why This Approach: These are different failure modes and should not collapse into one generic “missing data” state.
- Rejected Alternatives:
  - Treat every missing field as the same kind of problem.
  - Ignore conflicting evidence once one plausible value is found.
- Implications:
  - Downstream evaluation can separate vendor omission from extraction uncertainty.
  - Evidence conflicts become visible for auditability and confidence handling.

## Why This Approach
- It creates a reliable bridge from messy documents to formal evaluation.
- It reduces the risk of ungrounded scoring.
- It makes both technical and commercial comparisons more defensible.

## Rejected Alternatives
- Freeform summarization with no structural schema.
- Comparing documents without normalizing commercial and scope terms.
- Treating extraction as separate from evidence management.

## Implications
- The data model must support both structured fields and supporting evidence.
- Missing, partial, or conflicting responses should be detectable.
- The extraction layer is a core part of trust, not a preprocessing detail.

## Open Questions
- Should the internal data model use an explicit claims-and-evidence structure?
- How should confidence, ambiguity, and conflicting evidence be represented?
- How should taxes and other commercial adjustments be represented when vendor totals are not like-for-like?
