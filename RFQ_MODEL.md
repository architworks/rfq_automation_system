# RFQ Model

## Current Model
The RFQ lifecycle should follow a strict sequence so that evaluation logic is established before vendor responses are judged.

1. Buyer enters RFQ details.
2. AI analyzes the scope of work and line items.
3. AI proposes an evaluation and value model for that RFQ.
4. Buyer reviews and locks the framework.
5. AI generates questionnaires aligned to the locked framework.
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

### Questionnaire Serves The Rubric
- Decision: Questions should be generated from the evaluation framework, not treated as standalone content.
- Why This Approach: The point of the questionnaire is to gather evidence for evaluation, not simply to produce more text.
- Rejected Alternatives:
  - Treating the questionnaire as a separate artifact disconnected from scoring.
  - Asking broad prompts that are hard to map back to qualification or scoring.
- Implications:
  - Each question should correspond to a specific evaluation intent.
  - The extraction layer should know which question or criterion each piece of evidence supports.

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
- How much control should the buyer have over editing AI-proposed weights, cutoffs, and criteria?
- Should the system generate only questionnaire items, or also structured response templates and schedules?
- How granular should the rubric become for broad scopes of work?
