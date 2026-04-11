from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from statistics import median

from ..models import (
    AwardRecommendation,
    AwardType,
    CommercialEvaluationResult,
    CommercialLineItemResult,
    ComparabilityStatus,
    ComparisonSettings,
    Criterion,
    CriterionType,
    DeterministicScoringGuide,
    DeterministicScoringRule,
    DeterministicScoringType,
    EvaluationReport,
    ExtractedField,
    LockedFrameworkArtifact,
    ScenarioKind,
    ScenarioRankingItem,
    ScenarioResult,
    TechnicalCriterionResult,
    TechnicalCriterionStatus,
    TechnicalEvaluationResult,
    VendorRecord,
    VendorReview,
    VendorScoreBreakdown,
)
from .llm import LLMClient


HARD_NEGATIVE_PATTERNS = (
    re.compile(r"\bnot\s+(?:achievable|provided|included|available|clear|quoted|confirmed|compliant)\b"),
    re.compile(r"\bunable\b"),
    re.compile(r"\bmissing\b"),
    re.compile(r"\bincomplete\b"),
    re.compile(r"\bunclear\b"),
    re.compile(r"\bcannot\b"),
    re.compile(r"\bcan['’]?t\b"),
    re.compile(r"\bfail(?:ed|s|ure)?\b"),
    re.compile(r"\bomit(?:ted|s|ting)?\b"),
    re.compile(r"^\s*no\b"),
)
POSITIVE_PATTERNS = (
    re.compile(r"\byes\b"),
    re.compile(r"\bexplicitly\s+confirm\b"),
    re.compile(r"\bconfirm(?:ed|s)?\b"),
    re.compile(r"\bcompliant\b"),
    re.compile(r"\bcomplete(?:d|ness)?\b"),
    re.compile(r"\bachievable\b"),
    re.compile(r"\bprovided\b"),
    re.compile(r"\bincluded\b"),
    re.compile(r"\bavailable\b"),
    re.compile(r"\bquote(?:d)?\b"),
    re.compile(r"\bno\s+exclusions?\b"),
    re.compile(r"\bno\s+rfq\s+line\s+item\s+is\s+excluded\b"),
    re.compile(r"\bno\s+exclusions?\s+are\s+intended\b"),
)
COMMERCIAL_HINT_PATTERNS = (
    re.compile(r"\bcommercial\b"),
    re.compile(r"\bpricing\b"),
    re.compile(r"\bprice\b"),
    re.compile(r"\bquote(?:d)?\b"),
    re.compile(r"\bcost\b"),
    re.compile(r"\bcurrency\b"),
    re.compile(r"\bfee\b"),
)


@dataclass
class EvaluationContext:
    artifact: LockedFrameworkArtifact
    comparison_settings: ComparisonSettings | None
    vendors: list[VendorRecord]
    reviews_by_vendor: dict[str, VendorReview]


def run_evaluation(context: EvaluationContext, llm_client: LLMClient) -> EvaluationReport:
    technical_results = _build_technical_results(context, llm_client)
    commercial_results = _build_commercial_results(context, technical_results)
    official_recommendation = _build_official_recommendation(technical_results, commercial_results)
    advisory_scenarios = _build_standard_scenarios(technical_results, commercial_results)

    if official_recommendation.eligible_vendor_ids:
        advisory_scenarios.extend(
            llm_client.generate_ai_scenarios(
                artifact=context.artifact,
                technical_results=technical_results,
                commercial_results=commercial_results,
            )
        )

    blocked_reasons: list[str] = []
    if context.comparison_settings is None:
        blocked_reasons.append("Comparison settings must be provided before final commercial evaluation.")
    if not official_recommendation.eligible_vendor_ids:
        blocked_reasons.append(
            "No vendor remained both technically qualified and commercially comparable for award."
        )

    return EvaluationReport(
        generated_at=datetime.now(UTC),
        comparison_settings=context.comparison_settings,
        technical_results=technical_results,
        commercial_results=commercial_results,
        official_recommendation=official_recommendation,
        advisory_scenarios=advisory_scenarios,
        blocked_reasons=blocked_reasons,
    )


def _build_technical_results(
    context: EvaluationContext,
    llm_client: LLMClient,
) -> list[TechnicalEvaluationResult]:
    technical_criteria = [
        criterion
        for criterion in context.artifact.rubric_snapshot.criteria
        if _is_technical_gate_criterion(criterion, context.artifact)
    ]
    criterion_order = {
        criterion.id: index
        for index, criterion in enumerate(technical_criteria)
    }
    narrative_criteria = [
        criterion
        for criterion in technical_criteria
        if criterion.criterion_type != CriterionType.MAC and criterion.deterministic_scoring is None
    ]

    results: list[TechnicalEvaluationResult] = []
    for vendor in context.vendors:
        review = context.reviews_by_vendor.get(vendor.id)
        if review is None:
            results.append(
                TechnicalEvaluationResult(
                    vendor_id=vendor.id,
                    vendor_name=vendor.name,
                    passed_gate=False,
                    aggregate_score=0.0,
                    threshold=context.artifact.rubric_snapshot.aggregate_technical_threshold,
                    disqualification_reasons=["No extraction review exists for this vendor."],
                    criterion_results=[],
                    summary="Vendor cannot be evaluated until extraction and normalization are complete.",
                )
            )
            continue

        criterion_results: list[TechnicalCriterionResult] = [
            _evaluate_criterion_deterministically(criterion, review)
            for criterion in technical_criteria
            if criterion.deterministic_scoring is not None or criterion.criterion_type == CriterionType.MAC
        ]

        if narrative_criteria:
            criterion_results.extend(
                llm_client.score_narrative_technical(
                    artifact=context.artifact,
                    vendor=vendor,
                    review=review,
                    criteria=narrative_criteria,
                )
            )

        criterion_results_by_id = {
            result.criterion_id: result
            for result in criterion_results
        }

        total_score = 0.0
        disqualification_reasons: list[str] = []
        for criterion in technical_criteria:
            result = criterion_results_by_id.get(criterion.id)
            if result is None:
                result = TechnicalCriterionResult(
                    criterion_id=criterion.id,
                    title=criterion.title,
                    criterion_type=criterion.criterion_type,
                    status=TechnicalCriterionStatus.NOT_EVALUATED,
                    score=0.0 if criterion.criterion_type != CriterionType.MAC else None,
                    max_score=criterion.max_score,
                    passed=False if criterion.criterion_type == CriterionType.MAC else None,
                    confidence=0.0,
                    explanation="No evaluation result was produced for this criterion.",
                    evidence_refs=[],
                    math_trace=[],
                    risks=["Criterion was not evaluated."],
                )
                criterion_results_by_id[criterion.id] = result
                criterion_results.append(result)

            if criterion.criterion_type == CriterionType.MAC:
                if result.passed is not True:
                    disqualification_reasons.append(f"Failed MAC: {criterion.title}.")
                continue

            score = result.score or 0.0
            total_score += score

            if criterion.criterion_type == CriterionType.TECHNICAL_CUTOFF_BACKED:
                cutoff = criterion.min_cutoff or 0.0
                if score < cutoff:
                    disqualification_reasons.append(
                        f"Failed technical cutoff for {criterion.title}: scored {score:g} against minimum {cutoff:g}."
                    )

        threshold = context.artifact.rubric_snapshot.aggregate_technical_threshold
        rounded_total_score = round(total_score, 2)
        if rounded_total_score < threshold:
            disqualification_reasons.append(
                f"Aggregate technical score {rounded_total_score:g} is below threshold {threshold:g}."
            )

        passed_gate = not disqualification_reasons
        summary = (
            "Vendor passed the technical gate and can proceed to commercial evaluation."
            if passed_gate
            else "Vendor failed the technical gate and is excluded from commercial award ranking."
        )

        results.append(
            TechnicalEvaluationResult(
                vendor_id=vendor.id,
                vendor_name=vendor.name,
                passed_gate=passed_gate,
                aggregate_score=rounded_total_score,
                threshold=threshold,
                disqualification_reasons=disqualification_reasons,
                criterion_results=sorted(
                    criterion_results,
                    key=lambda result: criterion_order.get(result.criterion_id, len(criterion_order)),
                ),
                summary=summary,
            )
        )

    return results


def _evaluate_criterion_deterministically(
    criterion: Criterion,
    review: VendorReview,
) -> TechnicalCriterionResult:
    fields = _candidate_fields_for_criterion(criterion, review)
    primary_field = fields[0] if fields else None
    evidence_refs = [
        anchor.id
        for field in fields
        for anchor in field.evidence
    ]

    if criterion.criterion_type == CriterionType.MAC and criterion.deterministic_scoring is None:
        passed = bool(primary_field and primary_field.raw_value and primary_field.state.value == "answered")
        return TechnicalCriterionResult(
            criterion_id=criterion.id,
            title=criterion.title,
            criterion_type=criterion.criterion_type,
            status=TechnicalCriterionStatus.PASSED if passed else TechnicalCriterionStatus.FAILED,
            passed=passed,
            confidence=1.0 if passed else 0.3,
            explanation=(
                "Vendor provided direct evidence for the mandatory condition."
                if passed
                else "Mandatory condition is not evidenced clearly in the extracted response."
            ),
            evidence_refs=evidence_refs,
            math_trace=["Mandatory condition checked directly from linked evidence fields."],
            risks=[] if passed else ["Missing or weak evidence on a mandatory condition."],
        )

    guide = criterion.deterministic_scoring
    if guide is None:
        return TechnicalCriterionResult(
            criterion_id=criterion.id,
            title=criterion.title,
            criterion_type=criterion.criterion_type,
            status=TechnicalCriterionStatus.NOT_EVALUATED,
            score=0.0 if criterion.criterion_type != CriterionType.MAC else None,
            max_score=criterion.max_score,
            passed=None,
            confidence=0.0,
            explanation="Criterion requires narrative scoring.",
            evidence_refs=evidence_refs,
            math_trace=[],
            risks=["Criterion was left to narrative scoring but no AI result was available."],
        )

    if guide.guide_type == DeterministicScoringType.PASS_FAIL:
        passed, matched_rule, explanation = _evaluate_pass_fail(guide, primary_field)
        awarded_score = None
        if criterion.criterion_type != CriterionType.MAC:
            awarded_score = float(criterion.max_score or 0.0) if passed else 0.0
        return TechnicalCriterionResult(
            criterion_id=criterion.id,
            title=criterion.title,
            criterion_type=criterion.criterion_type,
            status=TechnicalCriterionStatus.PASSED if passed else TechnicalCriterionStatus.FAILED,
            score=awarded_score,
            max_score=criterion.max_score,
            passed=passed,
            confidence=1.0 if primary_field and primary_field.state.value == "answered" else 0.35,
            explanation=explanation,
            evidence_refs=evidence_refs,
            math_trace=[f"Matched rule: {matched_rule.condition if matched_rule else 'heuristic fallback'}."],
            risks=[] if passed else ["The pass/fail response indicates non-compliance or incomplete evidence."],
        )

    score, matched_rule, explanation = _evaluate_banded_score(guide, primary_field)
    passed = None
    status = TechnicalCriterionStatus.SCORED
    if criterion.criterion_type == CriterionType.TECHNICAL_CUTOFF_BACKED:
        cutoff = criterion.min_cutoff or 0.0
        passed = score >= cutoff
        status = TechnicalCriterionStatus.PASSED if passed else TechnicalCriterionStatus.FAILED

    return TechnicalCriterionResult(
        criterion_id=criterion.id,
        title=criterion.title,
        criterion_type=criterion.criterion_type,
        status=status,
        score=score,
        max_score=criterion.max_score,
        passed=passed,
        confidence=1.0 if primary_field and primary_field.state.value == "answered" else 0.4,
        explanation=explanation,
        evidence_refs=evidence_refs,
        math_trace=[
            f"Deterministic guide type: {guide.guide_type}.",
            f"Matched rule: {matched_rule.condition if matched_rule else 'none'}.",
        ],
        risks=[] if primary_field and primary_field.state.value == "answered" else ["Objective answer was weak or partially missing."],
    )


def _candidate_fields_for_criterion(
    criterion: Criterion,
    review: VendorReview,
) -> list[ExtractedField]:
    linked_question_ids = set(criterion.linked_question_ids)
    linked_schedule_fields = set(criterion.linked_schedule_fields)
    return [
        field
        for field in [
            *review.raw_extraction.question_answers,
            *review.raw_extraction.schedule_answers,
            *review.raw_extraction.technical_claims,
        ]
        if field.question_id in linked_question_ids
        or (
            field.schedule_id is not None
            and field.schedule_column_id is not None
            and f"{field.schedule_id}.{field.schedule_column_id}" in linked_schedule_fields
        )
        or criterion.id in field.criterion_ids
    ]


def _evaluate_pass_fail(
    guide: DeterministicScoringGuide,
    field: ExtractedField | None,
) -> tuple[bool, DeterministicScoringRule | None, str]:
    if field is None or field.state.value != "answered":
        fail_rule = next((rule for rule in guide.rules if rule.outcome == "fail"), None)
        return False, fail_rule, "Linked field is missing or not answered, so the pass/fail requirement is not met."

    text = f" {field.raw_value or ''} {field.normalized_hint or ''} ".lower()
    if _matches_any(HARD_NEGATIVE_PATTERNS, text):
        fail_rule = next((rule for rule in guide.rules if rule.outcome == "fail"), None)
        return False, fail_rule, "Extracted answer contains negative or incomplete signals against the pass condition."
    if _matches_any(POSITIVE_PATTERNS, text) or field.numeric_value not in (None, 0):
        pass_rule = next((rule for rule in guide.rules if rule.outcome == "pass"), None)
        return True, pass_rule, "Extracted answer satisfies the pass/fail condition with positive supporting language."

    fail_rule = next((rule for rule in guide.rules if rule.outcome == "fail"), None)
    return False, fail_rule, "Pass/fail response could not be confirmed from the extracted answer."


def _evaluate_banded_score(
    guide: DeterministicScoringGuide,
    field: ExtractedField | None,
) -> tuple[float, DeterministicScoringRule | None, str]:
    if field is None or field.state.value != "answered":
        return 0.0, None, "Linked field is missing or not answered, so the criterion scores zero."

    numeric_value = field.numeric_value
    if guide.guide_type == DeterministicScoringType.NUMERIC_BANDED and numeric_value is not None:
        matched_rule = _match_numeric_rule(numeric_value, guide.rules)
        if matched_rule and matched_rule.score is not None:
            return (
                float(matched_rule.score),
                matched_rule,
                f"Numeric value {numeric_value:g} matched the band '{matched_rule.condition}'.",
            )
        return 0.0, None, f"Numeric value {numeric_value:g} did not match an explicit scoring band."

    text = f"{field.raw_value or ''} {field.normalized_hint or ''}".strip().lower()
    matched_rule = _match_discrete_rule(text, guide.rules)
    if matched_rule and matched_rule.score is not None:
        return float(matched_rule.score), matched_rule, f"Answer text matched the rule '{matched_rule.condition}'."
    return 0.0, None, "Objective answer could not be matched to a deterministic rule."


def _match_numeric_rule(value: float, rules: list[DeterministicScoringRule]) -> DeterministicScoringRule | None:
    for rule in rules:
        condition = rule.condition.lower()
        if match := re.search(r"(\d+(?:\.\d+)?)\s*or more", condition):
            minimum = float(match.group(1))
            if value >= minimum:
                return rule
        elif match := re.search(r"(\d+(?:\.\d+)?)\s*to\s*(\d+(?:\.\d+)?)", condition):
            lower = float(match.group(1))
            upper = float(match.group(2))
            if lower <= value <= upper:
                return rule
        elif match := re.search(r"less than\s*(\d+(?:\.\d+)?)", condition):
            upper = float(match.group(1))
            if value < upper:
                return rule
        elif match := re.search(r"more than\s*(\d+(?:\.\d+)?)", condition):
            lower = float(match.group(1))
            if value > lower:
                return rule
        elif match := re.search(r"<=\s*(\d+(?:\.\d+)?)", condition):
            upper = float(match.group(1))
            if value <= upper:
                return rule
        elif match := re.search(r">=\s*(\d+(?:\.\d+)?)", condition):
            lower = float(match.group(1))
            if value >= lower:
                return rule
    return None


def _match_discrete_rule(answer_text: str, rules: list[DeterministicScoringRule]) -> DeterministicScoringRule | None:
    for rule in rules:
        condition = rule.condition.lower()
        keywords = [token for token in re.split(r"[^a-z0-9]+", condition) if len(token) > 3]
        if keywords and any(keyword in answer_text for keyword in keywords):
            return rule
    return None


def _matches_any(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _is_technical_gate_criterion(
    criterion: Criterion,
    artifact: LockedFrameworkArtifact,
) -> bool:
    if criterion.criterion_type == CriterionType.COMMERCIAL:
        return False
    return not _looks_like_commercial_criterion(criterion, artifact)


def _looks_like_commercial_criterion(
    criterion: Criterion,
    artifact: LockedFrameworkArtifact,
) -> bool:
    questions_by_id = {
        question.id: question
        for question in artifact.rubric_snapshot.questions
    }
    snippets = [criterion.title, criterion.description]
    for question_id in criterion.linked_question_ids:
        question = questions_by_id.get(question_id)
        if question is None:
            continue
        snippets.extend([question.text, question.purpose])

    text = " ".join(snippets).lower()
    return _matches_any(COMMERCIAL_HINT_PATTERNS, text)


def _build_commercial_results(
    context: EvaluationContext,
    technical_results: list[TechnicalEvaluationResult],
) -> list[CommercialEvaluationResult]:
    technical_by_vendor = {
        result.vendor_id: result
        for result in technical_results
    }
    results: list[CommercialEvaluationResult] = []

    for vendor in context.vendors:
        technical_result = technical_by_vendor.get(vendor.id)
        review = context.reviews_by_vendor.get(vendor.id)
        if technical_result is None or review is None:
            continue

        eligible_for_commercial = technical_result.passed_gate
        pricing_blockers = [
            blocker
            for line in review.normalized_pricing
            for blocker in line.blockers
        ]
        blockers = list(dict.fromkeys(pricing_blockers))
        if not eligible_for_commercial:
            blockers.insert(0, "Vendor did not pass the technical gate.")

        line_items = [
            CommercialLineItemResult(
                line_item_id=line.line_item_id,
                line_item_name=line.line_item_name,
                base_currency_total=line.base_currency_total,
                comparability_status=line.comparability_status,
                notes=[*line.conversion_notes, *line.exclusions, *line.blockers],
            )
            for line in review.normalized_pricing
        ]

        award_ready = (
            eligible_for_commercial
            and bool(review.normalized_pricing)
            and all(
                line.comparability_status == ComparabilityStatus.COMPARABLE
                and line.base_currency_total is not None
                for line in review.normalized_pricing
            )
        )
        comparable_total = (
            round(sum(line.base_currency_total or 0.0 for line in review.normalized_pricing), 2)
            if award_ready
            else None
        )

        anomalies = [
            f"{line.line_item_name}: vendor stated exclusions or assumptions."
            for line in review.normalized_pricing
            if line.exclusions
        ]
        explanation = (
            "Vendor is ready for commercial comparison."
            if award_ready
            else "Vendor cannot be ranked commercially until pricing completeness and comparability blockers are resolved."
        )

        results.append(
            CommercialEvaluationResult(
                vendor_id=vendor.id,
                vendor_name=vendor.name,
                eligible_for_commercial=eligible_for_commercial,
                award_ready=award_ready,
                base_currency=context.comparison_settings.base_currency if context.comparison_settings else "N/A",
                comparable_total=comparable_total,
                commercial_score=None,
                line_items=line_items,
                anomalies=anomalies,
                blockers=blockers,
                explanation=explanation,
                evidence_refs=[
                    evidence_ref
                    for line in review.normalized_pricing
                    for evidence_ref in line.evidence_refs
                ],
            )
        )

    award_ready_totals = [
        result.comparable_total
        for result in results
        if result.award_ready and result.comparable_total is not None
    ]
    if award_ready_totals:
        lowest_total = min(award_ready_totals)
        peer_median = median(award_ready_totals)
        for result in results:
            if result.award_ready and result.comparable_total is not None:
                result.commercial_score = round(100 * lowest_total / result.comparable_total, 2)
                if result.comparable_total < peer_median * 0.7:
                    result.anomalies.append("Quoted total is materially below the peer median.")
                elif result.comparable_total > peer_median * 1.3:
                    result.anomalies.append("Quoted total is materially above the peer median.")

    return results


def _build_official_recommendation(
    technical_results: list[TechnicalEvaluationResult],
    commercial_results: list[CommercialEvaluationResult],
) -> AwardRecommendation:
    commercial_by_vendor = {
        result.vendor_id: result
        for result in commercial_results
    }

    score_breakdown: list[VendorScoreBreakdown] = []
    eligible_vendor_ids: list[str] = []
    for technical in technical_results:
        commercial = commercial_by_vendor.get(technical.vendor_id)
        commercially_comparable = bool(
            commercial
            and commercial.award_ready
            and commercial.commercial_score is not None
        )
        final_score = None
        if technical.passed_gate and commercially_comparable and commercial is not None:
            final_score = round(
                0.7 * technical.aggregate_score + 0.3 * (commercial.commercial_score or 0.0),
                2,
            )
            eligible_vendor_ids.append(technical.vendor_id)

        score_breakdown.append(
            VendorScoreBreakdown(
                vendor_id=technical.vendor_id,
                vendor_name=technical.vendor_name,
                technical_score=technical.aggregate_score,
                commercial_score=commercial.commercial_score if commercial else None,
                final_score=final_score,
                passed_technical_gate=technical.passed_gate,
                commercially_comparable=commercially_comparable,
            )
        )

    eligible_breakdown = [
        item
        for item in score_breakdown
        if item.vendor_id in eligible_vendor_ids and item.final_score is not None
    ]
    if not eligible_breakdown:
        return AwardRecommendation(
            winner_vendor_id=None,
            award_type=AwardType.SINGLE_VENDOR,
            eligible_vendor_ids=[],
            score_breakdown=score_breakdown,
            evidence_refs=[],
            explanation=(
                "No official winner can be recommended because no vendor remained both technically qualified "
                "and commercially comparable."
            ),
            risks=["Resolve pricing comparability or extraction blockers before awarding."],
        )

    winner = max(eligible_breakdown, key=lambda item: item.final_score or 0.0)
    technical = next(result for result in technical_results if result.vendor_id == winner.vendor_id)
    commercial = commercial_by_vendor[winner.vendor_id]

    evidence_refs = list(
        dict.fromkeys(
            [
                evidence_ref
                for criterion in technical.criterion_results
                for evidence_ref in criterion.evidence_refs
            ]
            + list(commercial.evidence_refs)
        )
    )
    risks = list(
        dict.fromkeys(
            [
                risk
                for criterion in technical.criterion_results
                for risk in criterion.risks
            ]
            + list(commercial.anomalies)
        )
    )

    return AwardRecommendation(
        winner_vendor_id=winner.vendor_id,
        award_type=AwardType.SINGLE_VENDOR,
        eligible_vendor_ids=eligible_vendor_ids,
        score_breakdown=score_breakdown,
        evidence_refs=evidence_refs,
        explanation=(
            f"Vendor {winner.vendor_name} is the official QCBS 70/30 winner with technical score "
            f"{winner.technical_score or 0.0:g}, commercial score {winner.commercial_score or 0.0:g}, "
            f"and final weighted score {winner.final_score or 0.0:g}."
        ),
        risks=risks,
    )


def _build_standard_scenarios(
    technical_results: list[TechnicalEvaluationResult],
    commercial_results: list[CommercialEvaluationResult],
) -> list[ScenarioResult]:
    commercial_by_vendor = {
        result.vendor_id: result
        for result in commercial_results
    }
    eligible_technical = [
        result
        for result in technical_results
        if result.passed_gate
        and commercial_by_vendor.get(result.vendor_id) is not None
        and commercial_by_vendor[result.vendor_id].award_ready
    ]
    if not eligible_technical:
        return []

    eligible_vendor_ids = {
        result.vendor_id
        for result in eligible_technical
    }
    excluded_vendor_ids = [
        result.vendor_id
        for result in technical_results
        if result.vendor_id not in eligible_vendor_ids
    ]

    lcs_ranking = [
        ScenarioRankingItem(
            vendor_id=result.vendor_id,
            vendor_name=result.vendor_name,
            score=commercial_by_vendor[result.vendor_id].comparable_total,
            notes=[],
        )
        for result in sorted(
            eligible_technical,
            key=lambda result: commercial_by_vendor[result.vendor_id].comparable_total or float("inf"),
        )
    ]
    qbs_ranking = [
        ScenarioRankingItem(
            vendor_id=result.vendor_id,
            vendor_name=result.vendor_name,
            score=result.aggregate_score,
            notes=[],
        )
        for result in sorted(
            eligible_technical,
            key=lambda result: result.aggregate_score,
            reverse=True,
        )
    ]

    lcs_winner = lcs_ranking[0]
    qbs_winner = qbs_ranking[0]

    return [
        ScenarioResult(
            scenario_name="Lowest Comparable Cost",
            scenario_kind=ScenarioKind.ADVISORY_LCS,
            is_official=False,
            winner_vendor_id=lcs_winner.vendor_id,
            excluded_vendor_ids=excluded_vendor_ids,
            weighting_or_rule_basis=(
                "Choose the technically qualified and commercially comparable vendor with the lowest total normalized cost."
            ),
            explanation=(
                "This advisory view ignores technical-commercial weighting and answers the pure lowest comparable cost question."
            ),
            evidence_refs=list(commercial_by_vendor[lcs_winner.vendor_id].evidence_refs),
            ranking=lcs_ranking,
        ),
        ScenarioResult(
            scenario_name="Highest Technical Quality",
            scenario_kind=ScenarioKind.ADVISORY_QBS,
            is_official=False,
            winner_vendor_id=qbs_winner.vendor_id,
            excluded_vendor_ids=excluded_vendor_ids,
            weighting_or_rule_basis=(
                "Choose the technically qualified and commercially comparable vendor with the highest aggregate technical score."
            ),
            explanation=(
                "This advisory view prioritizes quality leadership while still excluding vendors that are not commercially comparable."
            ),
            evidence_refs=_technical_evidence_refs(qbs_winner.vendor_id, technical_results),
            ranking=qbs_ranking,
        ),
    ]


def _technical_evidence_refs(
    vendor_id: str,
    technical_results: list[TechnicalEvaluationResult],
) -> list[str]:
    result = next((item for item in technical_results if item.vendor_id == vendor_id), None)
    if result is None:
        return []
    return list(
        dict.fromkeys(
            evidence_ref
            for criterion in result.criterion_results
            for evidence_ref in criterion.evidence_refs
        )
    )
