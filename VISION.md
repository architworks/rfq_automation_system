# Application Vision

## Purpose
This system is an AI-assisted procurement engine for RFQ evaluation. It is meant to help a buyer move from messy vendor submissions to a defensible award recommendation without relying on static dashboards or hardcoded conclusions.

## Core Product Idea
The product exists because procurement teams are often not fully sure how to convert a broad scope of work into a rigorous definition of value before vendor responses arrive.

The system should help them do two things:

1. Convert buyer intent into a structured evaluation model before vendors are judged.
2. Compare qualified vendors through both a formal award basis and advisory AI insights.

## Current Model
The product follows a framework-first approach:

1. A buyer provides the RFQ context.
2. AI proposes an evaluation and value model for that RFQ, including criteria, classifications, weights, thresholds, questions, and response schedules.
3. The buyer has controlled edit rights and then locks that model before vendor evaluation.
4. AI generates questionnaire content and structured response schedules aligned to the locked model.
5. Vendors submit messy documents.
6. The system extracts and normalizes evidence from those documents.
7. Vendors go through a technical gate consisting of:
   - `MAC`
   - selected critical technical cutoffs
   - an aggregate technical threshold
8. Commercial analysis is performed on qualified vendors.
9. The prototype produces:
   - one official single-winner `QCBS 70/30` award outcome
   - advisory `LCS`, `QBS`, and RFQ-specific AI scenario insights

## What The System Is
- An evidence-backed decision-support system.
- A bridge between unstructured vendor documents and structured evaluation.
- A product that combines procurement rules with AI-driven insight generation.

## What The System Is Not
- A freeform chatbot that evaluates vendors ad hoc.
- A static dashboard with hardcoded outputs.
- A system that invents evaluation logic after seeing bids.

## Core Principles
- Framework first: evaluation logic is defined before vendor evaluation.
- Standard first, AI second: AI augments procurement logic but does not replace hard gates.
- No black boxes: every important conclusion should be tied to visible evidence.
- Grounded outputs: recommendations must be traceable to vendor submissions.
- Clear separation of binding and advisory outputs: the official award logic is distinct from simulated scenarios.
- Advisory scenarios are bound to the locked evaluation dimensions and the technically qualified vendor pool.

## Decision Snapshot
- The evaluation framework is derived before vendor responses are evaluated.
- The buyer has controlled edit rights over the AI-proposed framework before lock.
- The RFQ package includes both questionnaire items and structured response schedules.
- Technical disqualification removes a vendor from award eligibility.
- The prototype's official award basis is `QCBS 70/30`.
- `LCS`, `QBS`, and RFQ-specific AI scenarios are advisory AI insights, not the formal award basis.
- AI-generated scenarios should be contextual to the RFQ, not hardcoded into the product.

## Relationship To Other Docs
- `RFQ_MODEL.md` defines the RFQ lifecycle and rubric/questionnaire flow.
- `EVALUATION_FRAMEWORK.md` defines qualification, scoring, and award rules.
- `SCENARIO_ENGINE.md` defines advisory scenarios.
- `EXTRACTION_NORMALIZATION.md` defines extraction and evidence handling.
- `OPEN_QUESTIONS.md` tracks unresolved debates.
