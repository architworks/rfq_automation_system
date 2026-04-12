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
    BuyerPriority,
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
    LLMSettings,
    LineItem,
    LockedFrameworkArtifact,
    Question,
    RawExtraction,
    ResponseState,
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
    ValidationIssue,
    VendorDocument,
    VendorRecord,
    VendorReview,
)
from .normalization_catalog import ALLOWED_EXTRACTION_UOM_TOKENS, supported_currency_codes


class LLMConfigurationError(RuntimeError):
    pass


class LLMTaskError(RuntimeError):
    pass


class RubricGenerationError(LLMTaskError):
    pass


class LLMClient(ABC):
    @abstractmethod
    def generate_rubric(
        self,
        rfq_draft: RFQDraft,
        *,
        llm_settings: LLMSettings,
        repair_feedback: list[ValidationIssue] | None = None,
    ) -> RubricProposal:
        raise NotImplementedError

    @abstractmethod
    def extract_vendor_response(
        self,
        *,
        artifact: LockedFrameworkArtifact,
        vendor: VendorRecord,
        document: VendorDocument,
        document_bytes: bytes,
        llm_settings: LLMSettings,
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
        llm_settings: LLMSettings,
    ) -> list[TechnicalCriterionResult]:
        raise NotImplementedError

    @abstractmethod
    def generate_ai_scenarios(
        self,
        *,
        artifact: LockedFrameworkArtifact,
        technical_results: list[TechnicalEvaluationResult],
        commercial_results: list[CommercialEvaluationResult],
        llm_settings: LLMSettings,
    ) -> list[ScenarioResult]:
        raise NotImplementedError


Identifier = Annotated[str, Field(min_length=2, max_length=40, pattern=r"^[a-z][a-z0-9_]*$")]
ShortTitle = Annotated[str, Field(min_length=3)]
DescriptionText = Annotated[str, Field(min_length=8)]
QuestionText = Annotated[str, Field(min_length=12)]
PurposeText = Annotated[str, Field(min_length=8)]
ReasonText = Annotated[str, Field(min_length=8)]
FormatText = Annotated[str, Field(min_length=3)]
ConditionText = Annotated[str, Field(min_length=3)]
LongText = Annotated[str, Field(min_length=8)]
LocatorText = Annotated[str, Field(min_length=2)]
FreeText = Annotated[str, Field(min_length=1)]
UomToken = Annotated[str, Field(min_length=1, max_length=12)]


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


class GeneratedCriterionQuestion(BaseModel):
    id: Identifier
    text: QuestionText
    purpose: PurposeText


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
    vendor_question: GeneratedCriterionQuestion | None = None
    deterministic_scoring: GeneratedDeterministicScoringGuide | None = None
    qualitative_scoring_guidance: LongText | None = None


class GeneratedScheduleColumn(BaseModel):
    id: Identifier
    label: ShortTitle
    description: PurposeText
    required: bool = True


class GeneratedResponseSchedule(BaseModel):
    id: Identifier
    name: ShortTitle
    purpose: PurposeText
    columns: list[GeneratedScheduleColumn] = Field(default_factory=list, min_length=1, max_length=6)
    linked_criteria: list[Identifier] = Field(default_factory=list, min_length=1, max_length=4)


class LLMRubricProposal(BaseModel):
    sections: list[GeneratedSection] = Field(min_length=2, max_length=4)
    criteria: list[CriterionDraft] = Field(min_length=6, max_length=9)
    aggregate_technical_threshold: float = Field(ge=0, le=100)
    response_schedules: list[GeneratedResponseSchedule] = Field(min_length=2, max_length=3)
    official_award_basis: Literal["QCBS 70/30"] = OFFICIAL_AWARD_BASIS
    generation_rationale: list[ReasonText] = Field(min_length=2, max_length=4)


class GeneratedEvidenceAnchor(BaseModel):
    id: Identifier
    snippet: FreeText
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
    raw_value: FreeText | None = None
    normalized_hint: FreeText | None = None
    quantity_value: float | None = None
    numeric_value: float | None = None
    currency: Annotated[str, Field(min_length=3, max_length=8)] | None = None
    uom: UomToken | None = None
    notes: FreeText | None = None
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

    def generate_rubric(
        self,
        rfq_draft: RFQDraft,
        *,
        llm_settings: LLMSettings,
        repair_feedback: list[ValidationIssue] | None = None,
    ) -> RubricProposal:
        rfq_brief = self._build_rfq_brief(rfq_draft)
        instructions = (
            "Design one complete RFQ evaluation framework from the supplied RFQ brief. "
            "Stay generic to procurement logic and use only details present in the RFQ brief. "
            "When the RFQ brief marks buyer priorities or mandatory conditions as not provided, "
            "infer them from the rest of the RFQ details instead of importing sample-specific assumptions. "
            "When buyer priorities or mandatory conditions are provided in the RFQ brief, treat them as authoritative "
            "and do not replace them with inferred alternatives. "
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
            "For every non-commercial criterion, include one nested vendor_question inside that criterion instead of returning a separate question list. "
            "Questions must be mutually distinct and collectively cover the criteria without unnecessary overlap. "
            "Enforce a strict one-to-one mapping between each technical criterion and its vendor-facing question. "
            "Every technical criterion, including every MAC criterion, must own exactly one vendor-facing question. "
            "Do not create evaluator-only technical criteria or hidden MAC gates with no vendor-facing question. "
            "Do not reuse the same technical question across multiple technical criteria, even when the topics are related. "
            "If two technical criteria are both needed, write two separate questions with narrower intent instead of one shared question. "
            "If a mandatory gate and a scored technical judgement are related, they must still use separate questions. "
            "Do not use schedules as the primary scoring source for technical criteria. "
            "Use schedules mainly for commercial quoting or supplementary structured disclosures. "
            "Vendor-facing question text must be complete and readable, not clipped mid-sentence. "
            "Apply a quantification-first rule to technical criteria. "
            "If a technical intent can be measured reliably through an explicit numeric, binary, or discrete answer "
            "without distorting the procurement intent, ask for that measurable answer directly instead of a broad narrative response. "
            "When a technical criterion can be evaluated directly from a binary answer, an explicit numeric answer, or a discrete stated choice, "
            "you must include a deterministic_scoring guide with explicit rules and keep qualitative_scoring_guidance null. "
            "Leave deterministic_scoring null only for technical criteria where objective measurement would distort the real judgement. "
            "For every such qualitative technical criterion, populate qualitative_scoring_guidance with concise internal judging guidance describing "
            "what the AI should look for, what strong evidence looks like, and what weak or risky evidence looks like. "
            "For MAC criteria, use crisp binary or discrete vendor questions whenever possible. "
            "If one mandatory condition contains two separate intents, split it into separate criteria with separate questions instead of leaving one criterion under-specified. "
            "Commercial response schedules must ask for structured values in separate columns whenever that improves extraction reliability. "
            "For line-item pricing capture, prefer separate fields for line-item reference, currency, total price, quantity if applicable, UOM if applicable, and exclusions or assumptions, instead of one free-text commercial narrative. "
            "Do not turn commercial quote structure into technical criteria. "
            "Keep titles short, descriptions concise, and avoid repeating the RFQ narrative."
        )
        if repair_feedback:
            instructions = (
                f"{instructions} "
                "The previous rubric draft failed downstream validation. "
                "Regenerate the entire rubric from scratch and fix every issue listed below. "
                "Do not patch only one field in isolation; return one coherent replacement rubric that satisfies all feedback."
            )
        input_text = (
            "Create one coherent rubric for this RFQ brief.\n\n"
            f"{rfq_brief}"
        )
        if repair_feedback:
            input_text = (
                f"{input_text}\n\n"
                "Validation issues to fix in this full regeneration\n"
                f"{self._format_validation_feedback(repair_feedback)}"
            )
        generated = self._parse_structured_output(
            instructions=instructions,
            input_text=input_text,
            text_format=LLMRubricProposal,
            error_label="Rubric generation",
            llm_settings=llm_settings,
        )
        return self._compose_rubric(generated)

    def extract_vendor_response(
        self,
        *,
        artifact: LockedFrameworkArtifact,
        vendor: VendorRecord,
        document: VendorDocument,
        document_bytes: bytes,
        llm_settings: LLMSettings,
    ) -> RawExtraction:
        framework_brief = self._build_locked_framework_brief(artifact)
        file_data = build_file_data_url(document, document_bytes)
        instructions = (
            "Extract only information that is explicitly grounded in the vendor document and relevant to the locked RFQ framework. "
            "Do not invent answers, prices, experience, or evidence. "
            "For every buyer question and every requested schedule field, return one field object even if the answer is missing. "
            "Use the response states answered, missing_vendor_response, missing_extractable_evidence, conflicting_evidence, or not_applicable precisely. "
            "All line-item commercial pricing must be captured through schedule_answers, not through commercial_claims. "
            "For every quoted RFQ line item, return schedule_answers with the appropriate schedule_id, schedule_column_id, and line_item_id so pricing normalization can operate only from the schedule rows. "
            "Use commercial_claims only for supporting commercial notes, exclusions, assumptions, or anomalies that do not fit a requested schedule field. "
            "Capture short evidence snippets and precise locators such as page, slide, sheet, row, or cell. "
            "Populate the structured numeric fields explicitly instead of burying values inside prose. "
            "Use raw_value for the exact source text or table cell text, but store the parsed numeric amount separately in numeric_value, "
            "the explicit currency code separately in currency, the explicit quantity separately in quantity_value, and the explicit unit separately in uom. "
            "For quoted commercial totals, numeric_value must contain only the monetary amount, never the currency symbol or unit text. "
            "When a quantity and unit are stated, quantity_value and uom must be populated separately from the price amount. "
            "Do not normalize or convert currencies or units during extraction. "
            "For technical questions tied to numeric deterministic scoring, populate numeric_value only when the vendor explicitly states a number. "
            "Do not infer counts from narrative examples, named project lists, or descriptive prose. "
            "If a numeric technical question is answered vaguely or descriptively without an explicit number, keep the raw answer and evidence but mark it as missing_extractable_evidence for scoring. "
            "Use quantity_value only when the document states a quantity clearly, and numeric_value only when an explicit comparable number is visible in the document. "
            f"When a unit is visible, use one of these canonical UOM tokens where the document clearly supports it: {', '.join(ALLOWED_EXTRACTION_UOM_TOKENS)}. "
            f"When a currency is visible, prefer a standard code from this supported list when the document clearly supports it: {', '.join(supported_currency_codes())}."
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
            llm_settings=llm_settings,
        )
        raw_extraction = self._compose_raw_extraction(extracted)
        self._enforce_numeric_question_expectations(raw_extraction, artifact)
        return raw_extraction

    def score_narrative_technical(
        self,
        *,
        artifact: LockedFrameworkArtifact,
        vendor: VendorRecord,
        review: VendorReview,
        criteria: list[Criterion],
        llm_settings: LLMSettings,
    ) -> list[TechnicalCriterionResult]:
        if not criteria:
            return []

        criteria_brief = self._build_narrative_criteria_brief(criteria, artifact)
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
            llm_settings=llm_settings,
        )
        return self._compose_narrative_scores(criteria, parsed, reasoning_summary)

    def generate_ai_scenarios(
        self,
        *,
        artifact: LockedFrameworkArtifact,
        technical_results: list[TechnicalEvaluationResult],
        commercial_results: list[CommercialEvaluationResult],
        llm_settings: LLMSettings,
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
            llm_settings=llm_settings,
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
        llm_settings: LLMSettings,
    ) -> ParsedModelT:
        try:
            return self._parse_once(
                instructions=instructions,
                input_payload=input_text,
                text_format=text_format,
                llm_settings=llm_settings,
            )
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            if not self._looks_like_truncated_output(exc):
                raise RubricGenerationError(f"{error_label} failed: {exc}") from exc

            retry_instructions = (
                f"{instructions} "
                "Retry in ultra-compact mode. "
                "Use a compact response shape that still satisfies the schema. "
                "Prefer 2 sections, 6 criteria, 2 schedules, and 2 rationale bullets. "
                "Keep every free-text field complete and readable even in compact mode. "
                "Do not clip sentences or abbreviate content unnaturally. "
                "Avoid duplicate phrasing and do not include extra narrative."
            )
            try:
                return self._parse_once(
                    instructions=retry_instructions,
                    input_payload=input_text,
                    text_format=text_format,
                    llm_settings=llm_settings,
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
        llm_settings: LLMSettings,
    ) -> ParsedModelT:
        try:
            return self._parse_once(
                instructions=instructions,
                input_payload=input_payload,
                text_format=text_format,
                llm_settings=llm_settings,
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
        llm_settings: LLMSettings,
    ) -> tuple[ParsedModelT, str | None]:
        try:
            return self._parse_once_with_reasoning(
                instructions=instructions,
                input_payload=input_payload,
                text_format=text_format,
                llm_settings=llm_settings,
            )
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            raise LLMTaskError(f"{error_label} failed: {exc}") from exc

    def _parse_once(
        self,
        *,
        instructions: str,
        input_payload: str | list[dict[str, object]],
        text_format: type[ParsedModelT],
        llm_settings: LLMSettings,
    ) -> ParsedModelT:
        response = self._client.responses.parse(
            model=self._model,
            instructions=instructions,
            input=input_payload,
            text_format=text_format,
            reasoning={"effort": llm_settings.reasoning_effort.value},
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
        llm_settings: LLMSettings,
    ) -> tuple[ParsedModelT, str | None]:
        response = self._client.responses.parse(
            model=self._model,
            instructions=instructions,
            input=input_payload,
            text_format=text_format,
            reasoning={
                "effort": llm_settings.reasoning_effort.value,
                "summary": "auto",
            },
        )
        parsed = cast(ParsedModelT | None, response.output_parsed)
        if parsed is None:
            raise LLMTaskError("Structured output call returned no parsed object.")
        return parsed, self._extract_reasoning_summary(response)

    @staticmethod
    def _format_validation_feedback(issues: list[ValidationIssue]) -> str:
        return OpenAIResponsesClient._numbered_lines(
            f"{issue.field}: {issue.message}"
            for issue in issues
        )

    @staticmethod
    def _build_rfq_brief(rfq_draft: RFQDraft) -> str:
        priorities = OpenAIResponsesClient._meaningful_buyer_priorities(rfq_draft)
        mandatory_conditions = OpenAIResponsesClient._meaningful_mandatory_conditions(rfq_draft)
        line_items = OpenAIResponsesClient._meaningful_line_items(rfq_draft)
        timeline_lines = OpenAIResponsesClient._numbered_lines(
            [
                f"Clarifications deadline: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.timelines.clarifications_deadline)}",
                f"Technical bid deadline: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.timelines.technical_bid_deadline)}",
                f"Commercial bid deadline: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.timelines.commercial_bid_deadline)}",
                f"Evaluation start date: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.timelines.evaluation_start_date)}",
                f"Negotiation start date: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.timelines.negotiation_start_date)}",
                f"Final award date: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.timelines.final_award_date)}",
            ]
        )
        priority_lines = (
            OpenAIResponsesClient._numbered_lines(
                f"{OpenAIResponsesClient._value_or_placeholder(item.title, '[UNNAMED PRIORITY]')}: "
                f"{OpenAIResponsesClient._shorten(OpenAIResponsesClient._value_or_placeholder(item.description, '[NO DESCRIPTION PROVIDED]'), 90)}"
                for item in priorities
            )
            if priorities
            else "[NOT PROVIDED]. ACTION: Infer 3 strategic technical priorities based on the RFQ details provided."
        )
        mandatory_lines = (
            OpenAIResponsesClient._numbered_lines(
                OpenAIResponsesClient._shorten(item, 100)
                for item in mandatory_conditions
            )
            if mandatory_conditions
            else "[NOT PROVIDED]. ACTION: Infer 3-5 pass/fail mandatory gates based on the RFQ details provided."
        )
        line_item_lines = (
            OpenAIResponsesClient._numbered_lines(
                (
                    f"{OpenAIResponsesClient._value_or_placeholder(item.product_name, '[UNNAMED LINE ITEM]')} "
                    f"[{OpenAIResponsesClient._value_or_placeholder(item.category, 'category not provided')}, "
                    f"{OpenAIResponsesClient._value_or_placeholder(item.uom, 'uom not provided')}]: "
                    f"{OpenAIResponsesClient._shorten(OpenAIResponsesClient._value_or_placeholder(item.description, '[NO DESCRIPTION PROVIDED]'), 110)} "
                    f"(HSN/SAC: {OpenAIResponsesClient._value_or_placeholder(item.hsn_sac, 'not provided')})"
                )
                for item in line_items
            )
            if line_items
            else "[NOT PROVIDED]."
        )

        return (
            "RFQ summary\n"
            f"Subject: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.general_info.subject)}\n"
            f"Code: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.general_info.rfq_code)}\n"
            f"Sourcing type: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.general_info.sourcing_type)}\n"
            f"Round: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.general_info.round)}\n"
            f"Status: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.general_info.status)}\n"
            f"Owner: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.general_info.owner)}\n"
            f"Currency: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.general_info.currency)}\n"
            f"Requestor: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.general_info.requestor)}\n"
            f"Department: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.general_info.department)}\n"
            f"Category: {OpenAIResponsesClient._value_or_not_provided(rfq_draft.general_info.category)}\n\n"
            "Scope\n"
            f"{OpenAIResponsesClient._shorten(OpenAIResponsesClient._value_or_not_provided(rfq_draft.scope_overview), 320)}\n\n"
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
        schedule_links: dict[str, list[str]] = defaultdict(list)
        questions = []

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
            normalized_question = OpenAIResponsesClient._normalize_generated_vendor_question(criterion)
            normalized_type = OpenAIResponsesClient._normalize_generated_criterion_type(
                criterion=criterion,
                vendor_question=normalized_question,
            )
            weight = criterion.weight
            min_cutoff = criterion.min_cutoff
            max_score = criterion.max_score
            linked_question_ids = [normalized_question.id] if normalized_question is not None else []
            linked_schedule_fields = OpenAIResponsesClient._dedupe(schedule_links[criterion.id])
            qualitative_scoring_guidance = criterion.qualitative_scoring_guidance
            if normalized_type == CriterionType.COMMERCIAL:
                weight = None
                min_cutoff = None
                max_score = None
                qualitative_scoring_guidance = None
                normalized_question = None
            elif normalized_type == CriterionType.MAC:
                qualitative_scoring_guidance = None
            elif criterion.deterministic_scoring is not None:
                qualitative_scoring_guidance = None
            else:
                qualitative_scoring_guidance = OpenAIResponsesClient._normalize_qualitative_guidance(
                    criterion=criterion,
                    evidence_checks=evidence_checks,
                )
            if normalized_type != CriterionType.COMMERCIAL:
                linked_schedule_fields = []
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
                    vendor_question=normalized_question,
                    linked_question_ids=linked_question_ids,
                    linked_schedule_fields=linked_schedule_fields,
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
                    qualitative_scoring_guidance=qualitative_scoring_guidance,
                )
            )
            if normalized_question is not None:
                questions.append(normalized_question.model_copy(deep=True))

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
        vendor_question: Question | None,
    ) -> CriterionType:
        if criterion.criterion_type == CriterionType.COMMERCIAL:
            return CriterionType.COMMERCIAL

        snippets = [criterion.title, criterion.description]
        if vendor_question is not None:
            snippets.extend([vendor_question.text, vendor_question.purpose])

        commercial_text = " ".join(snippets).lower()
        if any(
            keyword in commercial_text
            for keyword in ("commercial", "pricing", "price", "quote", "quoted", "cost", "currency", "fee")
        ):
            return CriterionType.COMMERCIAL

        return criterion.criterion_type

    @staticmethod
    def _normalize_generated_vendor_question(criterion: CriterionDraft) -> Question | None:
        generated_question = criterion.vendor_question
        if generated_question is None:
            return None
        return Question(
            id=generated_question.id,
            text=generated_question.text,
            purpose=generated_question.purpose,
            linked_criteria=[criterion.id],
        )

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
        base_currency = artifact.rfq_snapshot.general_info.currency or "not provided"
        criteria_lines = OpenAIResponsesClient._numbered_lines(
            (
                f"{criterion.id} | {criterion.title} | {criterion.criterion_type} | "
                f"max {criterion.max_score if criterion.max_score is not None else 'n/a'} | "
                f"cutoff {criterion.min_cutoff if criterion.min_cutoff is not None else 'n/a'} | "
                f"question: {criterion.linked_question_ids[0] if criterion.linked_question_ids else 'none'} | "
                f"guide: {criterion.deterministic_scoring.guide_type if criterion.deterministic_scoring is not None else 'qualitative'} | "
                f"answer format: {criterion.deterministic_scoring.answer_format if criterion.deterministic_scoring is not None else 'narrative judgement'} | "
                f"schedules: {', '.join(criterion.linked_schedule_fields) or 'none'} | "
                f"qualitative guidance: {OpenAIResponsesClient._shorten(criterion.qualitative_scoring_guidance or 'none', 140)} | "
                f"{OpenAIResponsesClient._shorten(criterion.description, 120)}"
            )
            for criterion in proposal.criteria
        )
        question_lines = OpenAIResponsesClient._numbered_lines(
            (
                f"{question.id}: {question.text} | purpose: {OpenAIResponsesClient._shorten(question.purpose, 90)} | "
                f"linked criterion: {question.linked_criteria[0] if question.linked_criteria else 'none'} | "
                f"expected answer: {OpenAIResponsesClient._expected_answer_summary(question.id, proposal.criteria)}"
            )
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
            "Commercial normalization basis\n"
            f"RFQ base currency: {base_currency}\n"
            f"Allowed UOM tokens for structured extraction: {', '.join(ALLOWED_EXTRACTION_UOM_TOKENS)}\n"
            "UOM conversion policy: only weight and volume units convert mathematically; Lot and Count do not convert.\n\n"
            "Commercial extraction rule: line-item pricing must be returned via schedule_answers only; commercial_claims are for supporting notes only.\n\n"
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
    def _build_narrative_criteria_brief(
        criteria: list[Criterion],
        artifact: LockedFrameworkArtifact,
    ) -> str:
        questions_by_id = {
            question.id: question
            for question in artifact.rubric_snapshot.questions
        }
        return OpenAIResponsesClient._numbered_lines(
            (
                f"{criterion.id}: {criterion.title} | max score {criterion.max_score or 0:g} | "
                f"{OpenAIResponsesClient._shorten(criterion.description, 160)} | "
                f"question: {questions_by_id[criterion.linked_question_ids[0]].text if criterion.linked_question_ids and criterion.linked_question_ids[0] in questions_by_id else 'none'} | "
                f"guidance: {OpenAIResponsesClient._shorten(criterion.qualitative_scoring_guidance or 'none', 180)} | "
                f"evidence check: {criterion.evidence_checks[0].description if criterion.evidence_checks else 'Supporting evidence'}"
            )
            for criterion in criteria
        )

    @staticmethod
    def _build_vendor_review_brief(review: VendorReview) -> str:
        question_lines = OpenAIResponsesClient._numbered_lines(
            (
                f"{field.id} | {field.label} | state {field.state.value} | value: {field.raw_value or 'none'} | "
                f"numeric: {field.numeric_value if field.numeric_value is not None else 'n/a'} | "
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
                f"notes: {field.notes or 'none'} | numeric: {field.numeric_value if field.numeric_value is not None else 'n/a'} | "
                f"evidence ids: {', '.join(anchor.id for anchor in field.evidence) or 'none'}"
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
    def _expected_answer_summary(question_id: str, criteria: list[Criterion]) -> str:
        criterion = next(
            (
                item
                for item in criteria
                if question_id in item.linked_question_ids
            ),
            None,
        )
        if criterion is None:
            return "Not specified."
        if criterion.deterministic_scoring is not None:
            return (
                f"{criterion.deterministic_scoring.guide_type} | "
                f"{criterion.deterministic_scoring.answer_format}"
            )
        return "Qualitative narrative response."

    @staticmethod
    def _normalize_qualitative_guidance(
        *,
        criterion: CriterionDraft,
        evidence_checks: list[GeneratedEvidenceCheck],
    ) -> str:
        guidance = " ".join((criterion.qualitative_scoring_guidance or "").split())
        if guidance:
            return guidance
        evidence_text = evidence_checks[0].description if evidence_checks else "Look for direct supporting evidence."
        return (
            f"Judge how well the response addresses {criterion.description}. "
            f"Strong evidence should be specific, credible, and implementation-ready. "
            f"Weak or risky evidence should be vague, generic, unsupported, or incomplete. "
            f"Evaluator check: {evidence_text}"
        )

    @staticmethod
    def _enforce_numeric_question_expectations(
        raw_extraction: RawExtraction,
        artifact: LockedFrameworkArtifact,
    ) -> None:
        numeric_question_ids = {
            criterion.linked_question_ids[0]
            for criterion in artifact.rubric_snapshot.criteria
            if criterion.criterion_type in {
                CriterionType.TECHNICAL_CUTOFF_BACKED,
                CriterionType.TECHNICAL_SCORED_ONLY,
            }
            and criterion.deterministic_scoring is not None
            and criterion.deterministic_scoring.guide_type == DeterministicScoringType.NUMERIC_BANDED
            and len(criterion.linked_question_ids) == 1
        }

        for field in raw_extraction.question_answers:
            if field.question_id not in numeric_question_ids:
                continue
            if field.numeric_value is None and field.state == ResponseState.ANSWERED:
                field.state = ResponseState.MISSING_EXTRACTABLE_EVIDENCE

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

    @staticmethod
    def _value_or_not_provided(value: str) -> str:
        compact = " ".join(value.split())
        return compact or "[NOT PROVIDED]"

    @staticmethod
    def _value_or_placeholder(value: str, placeholder: str) -> str:
        compact = " ".join(value.split())
        return compact or placeholder

    @staticmethod
    def _meaningful_buyer_priorities(rfq_draft: RFQDraft) -> list[BuyerPriority]:
        return [
            item
            for item in rfq_draft.buyer_priorities
            if item.title.strip() or item.description.strip()
        ]

    @staticmethod
    def _meaningful_mandatory_conditions(rfq_draft: RFQDraft) -> list[str]:
        return [item.strip() for item in rfq_draft.mandatory_conditions if item.strip()]

    @staticmethod
    def _meaningful_line_items(rfq_draft: RFQDraft) -> list[LineItem]:
        return [
            item
            for item in rfq_draft.line_items
            if any(
                field.strip()
                for field in (item.product_name, item.category, item.description, item.hsn_sac, item.uom)
            )
        ]
