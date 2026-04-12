from __future__ import annotations

from collections import defaultdict

from ..models import (
    CriterionType,
    Question,
    RubricProposal,
    OFFICIAL_AWARD_BASIS,
)


def normalize_rubric_proposal(proposal: RubricProposal) -> RubricProposal:
    normalized = proposal.model_copy(deep=True)
    normalized.official_award_basis = OFFICIAL_AWARD_BASIS

    explicit_questions_by_id = {
        question.id: question.model_copy(deep=True)
        for question in normalized.questions
    }
    questions_by_criterion_id: dict[str, list[Question]] = defaultdict(list)
    for question in normalized.questions:
        for criterion_id in question.linked_criteria:
            questions_by_criterion_id[criterion_id].append(question.model_copy(deep=True))

    derived_questions: list[Question] = []
    used_question_ids: set[str] = set()

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

        if criterion.criterion_type == CriterionType.COMMERCIAL:
            criterion.vendor_question = None
            criterion.linked_question_ids = []
            continue

        vendor_question = criterion.vendor_question.model_copy(deep=True) if criterion.vendor_question else None
        if vendor_question is None:
            vendor_question = _backfill_vendor_question(
                criterion_id=criterion.id,
                linked_question_ids=criterion.linked_question_ids,
                explicit_questions_by_id=explicit_questions_by_id,
                questions_by_criterion_id=questions_by_criterion_id,
            )

        if vendor_question is None:
            criterion.linked_question_ids = []
            criterion.vendor_question = None
            continue

        vendor_question.id = _coerce_question_id(
            requested_id=vendor_question.id,
            criterion_id=criterion.id,
            used_question_ids=used_question_ids,
        )
        vendor_question.linked_criteria = [criterion.id]
        criterion.vendor_question = vendor_question
        criterion.linked_question_ids = [vendor_question.id]
        derived_questions.append(vendor_question.model_copy(deep=True))

    normalized.questions = derived_questions
    return normalized


def _backfill_vendor_question(
    *,
    criterion_id: str,
    linked_question_ids: list[str],
    explicit_questions_by_id: dict[str, Question],
    questions_by_criterion_id: dict[str, list[Question]],
) -> Question | None:
    for question_id in linked_question_ids:
        question = explicit_questions_by_id.get(question_id)
        if question is not None:
            return question.model_copy(deep=True)

    candidates = questions_by_criterion_id.get(criterion_id, [])
    if candidates:
        return candidates[0].model_copy(deep=True)

    return None


def _coerce_question_id(
    *,
    requested_id: str,
    criterion_id: str,
    used_question_ids: set[str],
) -> str:
    base_id = requested_id.strip() or f"q_{criterion_id}"
    if base_id not in used_question_ids:
        used_question_ids.add(base_id)
        return base_id

    suffix = 2
    while f"{base_id}_{suffix}" in used_question_ids:
        suffix += 1

    unique_id = f"{base_id}_{suffix}"
    used_question_ids.add(unique_id)
    return unique_id
