# Evaluation Framework

## Current Model
The evaluation framework uses a dual-hurdle model:

1. Technical qualification happens first through a layered gate:
   - `MAC`
   - selected critical technical cutoffs
   - an aggregate technical threshold
2. Only qualified vendors are eligible for the formal award.
3. Commercial comparison and final ranking occur on the qualified pool.

The prototype's formal award basis is `QCBS 70/30`.

## Decisions Made

### Requirement Taxonomy
- Decision: Evaluation criteria should be split into `MAC`, `Technical Cutoff-Backed`, `Technical Scored-Only`, and `Commercial`.
- Why This Approach: Not every requirement serves the same purpose. Some are hard stops, some rank quality, and some govern value for money.
- Rejected Alternatives:
  - Treat all criteria as one blended quality score.
  - Use only binary requirements with no quality differentiation.
- Implications:
  - The system needs explicit classification of each criterion.
  - Evaluation outputs should explain whether an issue caused disqualification or only reduced score.

### Technical Gate
- Decision: A vendor must pass mandatory acceptance criteria and clear a technical threshold to remain award-eligible.
- Why This Approach: It protects against both kinds of failure:
  - a vendor that is non-compliant
  - a vendor that is compliant on paper but technically weak
- Rejected Alternatives:
  - `MAC only` qualification.
  - `Quality only` qualification with no hard-stop criteria.
- Implications:
  - Technical evaluation has both binary and scored logic.
  - The system must support disqualification reasons that are clear and auditable.

### Individual Technical Cutoffs
- Decision: Individual minimum cutoffs should be applied only to selected critical technical criteria, not to every scored parameter.
- Why This Approach: Some technical dimensions are important enough to require a floor, but applying cutoffs everywhere makes the process brittle and overly bureaucratic.
- Rejected Alternatives:
  - Impose an individual cutoff on every scored technical parameter.
  - Use only an aggregate technical threshold with no parameter-level floors.
- Implications:
  - The technical gate becomes a layered filter:
    - MAC
    - selected critical technical cutoffs
    - aggregate technical threshold
  - The product must distinguish between:
    - scored-only criteria
    - cutoff-backed criteria
    - MAC criteria

### RFQ-Specific Technical Threshold
- Decision: The aggregate technical threshold and selected critical cutoffs are RFQ-specific. AI proposes them and the buyer approves them before lock.
- Why This Approach: Different RFQs have different risk profiles, so one universal threshold is too rigid.
- Rejected Alternatives:
  - One permanent house threshold for every RFQ.
  - Fully manual threshold design without AI assistance.
- Implications:
  - Each RFQ stores its own approved technical threshold and critical cutoffs.
  - Threshold-setting becomes part of the rubric design phase.

### Dual-Purpose Criteria
- Decision: Criteria that have both a minimum floor and a scored upside should be modeled as a single linked criterion.
- Why This Approach: One criterion can use one evidence base to support both qualification and ranking without duplicating logic.
- Rejected Alternatives:
  - Split the floor and upside into separate independent criteria.
  - Force every criterion to be only gating or only scored.
- Implications:
  - A single criterion can contain:
    - a minimum qualification floor
    - a scored quality range above that floor

### Qualified Pool Only For Award
- Decision: Technically disqualified vendors should not be considered in the formal award recommendation.
- Why This Approach: A buyer can benchmark against those vendors, but cannot defensibly award to them after they fail hard qualification logic.
- Rejected Alternatives:
  - Allow disqualified vendors to remain in the final award pool because of price.
  - Let scenarios override disqualification.
- Implications:
  - The award engine operates on a filtered vendor pool.
  - The system may still reference disqualified bids for context or anomaly analysis.

### Official Award Basis
- Decision: The prototype's formal award basis is `QCBS 70/30`.
- Why This Approach: It gives the prototype one defensible official winner while still balancing quality and cost.
- Rejected Alternatives:
  - `LCS` as the official award rule for the prototype.
  - Selecting the formal award rule after seeing bids.
- Implications:
  - Technical score remains relevant in the final award, not just at the gateway stage.
  - Commercial extraction must support comparable cost scoring.
  - Scenario outputs must be clearly separated from the formal award result.

### Rule-Mapped Missing Evidence
- Decision: Missing evidence should be handled according to the criterion type it supports, not by a blanket pass/fail rule.
- Why This Approach: The significance of missing information depends on whether it affects qualification, a critical floor, or only comparative scoring.
- Rejected Alternatives:
  - Auto-fail any missing field.
  - Treat all missing fields as low-impact scoring issues.
- Implications:
  - Missing evidence for a `MAC` can fail qualification.
  - Missing evidence for a cutoff-backed criterion can fail the cutoff.
  - Missing evidence for a scored-only criterion reduces score and confidence without auto-disqualification.

## Why This Approach
- It aligns with the idea that the system should not blindly reward the cheapest bid.
- It gives the prototype a formal and auditable selection basis.
- It preserves room for scenario simulation without weakening the official award logic.
- It avoids turning technical evaluation into an unnecessarily rigid checklist.

## Rejected Alternatives
- `MAC only`: too weak for complex services because it can let technically mediocre vendors survive too easily.
- `Quality only`: too weak on non-negotiable compliance and legal requirements.
- Letting the final award protocol be invented after seeing bids: useful as simulation, weak as official procurement logic.

## Implications
- The scoring system must preserve both technical and commercial dimensions cleanly.
- The system needs explicit disqualification handling.
- The product should visibly separate:
  - qualified vs disqualified
  - formal award vs advisory insights

## Open Questions
- Which technical criteria should have individual cutoffs in addition to the aggregate threshold?
- Should split-award logic remain advisory only, or be allowed as a formal outcome in some RFQs?
