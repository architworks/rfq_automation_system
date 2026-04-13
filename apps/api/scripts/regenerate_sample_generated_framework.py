from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from rfq_api.models import (
    DownloadMetadata,
    GovernanceInfo,
    LLMSettings,
    LockedFrameworkArtifact,
    OFFICIAL_AWARD_BASIS,
    ReasoningEffort,
)
from rfq_api.config import get_settings
from rfq_api.seeds import build_sample_rfq
from rfq_api.services.llm import OpenAIResponsesClient
from rfq_api.services.normalization_catalog import build_auto_comparison_settings
from rfq_api.services.rubric_generation import RubricGenerationService
from rfq_api.services.validation import validate_rubric_proposal
from rfq_api.services.vendor_pack import build_vendor_pack


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "src" / "rfq_api" / "seed_data" / "sample_generated_framework.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate and archive the sample generated framework.")
    parser.add_argument(
        "--reasoning-effort",
        default=ReasoningEffort.MEDIUM.value,
        choices=[effort.value for effort in ReasoningEffort],
        help="Reasoning effort to use for rubric generation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reasoning_effort = ReasoningEffort(args.reasoning_effort)

    print(f"Generating sample framework with reasoning effort: {reasoning_effort.value}")
    rfq_draft = build_sample_rfq()
    llm_client = OpenAIResponsesClient(get_settings())
    generation_service = RubricGenerationService(llm_client)

    rubric_proposal = generation_service.generate(
        rfq_draft,
        LLMSettings(reasoning_effort=reasoning_effort),
    )
    validation_issues = validate_rubric_proposal(rubric_proposal)

    artifact = LockedFrameworkArtifact(
        locked_at=datetime.now(UTC),
        rfq_snapshot=rfq_draft,
        rubric_snapshot=rubric_proposal,
        governance=GovernanceInfo(
            official_award_basis=OFFICIAL_AWARD_BASIS,
            technical_threshold_strategy="RFQ-specific threshold proposed by AI and approved by buyer before lock.",
            advisory_outputs=["LCS", "QBS", "RFQ-specific AI scenarios"],
            persistence_scope="Browser session plus in-memory backend session state with TTL-managed temp files.",
            rubric_warnings=validation_issues,
        ),
        download_metadata=DownloadMetadata(file_name="locked-framework-sample-generated.json"),
    )
    vendor_pack = build_vendor_pack(artifact)
    comparison_settings = build_auto_comparison_settings(rfq_draft.general_info.currency)

    payload = {
        "rfq_draft": rfq_draft.model_dump(mode="json"),
        "rubric_proposal": rubric_proposal.model_dump(mode="json"),
        "locked_artifact": artifact.model_dump(mode="json"),
        "vendor_pack": vendor_pack.model_dump(mode="json"),
        "comparison_settings": comparison_settings.model_dump(mode="json") if comparison_settings else None,
        "validation_issues": [issue.model_dump(mode="json") for issue in validation_issues],
        "generated_with": {
            "reasoning_effort": reasoning_effort.value,
            "generated_at": datetime.now(UTC).isoformat(),
        },
    }

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Archived sample framework written to {OUTPUT_PATH}")
    print(f"MAC count: {sum(1 for criterion in rubric_proposal.criteria if criterion.criterion_type == 'mac')}")
    print(f"Technical threshold: {rubric_proposal.aggregate_technical_threshold:g}")


if __name__ == "__main__":
    main()
