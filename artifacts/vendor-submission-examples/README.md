# Vendor Submission Examples

This folder contains five manually-authored vendor response examples built from the sample RFQ and the archived generated questionnaire saved in `rfq-package/`.
The final `submissions/` set is intentionally mixed across PDF and DOCX so the demo exercises more than one vendor document format.

## Contents

- `rfq-package/`: sample RFQ snapshot, archived generated rubric, and vendor-facing package reference
- `source/`: saved markdown source used to create the final files
- `submissions/`: uploadable vendor response files, one final artifact per vendor

## Vendor Set

- `01_sparkbridge_global_submission.pdf` - SparkBridge Global: Official QCBS benchmark: passes both MACs, clears the technical gate comfortably, and wins on the best comparable pricing among technically qualified vendors.
- `02_bluepeak_mediaworks_submission.docx` - BluePeak MediaWorks: Technically strong vendor that passes both MACs and the technical gate, but loses on higher normalized price after FX conversion.
- `03_nimblenest_creative_submission.pdf` - NimbleNest Creative: Passes the two MAC checks, but the lighter governance and weaker integration answers are intended to miss the technical gate.
- `04_childsafe_integrated_submission.docx` - ChildSafe Integrated: Quality-led vendor: passes MAC and should score very strongly technically, but is priced high enough to lose the official QCBS recommendation.
- `05_launchloop_collective_submission.pdf` - LaunchLoop Collective: Cheapest-looking bid, but designed to fail MAC because product claims review capability is explicitly unavailable.

The examples are intentionally varied in quality, pricing currency, assumptions, and compliance posture so they can be used to test technical gating, commercial normalization, and explainability flows.
