# Vendor-Facing RFQ Package Snapshot

This package uses the prefilled sample RFQ plus the archived medium-reasoning generated rubric.

## RFQ Header

- Subject: RFQ for global launch marketing services for new kids health drink
- RFQ Code: RFQ-MKT-KIDS-GL-2026-001
- Sourcing Type: RFQ
- Round: Round 1
- Owner: Ava Thompson
- Currency: USD
- Requestor: Global Brand Marketing Team
- Department: Marketing Procurement
- Category: Marketing Services

## Scope Overview

Select an integrated agency partner for the global launch of a new kids health drink covering strategy, creative, TVC development and production, paid and organic social, claims compliance review, and launch governance.

## Timelines

- Clarifications Deadline: 2026-05-12
- Technical Bid Deadline: 2026-05-19
- Commercial Bid Deadline: 2026-05-21
- Evaluation Start Date: 2026-05-22
- Negotiation Start Date: 2026-05-27
- Final Award Date: 2026-06-02

## Requested Line Items

- li_1: Strategy & Creative Development [Services, Lot] - Launch strategy, audience segmentation, messaging framework, creative territory development and master campaign toolkit for a new kids health drink.
- li_2: TVC Development [Services, Lot] - Development of flagship TV commercial concept and all pre-production creative required for global launch approvals.
- li_3: TVC Production [Services, Lot] - End-to-end TVC shoot, post-production and delivery of master film and cutdowns for paid media use.
- li_4: Social Organic Content [Services, Lot] - Organic social content strategy, monthly content calendar and asset adaptation for Meta, YouTube and TikTok.
- li_5: Social Paid Media Planning [Services, Lot] - Paid social and video media planning across Meta, YouTube and TikTok for global launch period.
- li_6: Social Paid Media Buying & Optimization [Services, Lot] - Campaign trafficking, paid media activation, optimization and performance reporting across Meta, YouTube and TikTok.
- li_7: Kids Advertising & Claims Compliance Review [Services, Lot] - Legal and regulatory review of kids advertising content and product-related claims across launch assets and scripts.
- li_8: Launch Program Management [Services, Lot] - Program management, stakeholder coordination, asset trafficking and master launch governance across all workstreams.

## Archived Generated Questionnaire

1. **q_child_compliance** - Select one option for your capability to support child-directed advertising compliance across launch assets and approvals: (a) Yes - delivered by our organisation, (b) Yes - delivered through a named specialist partner, or (c) No. If you select (b), provide the partner name.
   - Purpose: Tests the explicit mandatory confirmation for child-directed advertising compliance capability.
2. **q_claims_review** - Select one option for your capability to support product claims review for launch assets and related approvals: (a) Yes - delivered by our organisation, (b) Yes - delivered through a named specialist partner, or (c) No. If you select (b), provide the partner name.
   - Purpose: Tests the explicit mandatory confirmation for product claims review capability.
3. **q_launch_governance** - Provide your proposed launch governance and approval-management plan for this scope, including key milestones, critical path, approval routing, escalation approach, and the actions you will take to protect the stated launch calendar.
   - Purpose: Assesses the bidder's ability to manage approvals and maintain launch speed.
4. **q_integrated_delivery** - Describe the operating model you will use to coordinate strategy, creative, TVC development and production, organic social, paid media planning and buying, compliance review, and launch program management as one integrated launch program.
   - Purpose: Assesses the bidder's ability to coordinate multiple launch workstreams cleanly.
5. **q_campaign_solution** - Describe your proposed global launch solution across strategy, messaging, creative territory, TVC, organic social, and paid social/video, showing how the workstreams connect into one launch campaign.
   - Purpose: Assesses the strength and coherence of the bidder's proposed launch approach.

## Structured Commercial Schedules

### Commercial pricing schedule (sched_pricing)

- Line item ref (Required): Reference number of the requested line item.
- Line item name (Required): Name of the requested service lot.
- Quote status (Required): State whether the line is priced, included elsewhere, or excluded.
- Included in line ref (Optional): If included elsewhere, identify the line item reference containing the price.
- Currency (Required): Quoted currency for the line item; expected currency is USD.
- Total price (Optional): Total quoted amount for the line item where priced.

### Commercial pricing detail (sched_pricing_detail)

- Quantity (Optional): Quantity if applicable to the pricing basis.
- UOM (Optional): Unit of measure if applicable.
- Exclusions or assumptions (Required): State exclusions, dependencies, or assumptions affecting the quote.

## Internal Rubric Traceability Snapshot

- crit_mac_child_compliance: Child marketing compliance [mac] -> questions q_child_compliance
- crit_mac_claims_review: Claims review capability [mac] -> questions q_claims_review
- crit_launch_governance_speed: Launch governance and speed [technical_cutoff_backed] -> questions q_launch_governance
- crit_integrated_delivery: Integrated delivery model [technical_scored_only] -> questions q_integrated_delivery
- crit_campaign_solution: Campaign solution quality [technical_scored_only] -> questions q_campaign_solution
- crit_commercial_completeness: Pricing completeness [commercial] -> questions none
