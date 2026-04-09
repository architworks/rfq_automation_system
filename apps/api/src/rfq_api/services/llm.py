from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable
from typing import Annotated, Literal, TypeVar, cast

from openai import OpenAI
from pydantic import BaseModel, Field

from ..config import Settings
from ..models import (
    OFFICIAL_AWARD_BASIS,
    Criterion,
    CriterionType,
    EvidenceCheck,
    Question,
    ResponseSchedule,
    RFQDraft,
    RubricProposal,
    RubricSection,
    ScheduleColumn,
)


class LLMConfigurationError(RuntimeError):
    pass


class RubricGenerationError(RuntimeError):
    pass


class LLMClient(ABC):
    @abstractmethod
    def generate_rubric(self, rfq_draft: RFQDraft) -> RubricProposal:
        raise NotImplementedError


Identifier = Annotated[str, Field(min_length=2, max_length=40, pattern=r"^[a-z][a-z0-9_]*$")]
ShortTitle = Annotated[str, Field(min_length=3, max_length=72)]
BodyText = Annotated[str, Field(min_length=8, max_length=180)]
PurposeText = Annotated[str, Field(min_length=8, max_length=120)]
ReasonText = Annotated[str, Field(min_length=8, max_length=160)]


class GeneratedSection(BaseModel):
    id: Identifier
    title: ShortTitle
    description: BodyText


class GeneratedEvidenceCheck(BaseModel):
    id: Identifier
    label: ShortTitle
    description: PurposeText


class CriterionDraft(BaseModel):
    id: Identifier
    section_id: Identifier
    title: ShortTitle
    description: BodyText
    criterion_type: CriterionType
    weight: float | None = Field(default=None, ge=0, le=100)
    min_cutoff: float | None = Field(default=None, ge=0, le=100)
    max_score: float | None = Field(default=None, ge=0, le=100)
    evidence_checks: list[GeneratedEvidenceCheck] = Field(default_factory=list, min_length=1, max_length=1)


class GeneratedQuestion(BaseModel):
    id: Identifier
    text: BodyText
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
            "Use cutoff-backed criteria only for a small number of critical technical risks. "
            "Technical scored and cutoff-backed criteria together must total 100 points, "
            "and each scored criterion must use the same value for weight and max_score. "
            "Commercial criteria must have no weight and no cutoff. "
            "Set one aggregate technical threshold for qualified bids. "
            "Every criterion must include exactly one evidence check. "
            "Questions must be mutually distinct and collectively cover the criteria without unnecessary overlap. "
            "Schedules must capture structured vendor inputs a buyer can compare later. "
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
                input_text=input_text,
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
                "Keep titles short, keep descriptions under 80 characters, avoid duplicate phrasing, "
                "and do not include extra narrative."
            )
            try:
                return self._parse_once(
                    instructions=retry_instructions,
                    input_text=input_text,
                    text_format=text_format,
                )
            except Exception as retry_exc:  # pragma: no cover - network/runtime dependent
                raise RubricGenerationError(f"{error_label} failed: {retry_exc}") from retry_exc

    def _parse_once(
        self,
        *,
        instructions: str,
        input_text: str,
        text_format: type[ParsedModelT],
    ) -> ParsedModelT:
        response = self._client.responses.parse(
            model=self._model,
            instructions=instructions,
            input=input_text,
            text_format=text_format,
        )
        parsed = cast(ParsedModelT | None, response.output_parsed)
        if parsed is None:
            raise RubricGenerationError("Structured output call returned no parsed object.")
        return parsed

    @staticmethod
    def _build_rfq_brief(rfq_draft: RFQDraft) -> str:
        timeline_lines = OpenAIResponsesClient._numbered_lines(
            f"{item.label} ({item.target_date}): {OpenAIResponsesClient._shorten(item.description, 90)}"
            for item in rfq_draft.timelines
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
            f"Title: {rfq_draft.general_info.title}\n"
            f"Code: {rfq_draft.general_info.rfq_code}\n"
            f"Owner: {rfq_draft.general_info.owner}\n"
            f"Region: {rfq_draft.general_info.region}\n\n"
            "Scope\n"
            f"{OpenAIResponsesClient._shorten(rfq_draft.scope_overview, 320)}\n\n"
            "Milestones\n"
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
            criteria.append(
                Criterion(
                    id=criterion.id,
                    section_id=criterion.section_id,
                    title=criterion.title,
                    description=criterion.description,
                    criterion_type=criterion.criterion_type,
                    weight=criterion.weight,
                    min_cutoff=criterion.min_cutoff,
                    max_score=criterion.max_score,
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
