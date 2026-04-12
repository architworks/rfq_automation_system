from __future__ import annotations

from ..models import LLMSettings, RFQDraft, RubricProposal, ValidationIssue
from .llm import LLMClient
from .rubric_normalization import normalize_rubric_proposal
from .validation import validate_rubric_proposal


class RubricGenerationService:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def generate(self, rfq_draft: RFQDraft, llm_settings: LLMSettings) -> RubricProposal:
        proposal = normalize_rubric_proposal(
            self._llm_client.generate_rubric(rfq_draft, llm_settings=llm_settings)
        )
        issues = validate_rubric_proposal(proposal)
        if not issues:
            return proposal

        repaired = normalize_rubric_proposal(
            self._llm_client.generate_rubric(
                rfq_draft,
                llm_settings=llm_settings,
                repair_feedback=issues,
            )
        )
        repaired_issues = validate_rubric_proposal(repaired)
        if not repaired_issues:
            return repaired

        return self._pick_best_candidate(
            primary=(proposal, issues),
            repaired=(repaired, repaired_issues),
        )

    @staticmethod
    def _pick_best_candidate(
        *,
        primary: tuple[RubricProposal, list[ValidationIssue]],
        repaired: tuple[RubricProposal, list[ValidationIssue]],
    ) -> RubricProposal:
        primary_proposal, primary_issues = primary
        repaired_proposal, repaired_issues = repaired
        if len(repaired_issues) <= len(primary_issues):
            return repaired_proposal
        return primary_proposal
