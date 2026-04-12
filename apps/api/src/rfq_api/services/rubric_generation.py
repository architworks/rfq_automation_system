from __future__ import annotations

from ..models import LLMSettings, OFFICIAL_AWARD_BASIS, CriterionType, RFQDraft, RubricProposal
from .llm import LLMClient, RubricGenerationError
from .validation import validate_rubric_proposal


class RubricGenerationService:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def generate(self, rfq_draft: RFQDraft, llm_settings: LLMSettings) -> RubricProposal:
        proposal = self._normalize(
            self._llm_client.generate_rubric(rfq_draft, llm_settings=llm_settings)
        )
        issues = validate_rubric_proposal(proposal)
        if not issues:
            return proposal

        repaired = self._normalize(
            self._llm_client.generate_rubric(
                rfq_draft,
                llm_settings=llm_settings,
                repair_feedback=issues,
            )
        )
        repaired_issues = validate_rubric_proposal(repaired)
        if repaired_issues:
            issue_summary = "; ".join(
                f"{issue.field}: {issue.message}"
                for issue in repaired_issues
            )
            raise RubricGenerationError(
                f"Rubric generation produced an invalid proposal after repair attempt: {issue_summary}"
            )
        return repaired

    def _normalize(self, proposal: RubricProposal) -> RubricProposal:
        normalized = proposal.model_copy(deep=True)
        normalized.official_award_basis = OFFICIAL_AWARD_BASIS

        for criterion in normalized.criteria:
            if criterion.criterion_type == CriterionType.MAC:
                criterion.weight = None
                criterion.min_cutoff = None
                criterion.max_score = None
                criterion.qualitative_scoring_guidance = None
            elif criterion.criterion_type == CriterionType.COMMERCIAL:
                criterion.weight = None
                criterion.min_cutoff = None
                criterion.qualitative_scoring_guidance = None

        return normalized
