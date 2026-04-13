from __future__ import annotations

import html
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RFQ_DIR = ROOT / "rfq-package"
SUBMISSIONS_DIR = ROOT / "submissions"
SOURCE_DIR = ROOT / "source"
DEFAULT_CHROME_BINARY = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def main() -> None:
    RFQ_DIR.mkdir(parents=True, exist_ok=True)
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    clear_generated_outputs()

    framework = json.loads((RFQ_DIR / "sample-generated-framework.json").read_text())
    rfq = framework["rfq_draft"]
    rubric = framework["rubric_proposal"]
    vendor_pack = framework["vendor_pack"]

    write_reference_files(rfq=rfq, rubric=rubric, vendor_pack=vendor_pack)

    vendors = build_vendor_profiles()
    for vendor in vendors:
        markdown_path = SOURCE_DIR / f"{vendor['slug']}.md"
        if not markdown_path.exists():
            raise FileNotFoundError(
                f"Source markdown not found for {vendor['slug']}. Expected {markdown_path}."
            )
        markdown = markdown_path.read_text()

        html_path = SOURCE_DIR / f"{vendor['slug']}.html"
        html_path.write_text(render_vendor_html(markdown=markdown, vendor=vendor))

        output_format = vendor["final_format"]
        if output_format == "docx":
            render_docx_from_html(
                html_path=html_path,
                output_path=SUBMISSIONS_DIR / f"{vendor['slug']}.docx",
            )
        elif output_format == "pdf":
            render_pdf_from_html(
                html_path=html_path,
                output_path=SUBMISSIONS_DIR / f"{vendor['slug']}.pdf",
            )
        else:
            raise ValueError(f"Unsupported final_format for {vendor['slug']}: {output_format}")

    write_readme(vendors)


def write_reference_files(*, rfq: dict, rubric: dict, vendor_pack: dict) -> None:
    questions = vendor_pack["questions"]
    schedules = vendor_pack["response_schedules"]
    criteria = vendor_pack["criteria"]

    lines: list[str] = []
    lines.append("# Vendor-Facing RFQ Package Snapshot")
    lines.append("")
    lines.append("This package uses the prefilled sample RFQ plus the archived medium-reasoning generated rubric.")
    lines.append("")
    lines.append("## RFQ Header")
    lines.append("")
    general_info = rfq["general_info"]
    lines.append(f"- Subject: {general_info['subject']}")
    lines.append(f"- RFQ Code: {general_info['rfq_code']}")
    lines.append(f"- Sourcing Type: {general_info['sourcing_type']}")
    lines.append(f"- Round: {general_info['round']}")
    lines.append(f"- Owner: {general_info['owner']}")
    lines.append(f"- Currency: {general_info['currency']}")
    lines.append(f"- Requestor: {general_info['requestor']}")
    lines.append(f"- Department: {general_info['department']}")
    lines.append(f"- Category: {general_info['category']}")
    lines.append("")
    lines.append("## Scope Overview")
    lines.append("")
    lines.append(rfq["scope_overview"])
    lines.append("")
    lines.append("## Timelines")
    lines.append("")
    for label, value in rfq["timelines"].items():
        lines.append(f"- {label.replace('_', ' ').title()}: {value}")
    lines.append("")
    lines.append("## Requested Line Items")
    lines.append("")
    for item in rfq["line_items"]:
        lines.append(
            f"- {item['id']}: {item['product_name']} [{item['category']}, {item['uom']}] - {item['description']}"
        )
    lines.append("")
    lines.append("## Archived Generated Questionnaire")
    lines.append("")
    for index, question in enumerate(questions, start=1):
        lines.append(f"{index}. **{question['id']}** - {question['text']}")
        lines.append(f"   - Purpose: {question['purpose']}")
    lines.append("")
    lines.append("## Structured Commercial Schedules")
    lines.append("")
    for schedule in schedules:
        lines.append(f"### {schedule['name']} ({schedule['id']})")
        lines.append("")
        for column in schedule["columns"]:
            required = "Required" if column["required"] else "Optional"
            lines.append(f"- {column['label']} ({required}): {column['description']}")
        lines.append("")
    lines.append("## Internal Rubric Traceability Snapshot")
    lines.append("")
    for criterion in criteria:
        lines.append(
            f"- {criterion['criterion_id']}: {criterion['title']} [{criterion['criterion_type']}] -> "
            f"questions {', '.join(criterion['linked_question_ids']) or 'none'}"
        )
    lines.append("")

    (RFQ_DIR / "sample-rfq.json").write_text(json.dumps(rfq, indent=2))
    (RFQ_DIR / "generated-rubric-package.json").write_text(json.dumps(rubric, indent=2))
    (RFQ_DIR / "generated-questions.json").write_text(json.dumps(questions, indent=2))
    (RFQ_DIR / "vendor-facing-rfq-package.md").write_text("\n".join(lines))


def clear_generated_outputs() -> None:
    for directory, patterns in (
        (SUBMISSIONS_DIR, ("*.pdf", "*.doc", "*.docx", "*.ppt", "*.pptx", "*.xls", "*.xlsx")),
        (SOURCE_DIR, ("*.html",)),
    ):
        for pattern in patterns:
            for path in directory.glob(pattern):
                path.unlink()


def build_vendor_profiles() -> list[dict]:
    return [
        {
            "slug": "01_sparkbridge_global_submission",
            "final_format": "pdf",
            "vendor_name": "SparkBridge Global",
            "scenario": "Designed as the balanced benchmark vendor: strong technical quality, full line-item coverage, and the most competitive comparable pricing among technically qualified bidders.",
            "contact_block": "Prepared by: SparkBridge Global Launch Practice | Contact: Sarah Lin | Currency: USD",
            "agency_overview": "SparkBridge Global is an integrated launch partner combining brand strategy, creative development, production management, social activation, and launch PMO support across consumer health categories. The team proposed for this RFQ would be led from our global launch practice with embedded compliance and production specialists, and the submission intentionally covers all eight requested line items in one coordinated scope.",
            "strategic_point_of_view": "Our point of view is that the strongest kids-health launch combines caregiver trust, disciplined claims-safe messaging, and one adaptable master idea that can travel cleanly from flagship film into social and paid activation.",
            "selected_relevant_work": [
                "Global nutrition beverage relaunch across 14 markets with one master film and modular social system.",
                "Family wellness campaign requiring integrated legal and claims review across TV, digital, and shopper assets.",
            ],
            "answers": {
                "q_cr_mac_1": "Yes. Support will be provided by our Kids Marketing Compliance Cell working alongside the global creative and channel leads.",
                "q_cr_mac_2": "Yes. Claims review support will be provided by our in-house Health Claims and Regulatory Practice with escalation to market counsel where needed.",
                "q_cr_mac_3": "Sarah Lin, Global Launch Director, sarah.lin@sparkbridgeglobal.com. Sarah would own executive delivery, decision coordination, and buyer-facing accountability across all workstreams.",
                "q_cr_mac_4": "Yes. We would run a weekly steering committee, twice-weekly cross-functional operations review, and a 24-hour escalation path for claims, approvals, and production risks. Buyer sign-off would follow a defined approve/revise/escalate route.",
                "q_cr_mac_5": "Achievable as issued. Standard buyer approvals within the agreed turnaround windows will be sufficient; no exceptional dependencies or scope caveats are required beyond normal launch governance inputs.",
                "q_cr_tech_1": "Our compliance operating model places checkpoints at briefing, audience and message architecture approval, creative territory selection, storyboard approval, final script, pre-shoot legal lock, rough cut, final cut, and market adaptation release. One compliance lead owns the child-directed advertising and claims register, red-flags deviations immediately, and can hold release until written closure is recorded. This control log is shared across strategy, creative, production, social, and media teams so rework is prevented before assets progress.",
                "q_cr_tech_2": "We would protect the launch calendar through parallel workstreams, pre-booked production and post capacity, a milestone tracker shared with the buyer, and clear approval SLAs by stage. Critical dependencies are buyer approvals, claims wording freeze, and market adaptation decisions; each has an owner, target turnaround, and recovery path. If a delay appears, we trigger same-day escalation and preserve launch dates by separating non-critical local adaptations from the master asset path while keeping film, social, and compliance reviews synchronized.",
                "q_cr_tech_3": "Our strategy and creative approach starts with caregiver trust plus kid appeal, then builds one claims-safe master campaign idea that travels from flagship film into social, retail, and launch governance assets. We would define audience segments, message roles, and creative territories before development begins, then translate the chosen route into a modular toolkit so the same strategic spine carries into launch assets without resetting core approvals.",
                "q_cr_tech_4": "We would handle TVC development and production through one integrated film workstream covering concept development, script and storyboard, production-board approval, shoot planning, post-production, and delivery of the master film with paid-media cutdowns. One lead producer owns schedule and handoffs, while compliance reviewers stay active before shoot lock, at rough cut, and at final release. This gives the buyer one controlled path from concept to delivered hero film and cutdowns without fragmented ownership.",
            },
            "pricing_rows": [
                ("li_1", "Strategy & Creative Development", "Yes", "USD", "345000", "Includes audience segmentation, messaging framework, and global toolkit."),
                ("li_2", "TVC Development", "Yes", "USD", "225000", "Includes concepting, script, storyboard, and pre-production creative."),
                ("li_3", "TVC Production", "Yes", "USD", "705000", "Excludes celebrity talent, special music rights, and extraordinary travel."),
                ("li_4", "Social Organic Content", "Yes", "USD", "165000", "Includes launch-window calendar plus asset adaptation."),
                ("li_5", "Social Paid Media Planning", "Yes", "USD", "135000", "Includes audience, channel, and phasing plan."),
                ("li_6", "Social Paid Media Buying & Optimization", "Yes", "USD", "275000", "Platform media spend excluded; fee covers activation and optimization."),
                ("li_7", "Kids Advertising & Claims Compliance Review", "Yes", "USD", "155000", "Includes central review plus market counsel coordination."),
                ("li_8", "Launch Program Management", "Yes", "USD", "210000", "Includes program office, reporting, and launch governance."),
            ],
        },
        {
            "slug": "02_bluepeak_mediaworks_submission",
            "final_format": "docx",
            "vendor_name": "BluePeak MediaWorks",
            "scenario": "Designed to stay technically neck-and-neck with SparkBridge while losing commercially because the normalized total is higher.",
            "contact_block": "Prepared by: BluePeak MediaWorks Europe-APAC Team | Contact: Javier Mehra | Currency: EUR",
            "agency_overview": "BluePeak MediaWorks operates as a regional network model with shared strategy, creative, media, and regulatory resources across Europe and APAC. For this launch, BluePeak is positioning itself as a cross-market coordination partner with strong adaptation discipline and media integration, but with a more premium commercial model than the benchmark vendor.",
            "strategic_point_of_view": "We believe the launch should be built around one claims-safe family-health platform that can flex by market while preserving a single strategic spine across film, social, and activation.",
            "selected_relevant_work": [
                "Regional children’s dairy campaign rolled out with one central asset system and local market adaptation packs.",
                "Consumer health launch using synchronized creative, media planning, and compliance review across EMEA and Asia.",
            ],
            "answers": {
                "q_cr_mac_1": "Yes. Child-directed advertising support would be provided by our Youth Audience Strategy Lead and the regional policy reviewers assigned to the account.",
                "q_cr_mac_2": "Yes. Claims review support would be provided through our central regulatory desk with local counsel review in India, the UK, and key launch markets.",
                "q_cr_mac_3": "Javier Mehra, Client Partner, javier.mehra@bluepeakmediaworks.com. Javier would be the accountable engagement lead for scope, budget, and cross-market alignment.",
                "q_cr_mac_4": "Yes. We propose a weekly client steering call, Monday delivery huddle, and a formal approval tracker owned by the PMO lead. Material risks move from workstream leads to the client partner and then to a joint escalation forum within one business day.",
                "q_cr_mac_5": "Achievable as issued. Standard buyer approvals within the agreed turnaround windows will be sufficient; no exceptional dependencies or scope caveats are required beyond normal launch governance inputs.",
                "q_cr_tech_1": "Our compliance operating model places checkpoints at briefing, audience and message architecture approval, creative territory selection, storyboard approval, final script, pre-shoot legal lock, rough cut, final cut, and market adaptation release. One compliance lead owns the child-directed advertising and claims register, red-flags deviations immediately, and can hold release until written closure is recorded. This control log is shared across strategy, creative, production, social, and media teams so rework is prevented before assets progress.",
                "q_cr_tech_2": "We would protect the launch calendar through parallel workstreams, pre-booked production and post capacity, a milestone tracker shared with the buyer, and clear approval SLAs by stage. Critical dependencies are buyer approvals, claims wording freeze, and market adaptation decisions; each has an owner, target turnaround, and recovery path. If a delay appears, we trigger same-day escalation and preserve launch dates by separating non-critical local adaptations from the master asset path while keeping film, social, and compliance reviews synchronized.",
                "q_cr_tech_3": "Our strategy and creative approach starts with caregiver trust plus kid appeal, then builds one claims-safe master campaign idea that travels from flagship film into social, retail, and launch governance assets. We would define audience segments, message roles, and creative territories before development begins, then translate the chosen route into a modular toolkit so the same strategic spine carries into launch assets without resetting core approvals.",
                "q_cr_tech_4": "We would handle TVC development and production through one integrated film workstream covering concept development, script and storyboard, production-board approval, shoot planning, post-production, and delivery of the master film with paid-media cutdowns. One lead producer owns schedule and handoffs, while compliance reviewers stay active before shoot lock, at rough cut, and at final release. This gives the buyer one controlled path from concept to delivered hero film and cutdowns without fragmented ownership.",
            },
            "pricing_rows": [
                ("li_1", "Strategy & Creative Development", "Yes", "EUR", "365000", "Regional adaptation planning included."),
                ("li_2", "TVC Development", "Yes", "EUR", "238000", "Concept, script, and storyboard included."),
                ("li_3", "TVC Production", "Yes", "EUR", "760000", "Production and post-production included."),
                ("li_4", "Social Organic Content", "Yes", "EUR", "182000", "Regional transcreation priced for priority launch markets only."),
                ("li_5", "Social Paid Media Planning", "Yes", "EUR", "150000", "Paid media strategy and phasing included."),
                ("li_6", "Social Paid Media Buying & Optimization", "Yes", "EUR", "302000", "Media spend excluded from fee."),
                ("li_7", "Kids Advertising & Claims Compliance Review", "Yes", "EUR", "176000", "Central plus local counsel review included."),
                ("li_8", "Launch Program Management", "Yes", "EUR", "242000", "PMO and reporting included."),
            ],
        },
        {
            "slug": "03_nimblenest_creative_submission",
            "final_format": "pdf",
            "vendor_name": "NimbleNest Creative",
            "scenario": "Designed to pass the MAC checks but fail the technical gate because the compliance and launch-control answers are too thin for the cutoff-backed criteria.",
            "contact_block": "Prepared by: NimbleNest Creative Studio | Contact: Priya Nair | Currency: USD",
            "agency_overview": "NimbleNest Creative is a smaller independent studio built for lean strategy, fast creative development, and tight production control. The proposal emphasizes agility, compact governance, and focused senior attention rather than broad network infrastructure.",
            "strategic_point_of_view": "Our view is that the launch should use a clear, emotionally resonant idea that can be approved quickly, adapted efficiently, and executed without unnecessary process overhead.",
            "selected_relevant_work": [
                "Fast-turn youth beverage campaign developed with a lean internal team and external compliance counsel.",
                "Compact digital-first launch for a family nutrition brand with one hero concept and rapid adaptation assets.",
            ],
            "answers": {
                "q_cr_mac_1": "Yes. Support would come from our youth and family brand team.",
                "q_cr_mac_2": "Yes. Claims review would be supported by external legal counsel retained by NimbleNest for this assignment.",
                "q_cr_mac_3": "Priya Nair, Business Director, priya.nair@nimblenestcreative.com. Priya would act as the primary contact and delivery owner.",
                "q_cr_mac_4": "Yes. We would hold a weekly buyer check-in, keep a shared action list, and escalate urgent issues to the business director and buyer lead as needed.",
                "q_cr_mac_5": "Achievable with dependencies. The timeline depends on quick buyer feedback, one-round approval for the core concept, and legal inputs being consolidated rather than staggered.",
                "q_cr_tech_1": "Our team would brief external counsel at concept stage, then review scripts and social copy before release. We would maintain a simple claims checklist and ask the buyer to confirm any new product statements before assets go live. The model is intentionally lightweight and does not rely on a full shared control register across all workstreams.",
                "q_cr_tech_2": "We would move quickly by keeping a small decision team, daily internal stand-ups, and limited creative route exploration. If a delay occurs, we would prioritize the film and highest-impact social assets first, but we do not propose a formal multi-stage approval calendar, detailed recovery path, or separate escalation routine beyond the weekly buyer check-in.",
                "q_cr_tech_3": "Our strategy and creative approach is built around a simple 'daily strength for growing kids' idea translated into fast-moving film and social content. We would keep the concept system compact so approvals and adaptations can happen with minimal process overhead.",
                "q_cr_tech_4": "We would approach TVC delivery with a lean production model: one hero concept, one efficient pre-production cycle, a tightly managed shoot, and streamlined post-production for master film and paid cutdowns. The trade-off is less redundancy and less room for late-stage change than larger network agencies may offer.",
            },
            "pricing_rows": [
                ("li_1", "Strategy & Creative Development", "Yes", "USD", "250000", "Lean strategy sprint and creative system."),
                ("li_2", "TVC Development", "Yes", "USD", "150000", "Bundled with early pre-production creative."),
                ("li_3", "TVC Production", "Yes", "USD", "520000", "Production and post-production to standard commercial quality."),
                ("li_4", "Social Organic Content", "Yes", "USD", "110000", "Launch window organic content pack."),
                ("li_5", "Social Paid Media Planning", "Yes", "USD", "85000", "Paid social planning."),
                ("li_6", "Social Paid Media Buying & Optimization", "Yes", "USD", "165000", "Platform spend excluded from the activation fee."),
                ("li_7", "Kids Advertising & Claims Compliance Review", "Yes", "USD", "70000", "External legal support limited to two review rounds."),
                ("li_8", "Launch Program Management", "Yes", "USD", "130000", "Lean coordination layer."),
            ],
        },
        {
            "slug": "04_childsafe_integrated_submission",
            "final_format": "docx",
            "vendor_name": "ChildSafe Integrated",
            "scenario": "Designed to clear the technical gate strongly and compete as the quality-led option, but to lose official QCBS on a higher commercial total.",
            "contact_block": "Prepared by: ChildSafe Integrated Advisory + Studio | Contact: Michael Osei | Currency: USD",
            "agency_overview": "ChildSafe Integrated combines advisory, creative operations, and claims-review discipline with a compliance-first operating model. The proposed team is intentionally heavier on governance and risk control than on experimental creative exploration.",
            "strategic_point_of_view": "We believe a kids-health launch succeeds when the creative system is designed around safety, reviewability, and controlled adaptation from the start, instead of treating compliance as a late-stage checkpoint.",
            "selected_relevant_work": [
                "Claims-sensitive pediatric nutrition campaign with embedded review gates from briefing through final release.",
                "Multi-stakeholder launch program where legal, studio, and media teams worked from one control register and approval rhythm.",
            ],
            "answers": {
                "q_cr_mac_1": "Yes. Support would be delivered by our child-directed communications compliance lead together with the creative governance office.",
                "q_cr_mac_2": "Yes. Claims review would be handled by our nutrition claims counsel and market regulatory coordination team.",
                "q_cr_mac_3": "Michael Osei, Managing Program Lead, michael.osei@childsafeintegrated.com. Michael would own delivery governance, compliance quality, and executive issue resolution.",
                "q_cr_mac_4": "Yes. We propose a disciplined governance model: weekly steering committee, twice-weekly approvals board during production peaks, written decision logs, and named escalation owners across buyer, legal, studio, and media teams.",
                "q_cr_mac_5": "Achievable with dependencies. The calendar depends on timely buyer attendance at approval forums, stable claims language after concept freeze, and rapid local-market sign-off once the master assets are released.",
                "q_cr_tech_1": "Our compliance operating model is the strongest part of our offer. We embed claims counsel from briefing through final release, maintain a child-safety and claims control register, and require red-amber-green clearance before any strategy, creative, script, film, social, or media asset moves to the next stage. Exceptions cannot be closed informally; they require written owner sign-off and tracked closure before release.",
                "q_cr_tech_2": "We protect launch speed through a gated but predictable operating rhythm. Each milestone has a pre-read, approval owner, fallback option, and recovery path, and the approval board is visible against the critical path from kickoff to launch. Where a task threatens timing, we separate non-critical local adaptations from the master release, deploy pre-cleared backup assets, and escalate within the same day so the campaign can still launch on time.",
                "q_cr_tech_3": "Our strategic and creative approach is intentionally claims-safe first, then creatively expressive within those boundaries. The work would focus on a trust-building hero message, disciplined audience and message architecture, tightly controlled script language, and modular adaptation into social and paid media formats so the master idea stays usable across markets.",
                "q_cr_tech_4": "Our TVC approach uses close coupling between concept, script, production planning, shoot readiness, and post-production review. Regulatory and claims reviewers stay active through storyboard, shoot prep, rough cut, and final delivery so the master film and cutdowns remain launch-ready without late-stage rework or fragmented handoffs.",
            },
            "pricing_rows": [
                ("li_1", "Strategy & Creative Development", "Yes", "USD", "395000", "Compliance-first strategic development."),
                ("li_2", "TVC Development", "Yes", "USD", "270000", "Script and storyboard with regulatory review embedded."),
                ("li_3", "TVC Production", "Yes", "USD", "835000", "Music rights, celebrity usage, and extraordinary travel excluded."),
                ("li_4", "Social Organic Content", "Yes", "USD", "190000", "Organic adaptation pack included."),
                ("li_5", "Social Paid Media Planning", "Yes", "USD", "168000", "Planning and phasing included."),
                ("li_6", "Social Paid Media Buying & Optimization", "Yes", "USD", "295000", "Working media spend excluded."),
                ("li_7", "Kids Advertising & Claims Compliance Review", "Yes", "USD", "248000", "Senior counsel and market alignment included."),
                ("li_8", "Launch Program Management", "Yes", "USD", "245000", "Program controls and executive reporting included."),
            ],
        },
        {
            "slug": "05_launchloop_collective_submission",
            "final_format": "pdf",
            "vendor_name": "LaunchLoop Collective",
            "scenario": "Designed as the clear MAC failure: cheapest-looking bid, but rejected because claims-review capability is not included and the stated timeline is not achievable.",
            "contact_block": "Prepared by: LaunchLoop Collective | Contact: Anita Rao | Currency: INR",
            "agency_overview": "LaunchLoop Collective is a lean creative and activation shop designed for fast-moving campaigns with a small core team. The proposal is commercially aggressive and intentionally lighter on specialist governance infrastructure than larger competitors.",
            "strategic_point_of_view": "Our view is that the launch should prioritize a sharp, digital-first campaign system that can be produced efficiently and scaled through focused deliverables rather than a broad, high-overhead rollout model.",
            "selected_relevant_work": [
                "Lean social-first campaign for a mass consumer brand delivered on compressed timelines with a small account team.",
                "Mid-scale film and content launch optimized for cost efficiency and faster approval cycles.",
            ],
            "answers": {
                "q_cr_mac_1": "Yes. Support for child-directed advertising would be coordinated by our campaign operations lead and creative supervisor.",
                "q_cr_mac_2": "No. We do not maintain a dedicated claims review capability and would require the buyer to appoint external claims counsel for final approval.",
                "q_cr_mac_3": "Anita Rao, Founder and Account Lead, anita.rao@launchloopcollective.in. Anita would oversee commercial coordination and buyer communication.",
                "q_cr_mac_4": "Yes. Our governance approach is lightweight: a weekly update call, milestone tracker, and direct escalation to Anita for urgent decisions.",
                "q_cr_mac_5": "Not achievable. The stated launch dates would require shortened approval rounds, simplified production scope, and direct buyer turnaround within 24 hours. Without those conditions, we would expect slippage against the current calendar.",
                "q_cr_tech_1": "We would manage compliance by routing scripts and claims language to buyer-appointed counsel before release. Internally we can maintain a working checklist, but the formal review responsibility would sit outside our team. This keeps cost low but also means the buyer would need to manage final claim clearance more actively.",
                "q_cr_tech_2": "Our speed plan depends on minimizing iterations and holding one decision-maker per milestone. If approvals expand or additional markets are added, we would recommend reducing launch deliverables or staggering the rollout because we do not have reserve capacity built into the base plan.",
                "q_cr_tech_3": "Our strategy and creative approach is built around a bold, digital-first campaign platform that can be produced efficiently with a lean team. It is best suited to a narrower launch scope and faster-turn content model rather than a heavily governed multi-market program.",
                "q_cr_tech_4": "Our TVC approach focuses on a compact production model with a single concept route, limited revision cycles, and a streamlined shoot and edit process. It can deliver efficient output, but it is less suited to complex multi-market governance and extensive rework requirements.",
            },
            "pricing_rows": [
                ("li_1", "Strategy & Creative Development", "Yes", "INR", "18000000", "Lean strategic development."),
                ("li_2", "TVC Development", "Yes", "INR", "9500000", "Concept and pre-production creative included."),
                ("li_3", "TVC Production", "Yes", "INR", "34000000", "Production and edit included."),
                ("li_4", "Social Organic Content", "Yes", "INR", "7200000", "Organic launch content included."),
                ("li_5", "Social Paid Media Planning", "Yes", "INR", "4800000", "Paid planning included."),
                ("li_6", "Social Paid Media Buying & Optimization", "Yes", "INR", "8900000", "Paid media spend, translation, and talent rights excluded."),
                ("li_7", "Kids Advertising & Claims Compliance Review", "No", "INR", "0", "Not included; buyer-appointed counsel required."),
                ("li_8", "Launch Program Management", "Yes", "INR", "6300000", "Lean PM support included."),
            ],
        },
    ]


def render_vendor_markdown(*, rfq: dict, vendor_pack: dict, vendor: dict) -> str:
    questions = vendor_pack["questions"]
    lines: list[str] = []
    lines.append(f"# {vendor['vendor_name']} Submission")
    lines.append("")
    lines.append(vendor["contact_block"])
    lines.append("")
    lines.append(f"RFQ Reference: {rfq['general_info']['rfq_code']} - {rfq['general_info']['subject']}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        "This response covers the archived generated questionnaire, the requested service line items, "
        "and the commercial pricing schedule expected in the RFQ package."
    )
    lines.append("")
    lines.append("## Agency Overview")
    lines.append("")
    lines.append(vendor["agency_overview"])
    lines.append("")
    lines.append("## Strategic Point of View")
    lines.append("")
    lines.append(vendor["strategic_point_of_view"])
    lines.append("")
    lines.append("## Selected Relevant Work")
    lines.append("")
    for credential in vendor["selected_relevant_work"]:
        lines.append(f"- {credential}")
    lines.append("")
    lines.append("## Questionnaire Responses")
    lines.append("")
    for question in questions:
        lines.append(f"### {question['id']}")
        lines.append("")
        lines.append(f"**Question:** {question['text']}")
        lines.append("")
        lines.append(f"**Response:** {vendor['answers'][question['id']]}")
        lines.append("")
    lines.append("## Commercial Pricing Schedule")
    lines.append("")
    lines.append("| Line Item Ref | Line Item Name | Included in Quote | Currency | Total Price | Exclusions or Assumptions |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in vendor["pricing_rows"]:
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} |")
    lines.append("")
    return "\n".join(lines)


def render_vendor_html(*, markdown: str, vendor: dict) -> str:
    paragraphs: list[str] = []
    in_pricing_table = False
    pricing_rows: list[list[str]] = []

    for line in markdown.splitlines():
        if line.startswith("| Line Item Ref "):
            in_pricing_table = True
            continue
        if line.startswith("| ---"):
            continue
        if in_pricing_table and line.startswith("|"):
            pricing_rows.append([cell.strip() for cell in line.strip("|").split("|")])
            continue

        if line.startswith("# "):
            paragraphs.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            paragraphs.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            paragraphs.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("**Question:** "):
            paragraphs.append(f"<p><strong>Question:</strong> {html.escape(line[len('**Question:** '):])}</p>")
        elif line.startswith("**Response:** "):
            paragraphs.append(f"<p><strong>Response:</strong> {html.escape(line[len('**Response:** '):])}</p>")
        elif line.strip():
            paragraphs.append(f"<p>{html.escape(line)}</p>")

    pricing_table = build_html_table(
        headers=[
            "Line Item Ref",
            "Line Item Name",
            "Included in Quote",
            "Currency",
            "Total Price",
            "Exclusions or Assumptions",
        ],
        rows=pricing_rows,
    )

    body = "\n".join(paragraphs)
    body = body.replace("<h2>Commercial Pricing Schedule</h2>", "<h2>Commercial Pricing Schedule</h2>\n" + pricing_table)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{html.escape(vendor['vendor_name'])} Submission</title>
  <style>
    @page {{ size: A4; margin: 0.45in; }}
    body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.35; margin: 24px; }}
    h1 {{ font-size: 18pt; margin-bottom: 8px; }}
    h2 {{ font-size: 14pt; margin-top: 18px; margin-bottom: 8px; }}
    h3 {{ font-size: 11.5pt; margin-top: 12px; margin-bottom: 6px; }}
    p {{ margin: 4px 0 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 9.5pt; margin: 8px 0 14px; }}
    th, td {{ border: 1px solid #999; padding: 4px 6px; vertical-align: top; text-align: left; }}
    th {{ background: #efefef; }}
    tr {{ page-break-inside: avoid; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def build_html_table(*, headers: list[str], rows: list[list[str]]) -> str:
    header_html = "".join(f"<th>{html.escape(item)}</th>" for item in headers)
    row_html = []
    for row in rows:
        row_html.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>")
    return "<table><thead><tr>" + header_html + "</tr></thead><tbody>" + "".join(row_html) + "</tbody></table>"


def render_pdf_from_html(*, html_path: Path, output_path: Path) -> None:
    chrome_binary = find_chrome_binary()
    subprocess.run(
        [
            chrome_binary,
            "--headless",
            "--disable-gpu",
            f"--print-to-pdf={output_path}",
            f"file://{html_path}",
        ],
        check=True,
    )


def render_docx_from_html(*, html_path: Path, output_path: Path) -> None:
    textutil_binary = shutil.which("textutil")
    if not textutil_binary:
        raise FileNotFoundError("The macOS textutil binary is required to render sample DOCX submissions.")
    subprocess.run(
        [
            textutil_binary,
            "-convert",
            "docx",
            str(html_path),
            "-output",
            str(output_path),
        ],
        check=True,
    )


def find_chrome_binary() -> str:
    for candidate in (
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        DEFAULT_CHROME_BINARY,
    ):
        if candidate and Path(candidate).exists():
            return candidate
    raise FileNotFoundError(
        "A Chrome/Chromium binary is required to render the sample PDF submissions."
    )


def write_readme(vendors: list[dict]) -> None:
    lines = [
        "# Vendor Submission Examples",
        "",
        "This folder contains five manually-authored vendor response examples built from the sample RFQ and the archived generated questionnaire saved in `rfq-package/`.",
        "The final `submissions/` set is intentionally mixed across PDF and DOCX so the demo exercises more than one vendor document format.",
        "",
        "## Contents",
        "",
        "- `rfq-package/`: sample RFQ snapshot, archived generated rubric, and vendor-facing package reference",
        "- `source/`: saved markdown source used to create the final files",
        "- `submissions/`: uploadable vendor response files, one final artifact per vendor",
        "",
        "## Vendor Set",
        "",
    ]
    for vendor in vendors:
        extension = vendor["final_format"]
        lines.append(f"- `{vendor['slug']}.{extension}` - {vendor['vendor_name']}: {vendor['scenario']}")
    lines.append("")
    lines.append("The examples are intentionally varied in quality, pricing currency, assumptions, and compliance posture so they can be used to test technical gating, commercial normalization, and explainability flows.")
    lines.append("")
    (ROOT / "README.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
