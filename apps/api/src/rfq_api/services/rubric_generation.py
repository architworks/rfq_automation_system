from __future__ import annotations

from ..models import LLMSettings, OFFICIAL_AWARD_BASIS, CriterionType, RFQDraft, RubricProposal, ValidationIssue
from .llm import LLMClient
from .validation import validate_rubric_proposal


def normalize_rubric_proposal(proposal: RubricProposal) -> RubricProposal:
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
