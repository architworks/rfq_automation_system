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
CANONICAL_FRAMEWORK_PATH = ROOT.parents[1] / "apps" / "api" / "src" / "rfq_api" / "seed_data" / "sample_generated_framework.json"
DEFAULT_CHROME_BINARY = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def main() -> None:
    RFQ_DIR.mkdir(parents=True, exist_ok=True)
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    clear_generated_outputs()

    framework = json.loads(CANONICAL_FRAMEWORK_PATH.read_text())
    rfq = framework["rfq_draft"]
    rubric = framework["rubric_proposal"]
    vendor_pack = framework["vendor_pack"]

    write_reference_files(framework=framework, rfq=rfq, rubric=rubric, vendor_pack=vendor_pack)

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


def write_reference_files(*, framework: dict, rfq: dict, rubric: dict, vendor_pack: dict) -> None:
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

    (RFQ_DIR / "sample-generated-framework.json").write_text(
        json.dumps(
            {
                "rfq_draft": rfq,
                "rubric_proposal": rubric,
                "locked_artifact": framework["locked_artifact"] if "locked_artifact" in framework else None,
                "vendor_pack": vendor_pack,
                "comparison_settings": framework.get("comparison_settings"),
                "validation_issues": framework.get("validation_issues", []),
                "generated_with": framework.get("generated_with"),
            },
            indent=2,
        )
    )
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
            "scenario": "Official QCBS benchmark: passes both MACs, clears the technical gate comfortably, and wins on the best comparable pricing among technically qualified vendors.",
        },
        {
            "slug": "02_bluepeak_mediaworks_submission",
            "final_format": "docx",
            "vendor_name": "BluePeak MediaWorks",
            "scenario": "Technically strong vendor that passes both MACs and the technical gate, but loses on higher normalized price after FX conversion.",
        },
        {
            "slug": "03_nimblenest_creative_submission",
            "final_format": "pdf",
            "vendor_name": "NimbleNest Creative",
            "scenario": "Passes the two MAC checks, but the lighter governance and weaker integration answers are intended to miss the technical gate.",
        },
        {
            "slug": "04_childsafe_integrated_submission",
            "final_format": "docx",
            "vendor_name": "ChildSafe Integrated",
            "scenario": "Quality-led vendor: passes MAC and should score very strongly technically, but is priced high enough to lose the official QCBS recommendation.",
        },
        {
            "slug": "05_launchloop_collective_submission",
            "final_format": "pdf",
            "vendor_name": "LaunchLoop Collective",
            "scenario": "Cheapest-looking bid, but designed to fail MAC because product claims review capability is explicitly unavailable.",
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
    list_items: list[str] = []
    table_headers: list[str] | None = None
    table_rows: list[list[str]] = []

    def flush_list() -> None:
        nonlocal list_items
        if not list_items:
            return
        paragraphs.append(
            "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in list_items) + "</ul>"
        )
        list_items = []

    def flush_table() -> None:
        nonlocal table_headers, table_rows
        if not table_headers:
            table_headers = None
            table_rows = []
            return
        paragraphs.append(build_html_table(headers=table_headers, rows=table_rows))
        table_headers = None
        table_rows = []

    for line in markdown.splitlines():
        if line.startswith("|") and line.endswith("|"):
            flush_list()
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if all(not cell or set(cell.replace(":", "")) <= {"-"} for cell in cells):
                continue
            if table_headers is None:
                table_headers = cells
            else:
                table_rows.append(cells)
            continue
        flush_table()

        if line.startswith("# "):
            flush_list()
            paragraphs.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            flush_list()
            paragraphs.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            flush_list()
            paragraphs.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("**Question:** "):
            flush_list()
            paragraphs.append(f"<p><strong>Question:</strong> {html.escape(line[len('**Question:** '):])}</p>")
        elif line.startswith("**Response:** "):
            flush_list()
            paragraphs.append(f"<p><strong>Response:</strong> {html.escape(line[len('**Response:** '):])}</p>")
        elif line.startswith("- "):
            list_items.append(line[2:])
        elif line.strip():
            flush_list()
            paragraphs.append(f"<p>{html.escape(line)}</p>")
        else:
            flush_list()

    flush_list()
    flush_table()

    body = "\n".join(paragraphs)
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
    ul {{ margin: 4px 0 10px 18px; padding-left: 14px; }}
    li {{ margin: 3px 0; }}
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
