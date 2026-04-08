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


class GeneralInfo(BaseModel):
    title: str
    rfq_code: str
    owner: str
    region: str


class TimelineItem(BaseModel):
    id: str
    label: str
    target_date: str
    description: str


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
    timelines: list[TimelineItem]
    buyer_priorities: list[BuyerPriority]
    mandatory_conditions: list[str]
    line_items: list[LineItem]


class RubricSection(BaseModel):
    id: str
    title: str
    description: str


class EvidenceCheck(BaseModel):
    id: str
    label: str
    description: str


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


class SessionSnapshot(BaseModel):
    session_id: str
    status: SessionStatus
    rfq_draft: RFQDraft
    rubric_proposal: RubricProposal | None = None
    locked_artifact: LockedFrameworkArtifact | None = None
    updated_at: datetime


class CreateSessionRequest(BaseModel):
    session_id: str | None = None

