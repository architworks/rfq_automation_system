from __future__ import annotations

from ..models import OFFICIAL_AWARD_BASIS, CriterionType, RFQDraft, RubricProposal
from .llm import LLMClient


class RubricGenerationService:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def generate(self, rfq_draft: RFQDraft) -> RubricProposal:
        proposal = self._llm_client.generate_rubric(rfq_draft)
        return self._normalize(proposal)

    def _normalize(self, proposal: RubricProposal) -> RubricProposal:
        normalized = proposal.model_copy(deep=True)
        normalized.official_award_basis = OFFICIAL_AWARD_BASIS

        for criterion in normalized.criteria:
            if criterion.criterion_type == CriterionType.MAC:
                criterion.weight = None
                criterion.min_cutoff = None
                criterion.max_score = None
            elif criterion.criterion_type == CriterionType.COMMERCIAL:
                criterion.weight = None
                criterion.min_cutoff = None

        return normalized
