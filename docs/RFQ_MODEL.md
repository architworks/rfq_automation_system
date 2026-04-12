# RFQ Model

## Current Model
The RFQ lifecycle should follow a strict sequence so that evaluation logic is established before vendor responses are judged.

1. Buyer enters RFQ details.
2. AI analyzes the scope of work and line items.
3. AI proposes an evaluation and value model for that RFQ, including:
   - criterion classifications
   - weights
   - thresholds and cutoffs
   - questions
   - structured response schedules
4. Buyer reviews and locks the framework.
5. AI generates questionnaires and structured schedules aligned to the locked framework.
6. Vendor responses are ingested.
7. Extraction and normalization prepare the data for evaluation.
8. Technical and commercial evaluation are performed using the same locked framework.

## Decisions Made

### Framework-First Workflow
- Decision: The system should define the evaluation framework before vendor responses are evaluated.
- Why This Approach: It prevents the system from asking loose questions first and inventing evaluation logic later.
- Rejected Alternatives:
  - Generate generic questions without a pre-declared rubric.
  - Evaluate vendor responses afresh without reference to an earlier framework.
- Implications:
  - The system needs an internal representation of the evaluation framework, not just a list of questions.
  - Downstream extraction and evaluation must point back to the same framework.

### AI Drafts, Buyer Ratifies
- Decision: AI should propose the rubric and questionnaire, but the buyer should review and approve the model before evaluation proceeds.
- Why This Approach: Buyers may not know how to convert vague procurement intent into structured evaluation criteria, but the system still needs a human-approved basis before it judges vendors.
- Rejected Alternatives:
  - Fully manual rubric design as the default mode.
  - Fully autonomous AI-defined procurement rules with no buyer review.
- Implications:
  - The product needs a review-and-lock step before vendor evaluation.
  - AI value starts at the design stage, not only at the document analysis stage.

### Controlled Edit Before Lock
- Decision: The buyer has controlled edit rights over the AI-proposed framework before lock.
- Why This Approach: AI should accelerate rubric creation, but procurement ownership stays with the buyer before the RFQ is released.
- Rejected Alternatives:
  - Review-only approval with no meaningful edit control.
  - Fully manual authoring with AI kept out of framework design.
- Implications:
  - The buyer can edit criteria, classifications, weights, thresholds, questions, and schedules before lock.
  - After lock, the framework becomes immutable for evaluation.

### Questionnaire Serves The Rubric
- Decision: Questions should be generated from the evaluation framework, not treated as standalone content.
- Why This Approach: The point of the questionnaire is to gather evidence for evaluation, not simply to produce more text.
- Rejected Alternatives:
  - Treating the questionnaire as a separate artifact disconnected from scoring.
  - Asking broad prompts that are hard to map back to qualification or scoring.
- Implications:
  - Each question should correspond to a specific evaluation intent.
  - The extraction layer should know which question or criterion each piece of evidence supports.

### Criterion Owns Its Question
- Decision: Every non-commercial criterion should own its exact vendor-facing question inside the criterion object, instead of generating a separate question list and linking them later by ID.
- Why This Approach: In this system, the question exists only to gather evidence for that criterion. Nesting removes unnecessary indirection and reduces LLM linkage failures.
- Rejected Alternatives:
  - Generating `criteria[]` and `questions[]` independently and asking the model to cross-link them with IDs.
  - Treating vendor questions as first-class standalone objects for technical scoring when the intended mapping is one criterion to one question.
- Implications:
  - One non-commercial criterion maps to one vendor-facing question.
  - The top-level question list can remain as a derived export/view for compatibility, but the criterion is the source of truth.
  - Commercial criteria remain primarily schedule-backed.

### Questions Plus Structured Schedules
- Decision: The RFQ response package should include both freeform questions and structured response schedules.
- Why This Approach: Questions capture qualitative evidence, while schedules improve comparability for pricing, scope, compliance, timelines, and commercial terms.
- Rejected Alternatives:
  - Questions only.
  - Highly schedule-driven responses with minimal qualitative questioning.
- Implications:
  - The system should generate structured schedules for core comparable response areas.
  - Missing schedule fields are evaluated according to the mapped criterion type, not failed by default.

### Moderate Rubric Hierarchy
- Decision: The rubric should use a moderate hierarchy of `section -> criterion -> evidence check`.
- Why This Approach: It is structured enough for extraction and scoring without becoming atomized into an excessive number of micro-criteria.
- Rejected Alternatives:
  - Very coarse broad-criterion rubrics.
  - Highly atomic rubrics with many fine-grained items.
- Implications:
  - The framework remains usable for both buyers and downstream extraction logic.

## Why This Approach
- It creates a single golden thread from RFQ intent to final award.
- It reduces evaluation drift between the RFQ stage and the award stage.
- It makes explanations easier because the system can point from award logic back to the original evaluation design.

## Rejected Alternatives
- A chatbot-style approach where the system asks generic questions and later improvises the evaluation model.
- A document-reading approach where vendor submissions are scored directly without a prior framework.
- A process where procurement value is defined entirely after bids are seen.

## Implications
- The RFQ model is not just input capture; it is where the evaluation contract is defined.
- The product needs a distinction between draft mode and locked mode.
- Question generation, extraction, and evaluation should all operate against shared identifiers or rubric items.

## Open Questions
- No framework-level RFQ model questions are currently open.
- RFQ-specific criterion design will vary by scope and evaluation intent.
