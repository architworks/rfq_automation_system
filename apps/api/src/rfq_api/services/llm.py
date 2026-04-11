from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable
from typing import Annotated, Literal, TypeVar, cast

from openai import OpenAI
from pydantic import BaseModel, Field

from ..config import Settings
from .documents import build_file_data_url
from ..models import (
    AwardType,
    CommercialEvaluationResult,
    OFFICIAL_AWARD_BASIS,
    Criterion,
    CriterionType,
    DeterministicScoringGuide,
    DeterministicScoringRule,
    DeterministicScoringType,
    EvidenceCheck,
    EvidenceAnchor,
    ExtractedField,
    LockedFrameworkArtifact,
    Question,
    RawExtraction,
    ResponseSchedule,
    RFQDraft,
    RubricProposal,
    RubricSection,
    ScheduleColumn,
    ScenarioKind,
    ScenarioRankingItem,
    ScenarioResult,
    TechnicalCriterionResult,
    TechnicalCriterionStatus,
    TechnicalEvaluationResult,
    VendorDocument,
    VendorRecord,
    VendorReview,
)


class LLMConfigurationError(RuntimeError):
    pass


class LLMTaskError(RuntimeError):
    pass


class RubricGenerationError(LLMTaskError):
    pass


class LLMClient(ABC):
    @abstractmethod
    def generate_rubric(self, rfq_draft: RFQDraft) -> RubricProposal:
        raise NotImplementedError

    @abstractmethod
    def extract_vendor_response(
        self,
        *,
        artifact: LockedFrameworkArtifact,
        vendor: VendorRecord,
        document: VendorDocument,
        document_bytes: bytes,
    ) -> RawExtraction:
        raise NotImplementedError

    @abstractmethod
    def score_narrative_technical(
        self,
        *,
        artifact: LockedFrameworkArtifact,
        vendor: VendorRecord,
        review: VendorReview,
        criteria: list[Criterion],
    ) -> list[TechnicalCriterionResult]:
        raise NotImplementedError

    @abstractmethod
    def generate_ai_scenarios(
        self,
        *,
        artifact: LockedFrameworkArtifact,
        technical_results: list[TechnicalEvaluationResult],
        commercial_results: list[CommercialEvaluationResult],
    ) -> list[ScenarioResult]:
        raise NotImplementedError


Identifier = Annotated[str, Field(min_length=2, max_length=40, pattern=r"^[a-z][a-z0-9_]*$")]
ShortTitle = Annotated[str, Field(min_length=3, max_length=72)]
DescriptionText = Annotated[str, Field(min_length=8, max_length=220)]
QuestionText = Annotated[str, Field(min_length=12, max_length=500)]
PurposeText = Annotated[str, Field(min_length=8, max_length=140)]
ReasonText = Annotated[str, Field(min_length=8, max_length=220)]
FormatText = Annotated[str, Field(min_length=3, max_length=120)]
ConditionText = Annotated[str, Field(min_length=3, max_length=220)]
LongText = Annotated[str, Field(min_length=8, max_length=700)]
LocatorText = Annotated[str, Field(min_length=2, max_length=80)]


class GeneratedSection(BaseModel):
    id: Identifier
    title: ShortTitle
    description: DescriptionText


class GeneratedEvidenceCheck(BaseModel):
    id: Identifier
    label: ShortTitle
    description: PurposeText


class GeneratedDeterministicScoringRule(BaseModel):
    id: Identifier
    condition: ConditionText
    score: float | None = Field(default=None, ge=0, le=100)
    outcome: Literal["pass", "fail"] | None = None


class GeneratedDeterministicScoringGuide(BaseModel):
    guide_type: DeterministicScoringType
    answer_format: FormatText
    summary: PurposeText
    rules: list[GeneratedDeterministicScoringRule] = Field(default_factory=list, min_length=1, max_length=6)


class CriterionDraft(BaseModel):
    id: Identifier
    section_id: Identifier
    title: ShortTitle
    description: DescriptionText
    criterion_type: CriterionType
    weight: float | None = Field(default=None, ge=0, le=100)
    min_cutoff: float | None = Field(default=None, ge=0, le=100)
    max_score: float | None = Field(default=None, ge=0, le=100)
    evidence_checks: list[GeneratedEvidenceCheck] = Field(default_factory=list, min_length=1, max_length=1)
    deterministic_scoring: GeneratedDeterministicScoringGuide | None = None


class GeneratedQuestion(BaseModel):
    id: Identifier
    text: QuestionText
    purpose: PurposeText
    linked_criteria: list[Identifier] = Field(default_factory=list, min_length=1, max_length=3)


class GeneratedScheduleColumn(BaseModel):
    id: Identifier
    label: ShortTitle
    description: PurposeText
    required: bool = True


class GeneratedResponseSchedule(BaseModel):
    id: Identifier
    name: ShortTitle
    purpose: PurposeText
    columns: list[GeneratedScheduleColumn] = Field(default_factory=list, min_length=1, max_length=3)
    linked_criteria: list[Identifier] = Field(default_factory=list, min_length=1, max_length=4)


class LLMRubricProposal(BaseModel):
    sections: list[GeneratedSection] = Field(min_length=2, max_length=4)
    criteria: list[CriterionDraft] = Field(min_length=6, max_length=9)
    aggregate_technical_threshold: float = Field(ge=0, le=100)
    questions: list[GeneratedQuestion] = Field(min_length=5, max_length=8)
    response_schedules: list[GeneratedResponseSchedule] = Field(min_length=2, max_length=3)
    official_award_basis: Literal["QCBS 70/30"] = OFFICIAL_AWARD_BASIS
    generation_rationale: list[ReasonText] = Field(min_length=2, max_length=4)


class GeneratedEvidenceAnchor(BaseModel):
    id: Identifier
    snippet: LongText
    locator: LocatorText
    source_label: ShortTitle | None = None


class GeneratedExtractedField(BaseModel):
    id: Identifier
    label: ShortTitle
    question_id: Identifier | None = None
    schedule_id: Identifier | None = None
    schedule_column_id: Identifier | None = None
    criterion_ids: list[Identifier] = Field(default_factory=list, max_length=4)
    line_item_id: Identifier | None = None
    state: Literal[
        "answered",
        "missing_vendor_response",
        "missing_extractable_evidence",
        "conflicting_evidence",
        "not_applicable",
    ]
    raw_value: LongText | None = None
    normalized_hint: LongText | None = None
    quantity_value: float | None = None
    numeric_value: float | None = None
    currency: Annotated[str, Field(min_length=3, max_length=8)] | None = None
    uom: ShortTitle | None = None
    notes: LongText | None = None
    evidence: list[GeneratedEvidenceAnchor] = Field(default_factory=list, max_length=4)


class LLMVendorExtraction(BaseModel):
    document_summary: LongText
    question_answers: list[GeneratedExtractedField] = Field(default_factory=list)
    schedule_answers: list[GeneratedExtractedField] = Field(default_factory=list)
    technical_claims: list[GeneratedExtractedField] = Field(default_factory=list)
    commercial_claims: list[GeneratedExtractedField] = Field(default_factory=list)
    warnings: list[ReasonText] = Field(default_factory=list, max_length=6)


class NarrativeCriterionScore(BaseModel):
    criterion_id: Identifier
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    explanation: LongText
    evidence_refs: list[Identifier] = Field(default_factory=list, max_length=6)
    risks: list[ReasonText] = Field(default_factory=list, max_length=4)


class NarrativeCriterionScoreSet(BaseModel):
    scores: list[NarrativeCriterionScore] = Field(default_factory=list)


class AIScenarioRankingDraft(BaseModel):
    vendor_id: Identifier
    score: float | None = Field(default=None, ge=0, le=100)
    notes: list[ReasonText] = Field(default_factory=list, max_length=3)


class AIScenarioDraft(BaseModel):
    scenario_name: ShortTitle
    winner_vendor_id: Identifier
    weighting_or_rule_basis: LongText
    explanation: LongText
    evidence_refs: list[Identifier] = Field(default_factory=list, max_length=8)
    ranking: list[AIScenarioRankingDraft] = Field(default_factory=list)


class AIScenarioSet(BaseModel):
    scenarios: list[AIScenarioDraft] = Field(min_length=3, max_length=3)


ParsedModelT = TypeVar("ParsedModelT", bound=BaseModel)


class OpenAIResponsesClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        if not settings.azure_openai_endpoint:
            raise LLMConfigurationError("AZURE_OPENAI_ENDPOINT is required.")
        if not settings.azure_openai_api_key:
            raise LLMConfigurationError("AZURE_OPENAI_API_KEY is required.")
        if not settings.azure_openai_model:
            raise LLMConfigurationError("AZURE_OPENAI_MODEL is required.")

        self._model = settings.azure_openai_model
        base_url = settings.azure_openai_endpoint
        if not base_url.endswith("/"):
            base_url = f"{base_url}/"

        self._client = OpenAI(
            api_key=settings.azure_openai_api_key,
            base_url=base_url,
            timeout=settings.azure_openai_timeout_seconds,
        )

    def generate_rubric(self, rfq_draft: RFQDraft) -> RubricProposal:
        rfq_brief = self._build_rfq_brief(rfq_draft)
        instructions = (
            "Design one complete RFQ evaluation framework from the supplied RFQ brief. "
            "Stay generic to procurement logic and use only details present in the RFQ brief. "
            f"The official award basis must remain fixed to {OFFICIAL_AWARD_BASIS}. "
            "Use only the criterion types mac, technical_cutoff_backed, technical_scored_only, or commercial. "
            "Use MAC only for pass/fail mandatory gates. "
            "Criteria about pricing completeness, commercial quote coverage, costs, currencies, or exclusions clarity "
            "must use criterion_type commercial, even when they are pass/fail. "
            "Use cutoff-backed criteria only for a small number of critical technical risks. "
            "Technical scored and cutoff-backed criteria together must total 100 points, "
            "and each scored criterion must use the same value for weight and max_score. "
            "Commercial criteria must have no weight and no cutoff. "
            "Set one aggregate technical threshold for qualified bids. "
            "Every criterion must include exactly one evidence check. "
            "Questions must be mutually distinct and collectively cover the criteria without unnecessary overlap. "
            "Schedules must capture structured vendor inputs a buyer can compare later. "
            "Vendor-facing question text must be complete and readable, not clipped mid-sentence. "
            "When a criterion can be evaluated directly from a binary answer, a numeric count, or a discrete stated choice, "
            "include a deterministic_scoring guide with explicit rules. "
            "Use deterministic scoring mainly for objective compliance, completeness, count, or threshold checks. "
            "Leave deterministic_scoring null for narrative or evaluator-judgement criteria. "
            "Keep titles short, descriptions concise, and avoid repeating the RFQ narrative."
        )
        input_text = (
            "Create one coherent rubric for this RFQ brief.\n\n"
            f"{rfq_brief}"
        )
        generated = self._parse_structured_output(
            instructions=instructions,
            input_text=input_text,
            text_format=LLMRubricProposal,
            error_label="Rubric generation",
        )
        return self._compose_rubric(generated)

    def extract_vendor_response(
        self,
        *,
        artifact: LockedFrameworkArtifact,
        vendor: VendorRecord,
        document: VendorDocument,
        document_bytes: bytes,
    ) -> RawExtraction:
        framework_brief = self._build_locked_framework_brief(artifact)
        file_data = build_file_data_url(document, document_bytes)
        instructions = (
            "Extract only information that is explicitly grounded in the vendor document and relevant to the locked RFQ framework. "
            "Do not invent answers, prices, experience, or evidence. "
            "For every buyer question and every requested schedule field, return one field object even if the answer is missing. "
            "Use the response states answered, missing_vendor_response, missing_extractable_evidence, conflicting_evidence, or not_applicable precisely. "
            "Map commercial claims to the supplied RFQ line_item_id values when possible. "
            "Capture short evidence snippets and precise locators such as page, slide, sheet, row, or cell. "
            "Use quantity_value only when the document states a quantity clearly, and numeric_value only when a comparable number is visible in the document."
        )
        input_payload = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": document.file_name,
                        "file_data": file_data,
                    },
                    {
                        "type": "input_text",
                        "text": (
                            f"Vendor: {vendor.name}\n\n"
                            "Locked RFQ framework\n"
                            f"{framework_brief}\n\n"
                            "Return a single structured extraction for this vendor document."
                        ),
                    },
                ],
            }
        ]
        extracted = self._parse_structured_input(
            instructions=instructions,
            input_payload=input_payload,
            text_format=LLMVendorExtraction,
            error_label="Vendor extraction",
        )
        return self._compose_raw_extraction(extracted)

    def score_narrative_technical(
        self,
        *,
        artifact: LockedFrameworkArtifact,
        vendor: VendorRecord,
        review: VendorReview,
        criteria: list[Criterion],
    ) -> list[TechnicalCriterionResult]:
        if not criteria:
            return []

        criteria_brief = self._build_narrative_criteria_brief(criteria)
        review_brief = self._build_vendor_review_brief(review)
        instructions = (
            "Score only the listed narrative technical criteria using the extracted evidence summary. "
            "Do not score commercial criteria. Do not introduce new criteria or new evidence. "
            "Use only evidence_refs that appear in the supplied review summary. "
            "Keep each score within the criterion's max_score. "
            "If evidence is weak or missing, score conservatively and explain the risk."
        )
        parsed, reasoning_summary = self._parse_structured_input_with_reasoning(
            instructions=instructions,
            input_payload=(
                f"Vendor: {vendor.name}\n\n"
                f"RFQ: {artifact.rfq_snapshot.general_info.subject}\n\n"
                "Narrative criteria to score\n"
                f"{criteria_brief}\n\n"
                "Vendor review summary\n"
                f"{review_brief}"
            ),
            text_format=NarrativeCriterionScoreSet,
            error_label="Narrative technical scoring",
        )
        return self._compose_narrative_scores(criteria, parsed, reasoning_summary)

    def generate_ai_scenarios(
        self,
        *,
        artifact: LockedFrameworkArtifact,
        technical_results: list[TechnicalEvaluationResult],
        commercial_results: list[CommercialEvaluationResult],
    ) -> list[ScenarioResult]:
        commercial_by_vendor = {
            result.vendor_id: result
            for result in commercial_results
        }
        eligible_vendor_ids = [
            result.vendor_id
            for result in technical_results
            if result.passed_gate
            and commercial_by_vendor.get(result.vendor_id) is not None
            and commercial_by_vendor[result.vendor_id].award_ready
        ]
        if not eligible_vendor_ids:
            return []

        instructions = (
            "Generate exactly 3 advisory procurement scenarios derived only from the locked RFQ dimensions, buyer priorities, and evaluated vendor evidence. "
            "Do not repeat the standard QCBS, LCS, or QBS rules. "
            "Do not invent new criteria after bid opening. "
            "Choose winners only from the award-ready eligible vendor ids supplied. "
            "Vendors outside that eligible set may appear only as benchmarks, not as winners. "
            "Reference vendor ids and evidence ids exactly as given."
        )
        parsed, reasoning_summary = self._parse_structured_input_with_reasoning(
            instructions=instructions,
            input_payload=(
                "Locked RFQ framework\n"
                f"{self._build_locked_framework_brief(artifact)}\n\n"
                "Technical evaluation summary\n"
                f"{self._build_technical_results_brief(technical_results)}\n\n"
                "Commercial evaluation summary\n"
                f"{self._build_commercial_results_brief(commercial_results)}\n\n"
                f"Eligible winner vendor ids: {', '.join(eligible_vendor_ids)}"
            ),
            text_format=AIScenarioSet,
            error_label="AI scenario generation",
        )
        excluded_vendor_ids = [
            result.vendor_id
            for result in technical_results
            if result.vendor_id not in eligible_vendor_ids
        ]
        fallback_winner_id = self._rank_eligible_vendor_ids(technical_results, commercial_results)[0]

        scenarios: list[ScenarioResult] = []
        for scenario in parsed.scenarios:
            ranking = [
                ScenarioRankingItem(
                    vendor_id=item.vendor_id,
                    vendor_name=self._lookup_vendor_name(technical_results, item.vendor_id),
                    score=item.score,
                    notes=list(item.notes),
                )
                for item in scenario.ranking
                if self._lookup_vendor_name(technical_results, item.vendor_id) != item.vendor_id
            ]
            winner_vendor_id = self._coerce_scenario_winner(
                requested_winner_id=scenario.winner_vendor_id,
                ranking=ranking,
                eligible_vendor_ids=eligible_vendor_ids,
                fallback_winner_id=fallback_winner_id,
            )
            explanation = scenario.explanation
            if scenario.winner_vendor_id != winner_vendor_id:
                explanation = (
                    f"{explanation} Winner was normalized to the nearest eligible vendor for award safety."
                )
            if reasoning_summary:
                explanation = f"{explanation} Reasoning summary: {reasoning_summary}"

            scenarios.append(
                ScenarioResult(
                    scenario_name=scenario.scenario_name,
                    scenario_kind=ScenarioKind.ADVISORY_AI,
                    is_official=False,
                    winner_vendor_id=winner_vendor_id,
                    excluded_vendor_ids=excluded_vendor_ids,
                    weighting_or_rule_basis=scenario.weighting_or_rule_basis,
                    explanation=explanation,
                    evidence_refs=list(scenario.evidence_refs),
                    ranking=ranking,
                )
            )

        return scenarios

    def _parse_structured_output(
        self,
        *,
        instructions: str,
        input_text: str,
        text_format: type[ParsedModelT],
        error_label: str,
    ) -> ParsedModelT:
        try:
            return self._parse_once(
                instructions=instructions,
                input_payload=input_text,
                text_format=text_format,
            )
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            if not self._looks_like_truncated_output(exc):
                raise RubricGenerationError(f"{error_label} failed: {exc}") from exc

            retry_instructions = (
                f"{instructions} "
                "Retry in ultra-compact mode. "
                "Use the smallest valid response that still satisfies the schema. "
                "Prefer 2 sections, 6 criteria, 5 questions, 2 schedules, and 2 rationale bullets. "
                "Keep question text complete even in compact mode. "
                "Keep titles short, keep descriptions under 80 characters, avoid duplicate phrasing, "
                "and do not include extra narrative."
            )
            try:
                return self._parse_once(
                    instructions=retry_instructions,
                    input_payload=input_text,
                    text_format=text_format,
                )
            except Exception as retry_exc:  # pragma: no cover - network/runtime dependent
                raise RubricGenerationError(f"{error_label} failed: {retry_exc}") from retry_exc

    def _parse_structured_input(
        self,
        *,
        instructions: str,
        input_payload: str | list[dict[str, object]],
        text_format: type[ParsedModelT],
        error_label: str,
    ) -> ParsedModelT:
        try:
            return self._parse_once(
                instructions=instructions,
                input_payload=input_payload,
                text_format=text_format,
            )
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            raise LLMTaskError(f"{error_label} failed: {exc}") from exc

    def _parse_structured_input_with_reasoning(
        self,
        *,
        instructions: str,
        input_payload: str | list[dict[str, object]],
        text_format: type[ParsedModelT],
        error_label: str,
    ) -> tuple[ParsedModelT, str | None]:
        try:
            return self._parse_once_with_reasoning(
                instructions=instructions,
                input_payload=input_payload,
                text_format=text_format,
            )
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            raise LLMTaskError(f"{error_label} failed: {exc}") from exc

    def _parse_once(
        self,
        *,
        instructions: str,
        input_payload: str | list[dict[str, object]],
        text_format: type[ParsedModelT],
    ) -> ParsedModelT:
        response = self._client.responses.parse(
            model=self._model,
            instructions=instructions,
            input=input_payload,
            text_format=text_format,
        )
        parsed = cast(ParsedModelT | None, response.output_parsed)
        if parsed is None:
            raise RubricGenerationError("Structured output call returned no parsed object.")
        return parsed

    def _parse_once_with_reasoning(
        self,
        *,
        instructions: str,
        input_payload: str | list[dict[str, object]],
        text_format: type[ParsedModelT],
    ) -> tuple[ParsedModelT, str | None]:
        response = self._client.responses.parse(
            model=self._model,
            instructions=instructions,
            input=input_payload,
            text_format=text_format,
            reasoning={"summary": "auto"},
        )
        parsed = cast(ParsedModelT | None, response.output_parsed)
        if parsed is None:
            raise LLMTaskError("Structured output call returned no parsed object.")
        return parsed, self._extract_reasoning_summary(response)

    @staticmethod
    def _build_rfq_brief(rfq_draft: RFQDraft) -> str:
        timeline_lines = OpenAIResponsesClient._numbered_lines(
            [
                f"Clarifications deadline: {rfq_draft.timelines.clarifications_deadline}",
                f"Technical bid deadline: {rfq_draft.timelines.technical_bid_deadline}",
                f"Commercial bid deadline: {rfq_draft.timelines.commercial_bid_deadline}",
                f"Evaluation start date: {rfq_draft.timelines.evaluation_start_date}",
                f"Negotiation start date: {rfq_draft.timelines.negotiation_start_date}",
                f"Final award date: {rfq_draft.timelines.final_award_date}",
            ]
        )
        priority_lines = OpenAIResponsesClient._numbered_lines(
            f"{item.title}: {OpenAIResponsesClient._shorten(item.description, 90)}"
            for item in rfq_draft.buyer_priorities
        )
        mandatory_lines = OpenAIResponsesClient._numbered_lines(
            OpenAIResponsesClient._shorten(item, 100)
            for item in rfq_draft.mandatory_conditions
        )
        line_item_lines = OpenAIResponsesClient._numbered_lines(
            (
                f"{item.product_name} [{item.category}, {item.uom}]: "
                f"{OpenAIResponsesClient._shorten(item.description, 110)}"
            )
            for item in rfq_draft.line_items
        )

        return (
            "RFQ summary\n"
            f"Subject: {rfq_draft.general_info.subject}\n"
            f"Code: {rfq_draft.general_info.rfq_code}\n"
            f"Sourcing type: {rfq_draft.general_info.sourcing_type}\n"
            f"Round: {rfq_draft.general_info.round}\n"
            f"Status: {rfq_draft.general_info.status}\n"
            f"Owner: {rfq_draft.general_info.owner}\n"
            f"Currency: {rfq_draft.general_info.currency}\n"
            f"Requestor: {rfq_draft.general_info.requestor}\n"
            f"Department: {rfq_draft.general_info.department}\n"
            f"Category: {rfq_draft.general_info.category}\n\n"
            "Scope\n"
            f"{OpenAIResponsesClient._shorten(rfq_draft.scope_overview, 320)}\n\n"
            "Timelines\n"
            f"{timeline_lines}\n\n"
            "Buyer priorities\n"
            f"{priority_lines}\n\n"
            "Mandatory conditions\n"
            f"{mandatory_lines}\n\n"
            "Requested line items\n"
            f"{line_item_lines}"
        )

    @staticmethod
    def _compose_rubric(
        generated: LLMRubricProposal,
    ) -> RubricProposal:
        known_criteria = {criterion.id for criterion in generated.criteria}
        question_links: dict[str, list[str]] = defaultdict(list)
        schedule_links: dict[str, list[str]] = defaultdict(list)

        questions = []
        for question in generated.questions:
            linked = OpenAIResponsesClient._dedupe(
                criterion_id for criterion_id in question.linked_criteria if criterion_id in known_criteria
            )
            normalized_question = Question(
                id=question.id,
                text=question.text,
                purpose=question.purpose,
                linked_criteria=linked,
            )
            questions.append(normalized_question)
            for criterion_id in linked:
                question_links[criterion_id].append(normalized_question.id)

        schedules = []
        for schedule in generated.response_schedules:
            linked = OpenAIResponsesClient._dedupe(
                criterion_id for criterion_id in schedule.linked_criteria if criterion_id in known_criteria
            )
            normalized_schedule = ResponseSchedule(
                id=schedule.id,
                name=schedule.name,
                purpose=schedule.purpose,
                columns=[
                    ScheduleColumn(
                        id=column.id,
                        label=column.label,
                        description=column.description,
                        required=column.required,
                    )
                    for column in schedule.columns
                ],
                linked_criteria=linked,
            )
            schedules.append(normalized_schedule)
            field_ids = [f"{normalized_schedule.id}.{column.id}" for column in normalized_schedule.columns]
            for criterion_id in linked:
                schedule_links[criterion_id].extend(field_ids)

        criteria = []
        for criterion in generated.criteria:
            evidence_checks = criterion.evidence_checks or [
                GeneratedEvidenceCheck(
                    id=f"{criterion.id}_evidence",
                    label="Supporting evidence",
                    description="Vendor must provide supporting evidence.",
                )
            ]
            normalized_type = OpenAIResponsesClient._normalize_generated_criterion_type(
                criterion=criterion,
                questions=questions,
                linked_question_ids=OpenAIResponsesClient._dedupe(question_links[criterion.id]),
            )
            weight = criterion.weight
            min_cutoff = criterion.min_cutoff
            max_score = criterion.max_score
            if normalized_type == CriterionType.COMMERCIAL:
                weight = None
                min_cutoff = None
                max_score = None
            criteria.append(
                Criterion(
                    id=criterion.id,
                    section_id=criterion.section_id,
                    title=criterion.title,
                    description=criterion.description,
                    criterion_type=normalized_type,
                    weight=weight,
                    min_cutoff=min_cutoff,
                    max_score=max_score,
                    evidence_checks=[
                        EvidenceCheck(
                            id=check.id,
                            label=check.label,
                            description=check.description,
                        )
                        for check in evidence_checks
                    ],
                    linked_question_ids=OpenAIResponsesClient._dedupe(question_links[criterion.id]),
                    linked_schedule_fields=OpenAIResponsesClient._dedupe(schedule_links[criterion.id]),
                    deterministic_scoring=(
                        DeterministicScoringGuide(
                            guide_type=criterion.deterministic_scoring.guide_type,
                            answer_format=criterion.deterministic_scoring.answer_format,
                            summary=criterion.deterministic_scoring.summary,
                            rules=[
                                DeterministicScoringRule(
                                    id=rule.id,
                                    condition=rule.condition,
                                    score=rule.score,
                                    outcome=rule.outcome,
                                )
                                for rule in criterion.deterministic_scoring.rules
                            ],
                        )
                        if criterion.deterministic_scoring is not None
                        else None
                    ),
                )
            )

        return RubricProposal(
            sections=[
                RubricSection(
                    id=section.id,
                    title=section.title,
                    description=section.description,
                )
                for section in generated.sections
            ],
            criteria=criteria,
            aggregate_technical_threshold=generated.aggregate_technical_threshold,
            questions=questions,
            response_schedules=schedules,
            official_award_basis=OFFICIAL_AWARD_BASIS,
            generation_rationale=list(generated.generation_rationale),
        )

    @staticmethod
    def _normalize_generated_criterion_type(
        *,
        criterion: CriterionDraft,
        questions: list[Question],
        linked_question_ids: list[str],
    ) -> CriterionType:
        if criterion.criterion_type == CriterionType.COMMERCIAL:
            return CriterionType.COMMERCIAL

        questions_by_id = {
            question.id: question
            for question in questions
        }

        snippets = [criterion.title, criterion.description]
        for question_id in linked_question_ids:
            question = questions_by_id.get(question_id)
            if question is None:
                continue
            snippets.extend([question.text, question.purpose])

        commercial_text = " ".join(snippets).lower()
        if any(
            keyword in commercial_text
            for keyword in ("commercial", "pricing", "price", "quote", "quoted", "cost", "currency", "fee")
        ):
            return CriterionType.COMMERCIAL

        return criterion.criterion_type

    @staticmethod
    def _compose_raw_extraction(generated: LLMVendorExtraction) -> RawExtraction:
        return RawExtraction(
            document_summary=generated.document_summary,
            question_answers=OpenAIResponsesClient._compose_extracted_fields(
                generated.question_answers,
                field_group="question_answer",
            ),
            schedule_answers=OpenAIResponsesClient._compose_extracted_fields(
                generated.schedule_answers,
                field_group="schedule_answer",
            ),
            technical_claims=OpenAIResponsesClient._compose_extracted_fields(
                generated.technical_claims,
                field_group="technical_claim",
            ),
            commercial_claims=OpenAIResponsesClient._compose_extracted_fields(
                generated.commercial_claims,
                field_group="commercial_claim",
            ),
            warnings=list(generated.warnings),
        )

    @staticmethod
    def _compose_extracted_fields(
        fields: list[GeneratedExtractedField],
        *,
        field_group: str,
    ) -> list[ExtractedField]:
        return [
            ExtractedField(
                id=field.id,
                label=field.label,
                field_group=field_group,
                question_id=field.question_id,
                schedule_id=field.schedule_id,
                schedule_column_id=field.schedule_column_id,
                criterion_ids=list(field.criterion_ids),
                line_item_id=field.line_item_id,
                state=field.state,
                raw_value=field.raw_value,
                normalized_hint=field.normalized_hint,
                quantity_value=field.quantity_value,
                numeric_value=field.numeric_value,
                currency=field.currency,
                uom=field.uom,
                notes=field.notes,
                evidence=[
                    EvidenceAnchor(
                        id=anchor.id,
                        snippet=anchor.snippet,
                        locator=anchor.locator,
                        source_label=anchor.source_label,
                    )
                    for anchor in field.evidence
                ],
            )
            for field in fields
        ]

    @staticmethod
    def _compose_narrative_scores(
        criteria: list[Criterion],
        parsed: NarrativeCriterionScoreSet,
        reasoning_summary: str | None,
    ) -> list[TechnicalCriterionResult]:
        criteria_by_id = {criterion.id: criterion for criterion in criteria}
        results: list[TechnicalCriterionResult] = []
        for score in parsed.scores:
            criterion = criteria_by_id.get(score.criterion_id)
            if criterion is None:
                continue
            bounded_score = min(score.score, criterion.max_score or score.score)
            explanation = score.explanation
            if reasoning_summary:
                explanation = f"{score.explanation} Reasoning summary: {reasoning_summary}"
            results.append(
                TechnicalCriterionResult(
                    criterion_id=criterion.id,
                    title=criterion.title,
                    criterion_type=criterion.criterion_type,
                    status=TechnicalCriterionStatus.SCORED,
                    score=bounded_score,
                    max_score=criterion.max_score,
                    passed=None,
                    confidence=score.confidence,
                    explanation=explanation,
                    evidence_refs=list(score.evidence_refs),
                    math_trace=[
                        f"Narrative technical score assigned within max score {criterion.max_score or bounded_score:g}.",
                    ],
                    risks=list(score.risks),
                )
            )
        return results

    @staticmethod
    def _build_locked_framework_brief(artifact: LockedFrameworkArtifact) -> str:
        proposal = artifact.rubric_snapshot
        criteria_lines = OpenAIResponsesClient._numbered_lines(
            (
                f"{criterion.id} | {criterion.title} | {criterion.criterion_type} | "
                f"max {criterion.max_score if criterion.max_score is not None else 'n/a'} | "
                f"cutoff {criterion.min_cutoff if criterion.min_cutoff is not None else 'n/a'} | "
                f"questions: {', '.join(criterion.linked_question_ids) or 'none'} | "
                f"schedules: {', '.join(criterion.linked_schedule_fields) or 'none'} | "
                f"{OpenAIResponsesClient._shorten(criterion.description, 120)}"
            )
            for criterion in proposal.criteria
        )
        question_lines = OpenAIResponsesClient._numbered_lines(
            f"{question.id}: {question.text} | purpose: {OpenAIResponsesClient._shorten(question.purpose, 90)}"
            for question in proposal.questions
        )
        schedule_lines = OpenAIResponsesClient._numbered_lines(
            (
                f"{schedule.id} ({schedule.name}): "
                + "; ".join(
                    f"{schedule.id}.{column.id} = {column.label} [{column.description}]"
                    for column in schedule.columns
                )
            )
            for schedule in proposal.response_schedules
        )
        line_item_lines = OpenAIResponsesClient._numbered_lines(
            f"{item.id}: {item.product_name} [{item.uom}] - {OpenAIResponsesClient._shorten(item.description, 100)}"
            for item in artifact.rfq_snapshot.line_items
        )
        return (
            f"{OpenAIResponsesClient._build_rfq_brief(artifact.rfq_snapshot)}\n\n"
            f"Official award basis: {proposal.official_award_basis}\n"
            f"Aggregate technical threshold: {proposal.aggregate_technical_threshold}\n\n"
            "Criteria\n"
            f"{criteria_lines}\n\n"
            "Vendor questions\n"
            f"{question_lines}\n\n"
            "Requested schedules\n"
            f"{schedule_lines}\n\n"
            "RFQ line item ids for commercial mapping\n"
            f"{line_item_lines}"
        )

    @staticmethod
    def _build_narrative_criteria_brief(criteria: list[Criterion]) -> str:
        return OpenAIResponsesClient._numbered_lines(
            (
                f"{criterion.id}: {criterion.title} | max score {criterion.max_score or 0:g} | "
                f"{OpenAIResponsesClient._shorten(criterion.description, 160)} | "
                f"evidence check: {criterion.evidence_checks[0].label if criterion.evidence_checks else 'Supporting evidence'}"
            )
            for criterion in criteria
        )

    @staticmethod
    def _build_vendor_review_brief(review: VendorReview) -> str:
        question_lines = OpenAIResponsesClient._numbered_lines(
            (
                f"{field.id} | {field.label} | state {field.state.value} | value: {field.raw_value or 'none'} | "
                f"evidence ids: {', '.join(anchor.id for anchor in field.evidence) or 'none'}"
            )
            for field in review.raw_extraction.question_answers
        )
        schedule_lines = OpenAIResponsesClient._numbered_lines(
            (
                f"{field.id} | {field.label} | state {field.state.value} | value: {field.raw_value or 'none'} | "
                f"evidence ids: {', '.join(anchor.id for anchor in field.evidence) or 'none'}"
            )
            for field in review.raw_extraction.schedule_answers
        )
        technical_lines = OpenAIResponsesClient._numbered_lines(
            (
                f"{field.id} | {field.label} | state {field.state.value} | value: {field.raw_value or 'none'} | "
                f"notes: {field.notes or 'none'} | evidence ids: {', '.join(anchor.id for anchor in field.evidence) or 'none'}"
            )
            for field in review.raw_extraction.technical_claims
        )
        pricing_lines = OpenAIResponsesClient._numbered_lines(
            (
                f"{line.line_item_id} | {line.line_item_name} | quoted total {line.total_price if line.total_price is not None else 'n/a'} "
                f"{line.currency or ''} | base total {line.base_currency_total if line.base_currency_total is not None else 'n/a'} | "
                f"status {line.comparability_status.value} | evidence ids: {', '.join(line.evidence_refs) or 'none'}"
            )
            for line in review.normalized_pricing
        )
        return (
            f"Document summary: {review.raw_extraction.document_summary}\n\n"
            "Question answers\n"
            f"{question_lines}\n\n"
            "Schedule answers\n"
            f"{schedule_lines}\n\n"
            "Technical claims\n"
            f"{technical_lines}\n\n"
            "Normalized pricing\n"
            f"{pricing_lines}\n\n"
            f"Review blockers: {', '.join(review.blockers) or 'none'}"
        )

    @staticmethod
    def _build_technical_results_brief(results: list[TechnicalEvaluationResult]) -> str:
        return OpenAIResponsesClient._numbered_lines(
            (
                f"{result.vendor_id} ({result.vendor_name}) | passed gate: {result.passed_gate} | "
                f"aggregate technical score: {result.aggregate_score:g} | "
                f"reasons: {', '.join(result.disqualification_reasons) or 'none'}"
            )
            for result in results
        )

    @staticmethod
    def _build_commercial_results_brief(results: list[CommercialEvaluationResult]) -> str:
        return OpenAIResponsesClient._numbered_lines(
            (
                f"{result.vendor_id} ({result.vendor_name}) | award ready: {result.award_ready} | "
                f"comparable total: {result.comparable_total if result.comparable_total is not None else 'n/a'} "
                f"{result.base_currency} | commercial score: {result.commercial_score if result.commercial_score is not None else 'n/a'} | "
                f"blockers: {', '.join(result.blockers) or 'none'}"
            )
            for result in results
        )

    @staticmethod
    def _lookup_vendor_name(results: list[TechnicalEvaluationResult], vendor_id: str) -> str:
        match = next((result.vendor_name for result in results if result.vendor_id == vendor_id), vendor_id)
        return match

    @staticmethod
    def _rank_eligible_vendor_ids(
        technical_results: list[TechnicalEvaluationResult],
        commercial_results: list[CommercialEvaluationResult],
    ) -> list[str]:
        commercial_by_vendor = {
            result.vendor_id: result
            for result in commercial_results
            if result.award_ready and result.commercial_score is not None
        }
        ranked = [
            (
                result.vendor_id,
                0.7 * result.aggregate_score + 0.3 * (commercial_by_vendor[result.vendor_id].commercial_score or 0.0),
            )
            for result in technical_results
            if result.passed_gate and result.vendor_id in commercial_by_vendor
        ]
        ranked.sort(key=lambda item: item[1], reverse=True)
        return [vendor_id for vendor_id, _score in ranked]

    @staticmethod
    def _coerce_scenario_winner(
        *,
        requested_winner_id: str,
        ranking: list[ScenarioRankingItem],
        eligible_vendor_ids: list[str],
        fallback_winner_id: str,
    ) -> str:
        if requested_winner_id in eligible_vendor_ids:
            return requested_winner_id
        for item in ranking:
            if item.vendor_id in eligible_vendor_ids:
                return item.vendor_id
        return fallback_winner_id

    @staticmethod
    def _extract_reasoning_summary(response: object) -> str | None:
        output_items = getattr(response, "output", None)
        if not output_items:
            return None
        for item in output_items:
            if getattr(item, "type", None) != "reasoning":
                continue
            summaries = getattr(item, "summary", None) or []
            parts: list[str] = []
            for summary in summaries:
                text = getattr(summary, "text", None)
                if text:
                    parts.append(text)
            if parts:
                return " ".join(parts)
        return None

    @staticmethod
    def _looks_like_truncated_output(exc: Exception) -> bool:
        message = str(exc).lower()
        return (
            "invalid json" in message
            or "json_invalid" in message
            or "eof while parsing" in message
            or "unterminated" in message
        )

    @staticmethod
    def _dedupe(values: list[str] | tuple[str, ...] | set[str] | object) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value not in seen:
                seen.add(value)
                ordered.append(value)
        return ordered

    @staticmethod
    def _shorten(value: str, limit: int) -> str:
        compact = " ".join(value.split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 3].rstrip()}..."

    @staticmethod
    def _numbered_lines(values: Iterable[str]) -> str:
        return "\n".join(f"{index}. {value}" for index, value in enumerate(values, start=1))
