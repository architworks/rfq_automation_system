from __future__ import annotations

import html
import json
import shutil
import subprocess
import textwrap
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

    rfq = json.loads((RFQ_DIR / "sample-rfq.json").read_text())
    package = json.loads((RFQ_DIR / "generated-rubric-package.json").read_text())

    write_reference_files(rfq=rfq, package=package)

    vendors = build_vendor_profiles()
    for vendor in vendors:
        markdown = render_vendor_markdown(rfq=rfq, package=package, vendor=vendor)
        markdown_path = SOURCE_DIR / f"{vendor['slug']}.md"
        markdown_path.write_text(markdown)

        if vendor["output_format"] == "docx":
            html_path = SOURCE_DIR / f"{vendor['slug']}.html"
            html_path.write_text(render_vendor_html(markdown=markdown, vendor=vendor))
            subprocess.run(
                [
                    "textutil",
                    "-convert",
                    "docx",
                    str(html_path),
                    "-output",
                    str(SUBMISSIONS_DIR / f"{vendor['slug']}.docx"),
                ],
                check=True,
            )
        elif vendor["output_format"] == "pdf":
            html_path = SOURCE_DIR / f"{vendor['slug']}.html"
            html_path.write_text(render_vendor_html(markdown=markdown, vendor=vendor))
            render_pdf_from_html(
                html_path=html_path,
                output_path=SUBMISSIONS_DIR / f"{vendor['slug']}.pdf",
            )
        else:
            raise ValueError(f"Unsupported output format: {vendor['output_format']}")

    write_readme(vendors)


def write_reference_files(*, rfq: dict, package: dict) -> None:
    questions = package["questions"]
    schedules = package["schedules"]
    criteria = package["criteria"]

    lines: list[str] = []
    lines.append("# Vendor-Facing RFQ Package Snapshot")
    lines.append("")
    lines.append("This package uses the prefilled sample RFQ plus the live AI-generated questionnaire.")
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
    lines.append("## AI-Generated Questionnaire")
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
    lines.append("## Known AI Rubric Gap")
    lines.append("")
    lines.append(
        "The generated rubric also contains a technical criterion titled "
        f"`{criteria[-1]['title']}` (`{criteria[-1]['id']}`) without its own vendor-facing question. "
        "The sample vendor submissions therefore include an additional short strategy and creative response section grounded in the RFQ scope and line item 1 so that the likely intent of that criterion is still represented in the response set."
    )
    lines.append("")

    (RFQ_DIR / "vendor-facing-rfq-package.md").write_text("\n".join(lines))


def build_vendor_profiles() -> list[dict]:
    return [
        {
            "slug": "01_sparkbridge_global_submission",
            "vendor_name": "SparkBridge Global",
            "output_format": "docx",
            "contact_block": "Prepared by: SparkBridge Global Launch Practice | Contact: Sarah Lin | Currency: USD",
            "answers": {
                "q_m1": "Yes. Support will be provided by our Kids Marketing Compliance Cell working alongside the global creative and channel leads.",
                "q_m2": "Yes. Claims review support will be provided by our in-house Health Claims and Regulatory Practice with escalation to market counsel where needed.",
                "q_m3": "Sarah Lin, Global Launch Director. Sarah would own executive delivery, decision coordination, and buyer-facing accountability across all workstreams.",
                "q_m4": "We would run a weekly steering committee, twice-weekly cross-functional operations review, and a 24-hour escalation path for claims, approvals, and production risks. Buyer sign-off would follow a defined approve/revise/escalate route.",
                "q_m5": "Achievable.",
                "q_m6": "Key dependencies are final claims matrix approval by 14 May, buyer response windows within 48 hours, product sample access for production planning, and timely market adaptation inputs from regional brand teams.",
                "q_t1": "Our compliance operating model places a compliance checkpoint at briefing, creative territory selection, storyboard approval, final script, rough cut, final cut, and market adaptation release. The compliance lead signs off all child-directed claims language, maintains a red-flag register, and can stop release if unresolved issues remain.",
                "q_t2": "We would protect the launch calendar through parallel workstreams, pre-booked production capacity, a milestone tracker shared with the buyer, and an approval SLA pack. Delays trigger same-day escalation with path-to-green options such as alternate edit routes, pre-cleared modular social assets, and staggered release priorities.",
            },
            "additional_strategy": "Our strategy and creative approach starts with caregiver trust plus kid appeal, then builds one master campaign idea that travels from flagship film into social, retail, and launch governance assets. We would use modular creative components so claims-safe messaging can be adapted quickly without resetting the full approval cycle.",
            "pricing_rows": [
                ("li_1", "Strategy & Creative Development", "Standalone", "USD 420,000", "Includes research synthesis, master messaging, and global toolkit."),
                ("li_2", "TVC Development", "Standalone", "USD 280,000", "Includes concepting, script, storyboard, and pre-production creative."),
                ("li_3", "TVC Production", "Standalone", "USD 860,000", "Includes shoot, edit, sound mix, color, and standard cutdowns."),
                ("li_4", "Social Organic Content", "Standalone", "USD 220,000", "Monthly calendar plus asset adaptation for launch window."),
                ("li_5", "Social Paid Media Planning", "Standalone", "USD 180,000", "Audience, channel, and budget planning."),
                ("li_6", "Social Paid Media Buying & Optimization", "Standalone", "USD 360,000", "Activation and optimization fees; excludes platform media spend."),
                ("li_7", "Kids Advertising & Claims Compliance Review", "Standalone", "USD 190,000", "Central review plus market counsel coordination."),
                ("li_8", "Launch Program Management", "Standalone", "USD 270,000", "Program office, reporting, and master launch governance."),
            ],
            "assumptions_rows": [
                ("Paid media platform spend is excluded.", "li_5, li_6", "Media budgets are buyer-funded and pass through directly."),
                ("Music talent, celebrity rights, and extraordinary travel are excluded.", "li_3", "Only incurred if buyer chooses premium production options."),
            ],
        },
        {
            "slug": "02_bluepeak_mediaworks_submission",
            "vendor_name": "BluePeak MediaWorks",
            "output_format": "pdf",
            "contact_block": "Prepared by: BluePeak MediaWorks Europe-APAC Team | Contact: Javier Mehra | Currency: EUR",
            "answers": {
                "q_m1": "Yes. Child-directed advertising support would be provided by our Youth Audience Strategy Lead and the regional policy reviewers assigned to the account.",
                "q_m2": "Yes. Claims review support would be provided through our central regulatory desk with local counsel review in India, the UK, and key launch markets.",
                "q_m3": "Javier Mehra, Client Partner. Javier would be the accountable engagement lead for scope, budget, and cross-market alignment.",
                "q_m4": "We propose a weekly client steering call, Monday delivery huddle, and a formal approval tracker owned by the PMO lead. Material risks move from workstream leads to the client partner and then to a joint escalation forum within one business day.",
                "q_m5": "Achievable.",
                "q_m6": "The plan assumes weekly buyer decision windows, claims wording freeze before final film edit, and prompt regional feedback on social adaptations. Media buying activation also depends on market account access by the agreed cutover date.",
                "q_t1": "BluePeak uses a layered compliance model: message architecture review before creative build, pre-shoot claims verification, edit-stage compliance review, and final market release sign-off. We use one control log across creative, social, and media teams so that claims-safe language stays consistent through production and launch.",
                "q_t2": "We would manage speed by locking the decision calendar upfront, parallelizing market adaptation work, and using a shared issue log with owner-by-owner turnaround targets. If delays appear, we prioritize milestone protection by moving non-critical adaptations behind the master asset release.",
            },
            "additional_strategy": "Our strategy and creative approach centers on a family-health launch platform that can flex by market while keeping one clear claims-safe promise. We would use a strong film-led master asset supported by social cutdowns and a phased paid media ramp-up.",
            "pricing_rows": [
                ("li_1", "Strategy & Creative Development", "Standalone", "EUR 315,000", "Regional adaptation planning included."),
                ("li_2", "TVC Development", "Standalone", "EUR 205,000", "Concept, script, storyboard."),
                ("li_3", "TVC Production", "Standalone", "EUR 740,000", "Production and post-production."),
                ("li_4", "Social Organic Content", "Bundled", "EUR 165,000", "Bundled with launch toolkit adaptation."),
                ("li_5", "Social Paid Media Planning", "Standalone", "EUR 140,000", "Paid media strategy and phasing."),
                ("li_6", "Social Paid Media Buying & Optimization", "Bundled", "EUR 285,000", "Bundled buying fee; media spend excluded."),
                ("li_7", "Kids Advertising & Claims Compliance Review", "Standalone", "EUR 160,000", "Central plus local counsel review."),
                ("li_8", "Launch Program Management", "Standalone", "EUR 235,000", "PMO and reporting."),
            ],
            "assumptions_rows": [
                ("Local language transcreation is priced only for priority launch markets.", "li_4, li_5", "Additional markets can be added by change request."),
                ("Platform media spend is excluded from service fees.", "li_6", "Buyer funds media budgets directly."),
            ],
        },
        {
            "slug": "03_nimblenest_creative_submission",
            "vendor_name": "NimbleNest Creative",
            "output_format": "docx",
            "contact_block": "Prepared by: NimbleNest Creative Studio | Contact: Priya Nair | Currency: USD",
            "answers": {
                "q_m1": "Yes. Support would come from our youth and family brand team.",
                "q_m2": "Yes. Claims review would be supported by external legal counsel retained by NimbleNest for this assignment.",
                "q_m3": "Priya Nair, Business Director. Priya would act as the primary contact and delivery owner.",
                "q_m4": "We would hold a weekly buyer check-in, keep a shared action list, and escalate urgent issues to the business director and buyer lead as needed.",
                "q_m5": "Achievable.",
                "q_m6": "The timeline depends on quick buyer feedback, one-round approval for the core concept, and legal inputs being consolidated rather than staggered.",
                "q_t1": "Our team would brief external counsel at concept stage, then review scripts and social copy before release. We would maintain a claims checklist and ask the buyer to confirm any new product statements before assets go live. Compared with larger networks, our model is lighter but intended to stay practical and fast.",
                "q_t2": "We would move quickly by keeping a small decision team, daily internal stand-ups, and limited creative route exploration. If a delay occurs, we would prioritize the film and highest-impact social assets first and push lower-priority variants behind launch.",
            },
            "additional_strategy": "Our strategy and creative approach is built around a simple 'daily strength for growing kids' idea translated into fast-moving film and social content. We would keep the concept system compact so approvals and adaptations can happen with minimal process overhead.",
            "pricing_rows": [
                ("li_1", "Strategy & Creative Development", "Standalone", "USD 250,000", "Lean strategy sprint and creative system."),
                ("li_2", "TVC Development", "Bundled", "USD 150,000", "Bundled with early pre-production creative."),
                ("li_3", "TVC Production", "Standalone", "USD 520,000", "Production and post-production to standard commercial quality."),
                ("li_4", "Social Organic Content", "Standalone", "USD 110,000", "Launch window organic content pack."),
                ("li_5", "Social Paid Media Planning", "Standalone", "USD 85,000", "Paid social planning."),
                ("li_6", "Social Paid Media Buying & Optimization", "Standalone", "USD 165,000", "Activation fee; platform spend excluded."),
                ("li_7", "Kids Advertising & Claims Compliance Review", "Bundled", "USD 70,000", "External legal support limited to two review rounds."),
                ("li_8", "Launch Program Management", "Standalone", "USD 130,000", "Lean coordination layer."),
            ],
            "assumptions_rows": [
                ("External legal review beyond two rounds is chargeable at cost.", "li_7", "Could extend timelines if major claim changes are introduced late."),
                ("Buyer to consolidate feedback into one approval package per milestone.", "li_1, li_2, li_3", "Multiple fragmented approval cycles may require schedule revision."),
            ],
        },
        {
            "slug": "04_childsafe_integrated_submission",
            "vendor_name": "ChildSafe Integrated",
            "output_format": "pdf",
            "contact_block": "Prepared by: ChildSafe Integrated Advisory + Studio | Contact: Michael Osei | Currency: USD",
            "answers": {
                "q_m1": "Yes. Support would be delivered by our child-directed communications compliance lead together with the creative governance office.",
                "q_m2": "Yes. Claims review would be handled by our nutrition claims counsel and market regulatory coordination team.",
                "q_m3": "Michael Osei, Managing Program Lead. Michael would own delivery governance, compliance quality, and executive issue resolution.",
                "q_m4": "We propose a disciplined governance model: weekly steering committee, twice-weekly approvals board during production peaks, written decision logs, and named escalation owners across buyer, legal, studio, and media teams.",
                "q_m5": "Achievable.",
                "q_m6": "The calendar depends on timely buyer attendance at approval forums, stable claims language after concept freeze, and rapid local-market sign-off once the master assets are released.",
                "q_t1": "Our compliance operating model is the strongest part of our offer. We embed claims counsel from briefing through final release, maintain a child-safety control register, and require red-amber-green clearance before any creative, script, or media asset moves to the next stage. Exceptions cannot be closed informally; they require written owner sign-off.",
                "q_t2": "We protect launch speed through a gated but predictable operating rhythm. Each milestone has a pre-read, approval owner, fallback option, and recovery path. Where a task threatens the critical path, we separate non-critical local adaptations from the master release so the campaign can still launch on time.",
            },
            "additional_strategy": "Our strategic and creative approach is intentionally claims-safe first, then creatively expressive within those boundaries. The work would focus on a trust-building hero message, tightly controlled script language, and modular adaptation into social and paid media formats.",
            "pricing_rows": [
                ("li_1", "Strategy & Creative Development", "Standalone", "USD 330,000", "Compliance-first strategic development."),
                ("li_2", "TVC Development", "Standalone", "USD 225,000", "Script and storyboard with regulatory review embedded."),
                ("li_3", "TVC Production", "Standalone", "USD 690,000", "Production and post-production."),
                ("li_4", "Social Organic Content", "Standalone", "USD 145,000", "Organic adaptation pack."),
                ("li_5", "Social Paid Media Planning", "Standalone", "USD 120,000", "Planning and phasing."),
                ("li_6", "Social Paid Media Buying & Optimization", "Standalone", "USD 210,000", "Buying fee; spend excluded."),
                ("li_7", "Kids Advertising & Claims Compliance Review", "Standalone", "USD 215,000", "Senior counsel and market alignment."),
                ("li_8", "Launch Program Management", "Standalone", "USD 185,000", "Program controls and executive reporting."),
            ],
            "assumptions_rows": [
                ("Music rights, celebrity usage, and extraordinary travel are excluded.", "li_3", "Only incurred if buyer selects premium production options."),
                ("Platform media spend is excluded.", "li_6", "Buyer or media agency funds working media directly."),
            ],
        },
        {
            "slug": "05_launchloop_collective_submission",
            "vendor_name": "LaunchLoop Collective",
            "output_format": "docx",
            "contact_block": "Prepared by: LaunchLoop Collective | Contact: Anita Rao | Currency: INR",
            "answers": {
                "q_m1": "Yes. Support for child-directed advertising would be coordinated by our campaign operations lead and creative supervisor.",
                "q_m2": "No. We do not maintain a dedicated claims review capability and would require the buyer to appoint external claims counsel for final approval.",
                "q_m3": "Anita Rao, Founder and Account Lead. Anita would oversee commercial coordination and buyer communication.",
                "q_m4": "Our governance approach is lightweight: a weekly update call, milestone tracker, and direct escalation to Anita for urgent decisions.",
                "q_m5": "Not achievable.",
                "q_m6": "The stated launch dates would require shortened approval rounds, simplified production scope, and direct buyer turnaround within 24 hours. Without those conditions, we would expect slippage against the current calendar.",
                "q_t1": "We would manage compliance by routing scripts and claims language to buyer-appointed counsel before release. Internally we can maintain a working checklist, but the formal review responsibility would sit outside our team. This keeps cost low but also means the buyer would need to manage final claim clearance more actively.",
                "q_t2": "Our speed plan depends on minimizing iterations and holding one decision-maker per milestone. If approvals expand or additional markets are added, we would recommend reducing launch deliverables or staggering the rollout because we do not have reserve capacity built into the base plan.",
            },
            "additional_strategy": "Our strategy and creative approach is built around a bold, digital-first campaign platform that can be produced efficiently with a lean team. It is best suited to a narrower launch scope and faster-turn content model rather than a heavily governed multi-market program.",
            "pricing_rows": [
                ("li_1", "Strategy & Creative Development", "Standalone", "INR 18,000,000", "Lean strategic development."),
                ("li_2", "TVC Development", "Bundled", "INR 9,500,000", "Concept and pre-production creative."),
                ("li_3", "TVC Production", "Standalone", "INR 34,000,000", "Production and edit."),
                ("li_4", "Social Organic Content", "Standalone", "INR 7,200,000", "Organic launch content."),
                ("li_5", "Social Paid Media Planning", "Standalone", "INR 4,800,000", "Paid planning."),
                ("li_6", "Social Paid Media Buying & Optimization", "Standalone", "INR 8,900,000", "Service fee only; media spend excluded."),
                ("li_7", "Kids Advertising & Claims Compliance Review", "Standalone", "INR 0", "Not included; buyer-appointed counsel required."),
                ("li_8", "Launch Program Management", "Standalone", "INR 6,300,000", "Lean PM support."),
            ],
            "assumptions_rows": [
                ("Buyer to appoint and pay external claims counsel.", "li_7", "This service is not included in our scope."),
                ("Buyer to accept compressed approval cycles and fewer revision rounds.", "li_2, li_3, li_4", "Without this, current timeline is not achievable."),
                ("Paid media spend, translation, and talent rights are excluded.", "li_5, li_6", "Additional external costs would be buyer-funded."),
            ],
        },
    ]


def render_vendor_markdown(*, rfq: dict, package: dict, vendor: dict) -> str:
    questions = package["questions"]
    lines: list[str] = []
    lines.append(f"# {vendor['vendor_name']} Submission")
    lines.append("")
    lines.append(vendor["contact_block"])
    lines.append("")
    lines.append(f"RFQ Reference: {rfq['general_info']['rfq_code']} - {rfq['general_info']['subject']}")
    lines.append("")
    lines.append("## Executive Note")
    lines.append("")
    lines.append(
        "This response covers the exact AI-generated questionnaire, the requested line items, and the commercial "
        "schedule expectations from the RFQ package."
    )
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
    lines.append("## Additional Strategy and Creative Response")
    lines.append("")
    lines.append(vendor["additional_strategy"])
    lines.append("")
    lines.append("## Commercial Pricing Schedule")
    lines.append("")
    lines.append("| Line Item Ref | Line Item Name | Pricing Treatment | Quoted Price | Notes |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in vendor["pricing_rows"]:
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} |")
    lines.append("")
    lines.append("## Exclusions and Assumptions Schedule")
    lines.append("")
    lines.append("| Exclusion or Assumption | Affected Line Item | Commercial Impact |")
    lines.append("| --- | --- | --- |")
    for row in vendor["assumptions_rows"]:
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} |")
    lines.append("")
    return "\n".join(lines)


def render_vendor_html(*, markdown: str, vendor: dict) -> str:
    paragraphs: list[str] = []
    in_pricing_table = False
    in_assumption_table = False
    pricing_rows: list[list[str]] = []
    assumption_rows: list[list[str]] = []

    for line in markdown.splitlines():
        if line.startswith("| Line Item Ref "):
            in_pricing_table = True
            in_assumption_table = False
            continue
        if line.startswith("| Exclusion or Assumption "):
            in_assumption_table = True
            in_pricing_table = False
            continue
        if line.startswith("| ---"):
            continue
        if in_pricing_table and line.startswith("|"):
            pricing_rows.append([cell.strip() for cell in line.strip("|").split("|")])
            continue
        if in_assumption_table and line.startswith("|"):
            assumption_rows.append([cell.strip() for cell in line.strip("|").split("|")])
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
        headers=["Line Item Ref", "Line Item Name", "Pricing Treatment", "Quoted Price", "Notes"],
        rows=pricing_rows,
    )
    assumptions_table = build_html_table(
        headers=["Exclusion or Assumption", "Affected Line Item", "Commercial Impact"],
        rows=assumption_rows,
    )

    body = "\n".join(paragraphs)
    body = body.replace("<h2>Commercial Pricing Schedule</h2>", "<h2>Commercial Pricing Schedule</h2>\n" + pricing_table)
    body = body.replace("<h2>Exclusions and Assumptions Schedule</h2>", "<h2>Exclusions and Assumptions Schedule</h2>\n" + assumptions_table)
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


def render_vendor_text(*, markdown: str) -> str:
    output: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            output.append("")
            continue
        if line.startswith("# "):
            title = line[2:]
            output.append(title.upper())
            output.append("=" * len(title))
            continue
        if line.startswith("## "):
            title = line[3:]
            output.append("")
            output.append(title.upper())
            output.append("-" * len(title))
            continue
        if line.startswith("### "):
            title = line[4:]
            output.append("")
            output.append(title)
            output.append("~" * len(title))
            continue
        if line.startswith("|"):
            output.append(raw_line)
            continue
        wrapped = textwrap.wrap(line, width=94) or [""]
        output.extend(wrapped)
    return "\n".join(output) + "\n"


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
        "This folder contains five manually-authored vendor response examples built from the sample RFQ and the live AI-generated questionnaire saved in `rfq-package/`.",
        "",
        "## Contents",
        "",
        "- `rfq-package/`: sample RFQ snapshot, generated questionnaire, and vendor-facing package reference",
        "- `source/`: markdown or intermediate source used to create the final files",
        "- `submissions/`: uploadable vendor response files",
        "",
        "## Vendor Set",
        "",
    ]
    for vendor in vendors:
        extension = "docx" if vendor["output_format"] == "docx" else "pdf"
        lines.append(f"- `{vendor['slug']}.{extension}` - {vendor['vendor_name']}")
    lines.append("")
    lines.append("The examples are intentionally varied in quality, pricing currency, assumptions, and compliance posture so they can be used to test technical gating, commercial normalization, and explainability flows.")
    lines.append("")
    (ROOT / "README.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
