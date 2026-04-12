from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


OFFICIAL_AWARD_BASIS = "QCBS 70/30"


class CriterionType(str, Enum):
    MAC = "mac"
    TECHNICAL_CUTOFF_BACKED = "technical_cutoff_backed"
    TECHNICAL_SCORED_ONLY = "technical_scored_only"
    COMMERCIAL = "commercial"


class SessionStatus(str, Enum):
    DRAFT = "draft"
    PROPOSAL_READY = "proposal_ready"
    LOCKED = "locked"


class ReasoningEffort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class VendorStatus(str, Enum):
    NO_DOCUMENT = "no_document"
    UPLOADED = "uploaded"
    EXTRACTED = "extracted"
    EVALUATION_READY = "evaluation_ready"
    EVALUATED = "evaluated"


class ResponseState(str, Enum):
    ANSWERED = "answered"
    MISSING_VENDOR_RESPONSE = "missing_vendor_response"
    MISSING_EXTRACTABLE_EVIDENCE = "missing_extractable_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    NOT_APPLICABLE = "not_applicable"


class ComparabilityStatus(str, Enum):
    COMPARABLE = "comparable"
    NEEDS_BUYER_INPUT = "needs_buyer_input"
    NON_COMPARABLE = "non_comparable"
    INFORMATIONAL = "informational"


class AwardType(str, Enum):
    SINGLE_VENDOR = "single_vendor"
    SPLIT_AWARD = "split_award"


class ScenarioKind(str, Enum):
    OFFICIAL_QCBS = "official_qcbs"
    ADVISORY_LCS = "advisory_lcs"
    ADVISORY_QBS = "advisory_qbs"
    ADVISORY_AI = "advisory_ai"


class TechnicalCriterionStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SCORED = "scored"
    NOT_EVALUATED = "not_evaluated"


class GeneralInfo(BaseModel):
    subject: str
    rfq_code: str
    sourcing_type: str
    round: str
    status: str
    owner: str
    currency: str
    requestor: str
    department: str
    category: str


class RFQTimelineSet(BaseModel):
    clarifications_deadline: str
    technical_bid_deadline: str
    commercial_bid_deadline: str
    evaluation_start_date: str
    negotiation_start_date: str
    final_award_date: str


class BuyerPriority(BaseModel):
    id: str
    title: str
    description: str


class LineItem(BaseModel):
    id: str
    product_name: str
    category: str
    description: str
    hsn_sac: str
    uom: str


class RFQDraft(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    general_info: GeneralInfo
    scope_overview: str
    timelines: RFQTimelineSet
    buyer_priorities: list[BuyerPriority]
    mandatory_conditions: list[str]
    line_items: list[LineItem]


class LLMSettings(BaseModel):
    reasoning_effort: ReasoningEffort = ReasoningEffort.HIGH


class RubricSection(BaseModel):
    id: str
    title: str
    description: str


class EvidenceCheck(BaseModel):
    id: str
    label: str
    description: str


class DeterministicScoringType(str, Enum):
    PASS_FAIL = "pass_fail"
    NUMERIC_BANDED = "numeric_banded"
    DISCRETE_BANDED = "discrete_banded"


class DeterministicScoringRule(BaseModel):
    id: str
    condition: str
    score: float | None = None
    outcome: Literal["pass", "fail"] | None = None


class DeterministicScoringGuide(BaseModel):
    guide_type: DeterministicScoringType
    answer_format: str
    summary: str
    rules: list[DeterministicScoringRule] = Field(default_factory=list)


class Question(BaseModel):
    id: str
    text: str
    purpose: str
    linked_criteria: list[str] = Field(default_factory=list)


class ScheduleColumn(BaseModel):
    id: str
    label: str
    description: str
    required: bool = True


class ResponseSchedule(BaseModel):
    id: str
    name: str
    purpose: str
    columns: list[ScheduleColumn]
    linked_criteria: list[str] = Field(default_factory=list)


class Criterion(BaseModel):
    id: str
    section_id: str
    title: str
    description: str
    criterion_type: CriterionType
    weight: float | None = None
    min_cutoff: float | None = None
    max_score: float | None = None
    evidence_checks: list[EvidenceCheck] = Field(default_factory=list)
    linked_question_ids: list[str] = Field(default_factory=list)
    linked_schedule_fields: list[str] = Field(default_factory=list)
    deterministic_scoring: DeterministicScoringGuide | None = None
    qualitative_scoring_guidance: str | None = None


class RubricProposal(BaseModel):
    sections: list[RubricSection]
    criteria: list[Criterion]
    aggregate_technical_threshold: float
    questions: list[Question]
    response_schedules: list[ResponseSchedule]
    official_award_basis: Literal["QCBS 70/30"] = OFFICIAL_AWARD_BASIS
    generation_rationale: list[str]


class GovernanceInfo(BaseModel):
    official_award_basis: Literal["QCBS 70/30"] = OFFICIAL_AWARD_BASIS
    technical_threshold_strategy: str
    advisory_outputs: list[str]
    persistence_scope: str


class DownloadMetadata(BaseModel):
    file_name: str
    content_type: str = "application/json"


class LockedFrameworkArtifact(BaseModel):
    version: str = "1.0"
    locked_at: datetime
    rfq_snapshot: RFQDraft
    rubric_snapshot: RubricProposal
    governance: GovernanceInfo
    download_metadata: DownloadMetadata


class ValidationIssue(BaseModel):
    field: str
    message: str


class VendorPackQuestion(BaseModel):
    id: str
    text: str
    purpose: str
    linked_criteria: list[str] = Field(default_factory=list)


class VendorPackScheduleField(BaseModel):
    field_id: str
    schedule_id: str
    schedule_name: str
    column_id: str
    label: str
    description: str
    required: bool = True
    linked_criteria: list[str] = Field(default_factory=list)


class VendorPackSchedule(BaseModel):
    id: str
    name: str
    purpose: str
    linked_criteria: list[str] = Field(default_factory=list)
    columns: list[VendorPackScheduleField] = Field(default_factory=list)


class VendorPackCriterion(BaseModel):
    criterion_id: str
    title: str
    criterion_type: CriterionType
    description: str
    linked_question_ids: list[str] = Field(default_factory=list)
    linked_schedule_fields: list[str] = Field(default_factory=list)


class VendorPack(BaseModel):
    rfq_title: str
    official_award_basis: Literal["QCBS 70/30"] = OFFICIAL_AWARD_BASIS
    response_instructions: list[str] = Field(default_factory=list)
    questions: list[VendorPackQuestion] = Field(default_factory=list)
    response_schedules: list[VendorPackSchedule] = Field(default_factory=list)
    criteria: list[VendorPackCriterion] = Field(default_factory=list)


class VendorDocument(BaseModel):
    file_name: str
    mime_type: str
    extension: str
    size_bytes: int
    uploaded_at: datetime
    warnings: list[str] = Field(default_factory=list)


class VendorRecord(BaseModel):
    id: str
    name: str
    status: VendorStatus = VendorStatus.NO_DOCUMENT
    document: VendorDocument | None = None
    warnings: list[str] = Field(default_factory=list)
    extraction_error: str | None = None
    last_extracted_at: datetime | None = None
    last_evaluated_at: datetime | None = None


class EvidenceAnchor(BaseModel):
    id: str
    snippet: str
    locator: str
    source_label: str | None = None


class ExtractedField(BaseModel):
    id: str
    label: str
    field_group: str
    question_id: str | None = None
    schedule_id: str | None = None
    schedule_column_id: str | None = None
    criterion_ids: list[str] = Field(default_factory=list)
    line_item_id: str | None = None
    state: ResponseState
    raw_value: str | None = None
    normalized_hint: str | None = None
    quantity_value: float | None = None
    numeric_value: float | None = None
    currency: str | None = None
    uom: str | None = None
    notes: str | None = None
    evidence: list[EvidenceAnchor] = Field(default_factory=list)


class RawExtraction(BaseModel):
    document_summary: str
    question_answers: list[ExtractedField] = Field(default_factory=list)
    schedule_answers: list[ExtractedField] = Field(default_factory=list)
    technical_claims: list[ExtractedField] = Field(default_factory=list)
    commercial_claims: list[ExtractedField] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class NormalizedField(BaseModel):
    id: str
    label: str
    field_group: str
    criterion_ids: list[str] = Field(default_factory=list)
    line_item_id: str | None = None
    source_field_ids: list[str] = Field(default_factory=list)
    normalized_value: str | None = None
    quantity_value: float | None = None
    numeric_value: float | None = None
    currency: str | None = None
    base_currency_value: float | None = None
    uom: str | None = None
    target_uom: str | None = None
    comparability_status: ComparabilityStatus
    conversion_notes: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class NormalizedPricingLine(BaseModel):
    line_item_id: str
    line_item_name: str
    quantity: float | None = None
    uom: str | None = None
    target_uom: str | None = None
    currency: str | None = None
    total_price: float | None = None
    base_currency_total: float | None = None
    comparability_status: ComparabilityStatus
    exclusions: list[str] = Field(default_factory=list)
    source_field_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    conversion_notes: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class FXRate(BaseModel):
    currency: str
    rate_to_base: float = Field(gt=0)


class UomOverride(BaseModel):
    from_uom: str
    to_uom: str
    factor: float = Field(gt=0)
    line_item_id: str | None = None


class ComparisonSettings(BaseModel):
    base_currency: str
    fx_effective_date: str
    fx_rates: list[FXRate] = Field(default_factory=list)
    uom_overrides: list[UomOverride] = Field(default_factory=list)


class VendorReview(BaseModel):
    vendor_id: str
    document: VendorDocument
    visual_fidelity_warning: str | None = None
    raw_extraction: RawExtraction
    normalized_fields: list[NormalizedField] = Field(default_factory=list)
    normalized_pricing: list[NormalizedPricingLine] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    created_at: datetime


class TechnicalCriterionResult(BaseModel):
    criterion_id: str
    title: str
    criterion_type: CriterionType
    status: TechnicalCriterionStatus
    score: float | None = None
    max_score: float | None = None
    passed: bool | None = None
    confidence: float | None = None
    explanation: str
    evidence_refs: list[str] = Field(default_factory=list)
    math_trace: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class TechnicalEvaluationResult(BaseModel):
    vendor_id: str
    vendor_name: str
    passed_gate: bool
    aggregate_score: float
    threshold: float
    disqualification_reasons: list[str] = Field(default_factory=list)
    criterion_results: list[TechnicalCriterionResult] = Field(default_factory=list)
    summary: str


class CommercialLineItemResult(BaseModel):
    line_item_id: str
    line_item_name: str
    base_currency_total: float | None = None
    comparability_status: ComparabilityStatus
    notes: list[str] = Field(default_factory=list)


class CommercialEvaluationResult(BaseModel):
    vendor_id: str
    vendor_name: str
    eligible_for_commercial: bool
    award_ready: bool
    base_currency: str
    comparable_total: float | None = None
    commercial_score: float | None = None
    line_items: list[CommercialLineItemResult] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    explanation: str
    evidence_refs: list[str] = Field(default_factory=list)


class VendorScoreBreakdown(BaseModel):
    vendor_id: str
    vendor_name: str
    technical_score: float | None = None
    commercial_score: float | None = None
    final_score: float | None = None
    passed_technical_gate: bool = False
    commercially_comparable: bool = False


class ScenarioRankingItem(BaseModel):
    vendor_id: str
    vendor_name: str
    score: float | None = None
    notes: list[str] = Field(default_factory=list)


class AwardRecommendation(BaseModel):
    winner_vendor_id: str | None = None
    award_type: AwardType = AwardType.SINGLE_VENDOR
    eligible_vendor_ids: list[str] = Field(default_factory=list)
    score_breakdown: list[VendorScoreBreakdown] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    explanation: str
    risks: list[str] = Field(default_factory=list)


class ScenarioResult(BaseModel):
    scenario_name: str
    scenario_kind: ScenarioKind
    is_official: bool = False
    winner_vendor_id: str | None = None
    excluded_vendor_ids: list[str] = Field(default_factory=list)
    weighting_or_rule_basis: str
    explanation: str
    evidence_refs: list[str] = Field(default_factory=list)
    ranking: list[ScenarioRankingItem] = Field(default_factory=list)


class EvaluationReport(BaseModel):
    generated_at: datetime
    comparison_settings: ComparisonSettings | None = None
    technical_results: list[TechnicalEvaluationResult] = Field(default_factory=list)
    commercial_results: list[CommercialEvaluationResult] = Field(default_factory=list)
    official_recommendation: AwardRecommendation
    advisory_scenarios: list[ScenarioResult] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class SessionSnapshot(BaseModel):
    session_id: str
    status: SessionStatus
    llm_settings: LLMSettings = Field(default_factory=LLMSettings)
    rfq_draft: RFQDraft
    rubric_proposal: RubricProposal | None = None
    locked_artifact: LockedFrameworkArtifact | None = None
    vendor_pack: VendorPack | None = None
    vendors: list[VendorRecord] = Field(default_factory=list)
    comparison_settings: ComparisonSettings | None = None
    vendor_reviews: list[VendorReview] = Field(default_factory=list)
    evaluation_report: EvaluationReport | None = None
    updated_at: datetime


class CreateSessionRequest(BaseModel):
    session_id: str | None = None


class UpdateLLMSettingsRequest(BaseModel):
    reasoning_effort: ReasoningEffort


class CreateVendorRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class UpdateVendorRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
