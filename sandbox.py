#%%

from openai import OpenAI
from rfq_api.models import (
    OFFICIAL_AWARD_BASIS,
    BuyerPriority,
    GeneralInfo,
    LineItem,
    RFQDraft,
    RubricProposal,
    TimelineItem,
)

#%%
client = OpenAI(
    api_key="REDACTED",
    base_url="https://grmopenai-us2.openai.azure.com/openai/v1",  # e.g. https://your-resource.openai.azure.com/openai/v1/
    timeout=300,
)

rfq_draft = RFQDraft(
    general_info=GeneralInfo(
        title="Global Kids Health Drink Launch Partner RFQ",
        rfq_code="KHD-GL-2026-01",
        owner="Global Brand Procurement",
        region="Global",
    ),
    scope_overview=(
        "Select an integrated agency partner for the global launch of a new kids health drink "
        "covering strategy, creative, TVC development and production, paid and organic social, "
        "claims compliance review, and launch governance."
    ),
    timelines=[
        TimelineItem(
            id="tl_submission",
            label="Vendor submission deadline",
            target_date="2026-05-07",
            description="Final date for vendors to submit proposals and supporting documents.",
        ),
        TimelineItem(
            id="tl_eval",
            label="Technical and commercial evaluation complete",
            target_date="2026-05-21",
            description="Internal evaluation and recommendation sign-off date.",
        ),
        TimelineItem(
            id="tl_award",
            label="Award decision",
            target_date="2026-05-26",
            description="Buyer intends to finalize award and notify vendors.",
        ),
        TimelineItem(
            id="tl_launch",
            label="Market launch readiness",
            target_date="2026-07-15",
            description="All assets and media plans must be launch-ready before this date.",
        ),
    ],
    buyer_priorities=[
        BuyerPriority(
            id="priority_compliance",
            title="Kids advertising compliance",
            description="The program must be safe for child-directed marketing and claims usage.",
        ),
        BuyerPriority(
            id="priority_speed",
            title="Launch speed",
            description="The buyer values partners who can manage approvals and hit the launch calendar.",
        ),
        BuyerPriority(
            id="priority_integration",
            title="Integrated delivery",
            description="The buyer prefers partners who can coordinate multiple launch workstreams cleanly.",
        ),
    ],
    mandatory_conditions=[
        "Vendors must explicitly confirm capability to support child-directed advertising and claims review.",
        "Vendors must provide a named engagement lead and governance approach.",
        "Vendors must quote against all applicable RFQ line items and call out exclusions clearly.",
        "Vendors must state whether launch timelines are achievable with identified dependencies.",
    ],
    line_items=[
        LineItem(
            id="li_1",
            product_name="Strategy & Creative Development",
            category="Services",
            description=(
                "Launch strategy, audience segmentation, messaging framework, creative territory "
                "development and master campaign toolkit for a new kids health drink."
            ),
            hsn_sac="8471XX",
            uom="Lot",
        ),
        LineItem(
            id="li_2",
            product_name="TVC Development",
            category="Services",
            description=(
                "Development of flagship TV commercial concept and all pre-production creative "
                "required for global launch approvals."
            ),
            hsn_sac="8471XX",
            uom="Lot",
        ),
        LineItem(
            id="li_3",
            product_name="TVC Production",
            category="Services",
            description=(
                "End-to-end TVC shoot, post-production and delivery of master film and cutdowns "
                "for paid media use."
            ),
            hsn_sac="8471XX",
            uom="Lot",
        ),
        LineItem(
            id="li_4",
            product_name="Social Organic Content",
            category="Services",
            description=(
                "Organic social content strategy, monthly content calendar and asset adaptation "
                "for Meta, YouTube and TikTok."
            ),
            hsn_sac="8471XX",
            uom="Lot",
        ),
        LineItem(
            id="li_5",
            product_name="Social Paid Media Planning",
            category="Services",
            description=(
                "Paid social and video media planning across Meta, YouTube and TikTok for "
                "global launch period."
            ),
            hsn_sac="8471XX",
            uom="Lot",
        ),
        LineItem(
            id="li_6",
            product_name="Social Paid Media Buying & Optimization",
            category="Services",
            description=(
                "Campaign trafficking, paid media activation, optimization and performance "
                "reporting across Meta, YouTube and TikTok."
            ),
            hsn_sac="8471XX",
            uom="Lot",
        ),
        LineItem(
            id="li_7",
            product_name="Kids Advertising & Claims Compliance Review",
            category="Services",
            description=(
                "Legal and regulatory review of kids advertising content and product-related "
                "claims across launch assets and scripts."
            ),
            hsn_sac="8471XX",
            uom="Lot",
        ),
        LineItem(
            id="li_8",
            product_name="Launch Program Management",
            category="Services",
            description=(
                "Program management, stakeholder coordination, asset trafficking and master "
                "launch governance across all workstreams."
            ),
            hsn_sac="8471XX",
            uom="Lot",
        ),
    ],
)

instructions = (
    "You are generating an RFQ evaluation framework for a procurement buyer. "
    "Return only structured data that matches the schema. "
    f"The official award basis must remain fixed to {OFFICIAL_AWARD_BASIS}. "
    "Use a moderate hierarchy of sections, criteria, and evidence checks. "
    "Classify criteria into mac, technical_cutoff_backed, technical_scored_only, or commercial. "
    "Technical scored and cutoff-backed criteria together must total 100 points. "
    "Use only a selected subset of critical technical cutoffs, not a cutoff on every scored criterion. "
    "Generate freeform questions plus structured response schedules for pricing, scope coverage, "
    "compliance, timelines, and commercial terms. "
    "Every criterion must have evidence checks or linked questions/schedule fields."
)

#%%
rfq_text = """
RFQ Draft

General Info
- Title: Global Kids Health Drink Launch Partner RFQ
- RFQ Code: KHD-GL-2026-01
- Owner: Global Brand Procurement
- Region: Global

Scope Overview
Select an integrated agency partner for the global launch of a new kids health drink covering:
- Strategy
- Creative
- TVC development and production
- Paid and organic social
- Claims compliance review
- Launch governance

Timelines
1. Vendor submission deadline
   Date: 2026-05-07
   Description: Final date for vendors to submit proposals and supporting documents

2. Technical and commercial evaluation complete
   Date: 2026-05-21
   Description: Internal evaluation and recommendation sign-off date

3. Award decision
   Date: 2026-05-26
   Description: Buyer intends to finalize award and notify vendors

4. Market launch readiness
   Date: 2026-07-15
   Description: All assets and media plans must be launch-ready before this date

Buyer Priorities
1. Kids advertising compliance
   - The program must be safe for child-directed marketing and claims usage

2. Launch speed
   - Ability to manage approvals and hit the launch calendar

3. Integrated delivery
   - Ability to coordinate multiple launch workstreams cleanly

Mandatory Conditions
- Vendors must explicitly confirm capability to support child-directed advertising and claims review
- Vendors must provide a named engagement lead and governance approach
- Vendors must quote against all applicable RFQ line items and clearly call out exclusions
- Vendors must state whether launch timelines are achievable with dependencies

Line Items

1. Strategy & Creative Development
   Category: Services
   Description: Launch strategy, audience segmentation, messaging framework, creative territory development and master campaign toolkit for a new kids health drink
   HSN/SAC: 8471XX
   UOM: Lot

2. TVC Development
   Category: Services
   Description: Development of flagship TV commercial concept and all pre-production creative required for global launch approvals
   HSN/SAC: 8471XX
   UOM: Lot

3. TVC Production
   Category: Services
   Description: End-to-end TVC shoot, post-production and delivery of master film and cutdowns for paid media use
   HSN/SAC: 8471XX
   UOM: Lot

4. Social Organic Content
   Category: Services
   Description: Organic social content strategy, monthly content calendar and asset adaptation for Meta, YouTube and TikTok
   HSN/SAC: 8471XX
   UOM: Lot

5. Social Paid Media Planning
   Category: Services
   Description: Paid social and video media planning across Meta, YouTube and TikTok for global launch period
   HSN/SAC: 8471XX
   UOM: Lot

6. Social Paid Media Buying & Optimization
   Category: Services
   Description: Campaign trafficking, paid media activation, optimization and performance reporting across Meta, YouTube and TikTok
   HSN/SAC: 8471XX
   UOM: Lot

7. Kids Advertising & Claims Compliance Review
   Category: Services
   Description: Legal and regulatory review of kids advertising content and product-related claims across launch assets and scripts
   HSN/SAC: 8471XX
   UOM: Lot

8. Launch Program Management
   Category: Services
   Description: Program management, stakeholder coordination, asset trafficking and master launch governance across all workstreams
   HSN/SAC: 8471XX
   UOM: Lot
"""

input_text = (
    "Generate an RFQ evaluation rubric for the following draft.\n"
    f"{rfq_text}"
)
#%%
print(input_text)



#%%
response = client.responses.parse(
    model="gpt-5.4",  # e.g. gpt-5.4
    instructions=instructions,
    input=input_text,
    text_format=RubricProposal,
)



#%%
proposal = response.output_parsed
print(proposal)

# %%
input_text = (
    "Generate an RFQ evaluation rubric for the following draft.\n"
    f"{rfq_draft.model_dump_json(indent=2)}"
)

print(input_text)
# %%