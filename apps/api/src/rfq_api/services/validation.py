from __future__ import annotations

from math import isclose

from ..models import (
    OFFICIAL_AWARD_BASIS,
    Criterion,
    CriterionType,
    DeterministicScoringType,
    RubricProposal,
    ValidationIssue,
)


def validate_rubric_proposal(proposal: RubricProposal) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if proposal.official_award_basis != OFFICIAL_AWARD_BASIS:
        issues.append(
            ValidationIssue(
                field="official_award_basis",
                message=f"Official award basis must remain fixed to {OFFICIAL_AWARD_BASIS}.",
            )
        )

    if not 0 <= proposal.aggregate_technical_threshold <= 100:
        issues.append(
            ValidationIssue(
                field="aggregate_technical_threshold",
                message="Aggregate technical threshold must be between 0 and 100.",
            )
        )

    technical_weight_total = 0.0
    section_ids = {section.id for section in proposal.sections}
    question_ids = {question.id for question in proposal.questions}
    schedule_field_ids = {
        f"{schedule.id}.{column.id}"
        for schedule in proposal.response_schedules
        for column in schedule.columns
    }

    for index, criterion in enumerate(proposal.criteria):
        field_prefix = f"criteria[{index}]"
        issues.extend(
            _validate_criterion(
                criterion=criterion,
                field_prefix=field_prefix,
                known_section_ids=section_ids,
                known_question_ids=question_ids,
                known_schedule_field_ids=schedule_field_ids,
            )
        )
        if criterion.criterion_type in {
            CriterionType.TECHNICAL_CUTOFF_BACKED,
            CriterionType.TECHNICAL_SCORED_ONLY,
        }:
            technical_weight_total += criterion.weight or 0.0

    if not isclose(technical_weight_total, 100.0, abs_tol=0.01):
        issues.append(
            ValidationIssue(
                field="criteria",
                message="Technical scored and cutoff-backed criteria must total 100 points.",
            )
        )

    return issues


def _validate_criterion(
    *,
    criterion: Criterion,
    field_prefix: str,
    known_section_ids: set[str],
    known_question_ids: set[str],
    known_schedule_field_ids: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    is_technical = criterion.criterion_type != CriterionType.COMMERCIAL

    if criterion.section_id not in known_section_ids:
        issues.append(
            ValidationIssue(
                field=f"{field_prefix}.section_id",
                message="Criterion references an unknown section.",
            )
        )

    if not (
        criterion.evidence_checks
        or criterion.linked_question_ids
        or criterion.linked_schedule_fields
    ):
        issues.append(
            ValidationIssue(
                field=f"{field_prefix}.evidence",
                message="Each criterion must include at least one evidence check or linked question/schedule field.",
            )
        )

    for question_id in criterion.linked_question_ids:
        if question_id not in known_question_ids:
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.linked_question_ids",
                    message=f"Unknown linked question id: {question_id}.",
                )
            )

    for schedule_field_id in criterion.linked_schedule_fields:
        if schedule_field_id not in known_schedule_field_ids:
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.linked_schedule_fields",
                    message=f"Unknown linked schedule field: {schedule_field_id}.",
                )
            )

    if is_technical:
        if len(criterion.linked_question_ids) != 1:
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.linked_question_ids",
                    message="Technical criteria must link to exactly one vendor-facing question.",
                )
            )
        if criterion.linked_schedule_fields:
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.linked_schedule_fields",
                    message="Technical criteria cannot rely on schedule fields for scoring.",
                )
            )

    if criterion.deterministic_scoring is not None:
        issues.extend(_validate_deterministic_scoring(criterion=criterion, field_prefix=field_prefix))

    if criterion.criterion_type == CriterionType.MAC:
        if criterion.weight not in (None, 0):
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.weight",
                    message="MAC criteria cannot carry weights.",
                )
            )
        if criterion.min_cutoff not in (None, 0):
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.min_cutoff",
                    message="MAC criteria cannot carry cutoffs.",
                )
            )
        if criterion.qualitative_scoring_guidance not in (None, ""):
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.qualitative_scoring_guidance",
                    message="MAC criteria cannot carry qualitative scoring guidance.",
                )
            )
        if (
            criterion.deterministic_scoring is not None
            and criterion.deterministic_scoring.guide_type != DeterministicScoringType.PASS_FAIL
        ):
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.deterministic_scoring.guide_type",
                    message="MAC criteria may only use pass/fail deterministic scoring.",
                )
            )
        return issues

    if criterion.criterion_type == CriterionType.TECHNICAL_SCORED_ONLY:
        if criterion.weight is None or criterion.weight <= 0:
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.weight",
                    message="Scored-only technical criteria must have a positive weight.",
                )
            )
        if criterion.max_score is None or criterion.max_score <= 0:
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.max_score",
                    message="Scored-only technical criteria must have a positive max score.",
                )
            )
        if criterion.min_cutoff not in (None, 0):
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.min_cutoff",
                    message="Scored-only technical criteria cannot define a cutoff.",
                )
            )
        if criterion.deterministic_scoring is None and not (criterion.qualitative_scoring_guidance or "").strip():
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.qualitative_scoring_guidance",
                    message="Qualitative technical criteria must define qualitative scoring guidance.",
                )
            )
        if criterion.deterministic_scoring is not None and (criterion.qualitative_scoring_guidance or "").strip():
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.qualitative_scoring_guidance",
                    message="Objective technical criteria should not define qualitative scoring guidance.",
                )
            )
        return issues

    if criterion.criterion_type == CriterionType.TECHNICAL_CUTOFF_BACKED:
        if criterion.weight is None or criterion.weight <= 0:
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.weight",
                    message="Cutoff-backed technical criteria must have a positive weight.",
                )
            )
        if criterion.max_score is None or criterion.max_score <= 0:
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.max_score",
                    message="Cutoff-backed technical criteria must have a positive max score.",
                )
            )
        if criterion.min_cutoff is None:
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.min_cutoff",
                    message="Cutoff-backed technical criteria must define a minimum cutoff.",
                )
            )
        elif criterion.max_score is not None and not 0 <= criterion.min_cutoff <= criterion.max_score:
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.min_cutoff",
                    message="Cutoff-backed technical criteria must keep the minimum cutoff within the max score range.",
                )
            )
        if criterion.deterministic_scoring is None and not (criterion.qualitative_scoring_guidance or "").strip():
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.qualitative_scoring_guidance",
                    message="Qualitative technical criteria must define qualitative scoring guidance.",
                )
            )
        if criterion.deterministic_scoring is not None and (criterion.qualitative_scoring_guidance or "").strip():
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.qualitative_scoring_guidance",
                    message="Objective technical criteria should not define qualitative scoring guidance.",
                )
            )
        return issues

    if criterion.criterion_type == CriterionType.COMMERCIAL:
        if criterion.weight not in (None, 0):
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.weight",
                    message="Commercial criteria are not part of the phase 1 technical weighting.",
                )
            )
        if criterion.min_cutoff not in (None, 0):
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.min_cutoff",
                    message="Commercial criteria cannot define technical cutoffs.",
                )
            )
        if criterion.qualitative_scoring_guidance not in (None, ""):
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.qualitative_scoring_guidance",
                    message="Commercial criteria cannot define qualitative scoring guidance.",
                )
            )
        return issues

    return issues


def _validate_deterministic_scoring(*, criterion: Criterion, field_prefix: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    guide = criterion.deterministic_scoring
    if guide is None:
        return issues

    if not guide.rules:
        issues.append(
            ValidationIssue(
                field=f"{field_prefix}.deterministic_scoring.rules",
                message="Deterministic scoring guides must define at least one rule.",
            )
        )
        return issues

    if criterion.criterion_type == CriterionType.COMMERCIAL:
        if not (criterion.linked_question_ids or criterion.linked_schedule_fields):
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.deterministic_scoring",
                    message="Deterministic scoring must reference at least one linked question or schedule field.",
                )
            )
    elif not criterion.linked_question_ids:
        issues.append(
            ValidationIssue(
                field=f"{field_prefix}.deterministic_scoring",
                message="Deterministic technical scoring must reference the linked vendor question.",
            )
        )

    if guide.guide_type == DeterministicScoringType.PASS_FAIL:
        if not any(rule.outcome == "pass" for rule in guide.rules):
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.deterministic_scoring.rules",
                    message="Pass/fail guides must include at least one pass rule.",
                )
            )
        if not any(rule.outcome == "fail" for rule in guide.rules):
            issues.append(
                ValidationIssue(
                    field=f"{field_prefix}.deterministic_scoring.rules",
                    message="Pass/fail guides must include at least one fail rule.",
                )
            )
        return issues

    if not any(rule.score is not None for rule in guide.rules):
        issues.append(
            ValidationIssue(
                field=f"{field_prefix}.deterministic_scoring.rules",
                message="Banded deterministic guides must define a score for at least one rule.",
            )
        )

    return issues
