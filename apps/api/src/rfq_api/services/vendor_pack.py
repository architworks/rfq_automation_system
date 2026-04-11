from __future__ import annotations

from ..models import (
    LockedFrameworkArtifact,
    VendorPack,
    VendorPackCriterion,
    VendorPackQuestion,
    VendorPackSchedule,
    VendorPackScheduleField,
)


def build_vendor_pack(artifact: LockedFrameworkArtifact) -> VendorPack:
    proposal = artifact.rubric_snapshot

    schedules: list[VendorPackSchedule] = []
    for schedule in proposal.response_schedules:
        linked_field_ids = {field_id for field_id in _schedule_field_ids(schedule.id, schedule.columns)}
        schedules.append(
            VendorPackSchedule(
                id=schedule.id,
                name=schedule.name,
                purpose=schedule.purpose,
                linked_criteria=list(schedule.linked_criteria),
                columns=[
                    VendorPackScheduleField(
                        field_id=f"{schedule.id}.{column.id}",
                        schedule_id=schedule.id,
                        schedule_name=schedule.name,
                        column_id=column.id,
                        label=column.label,
                        description=column.description,
                        required=column.required,
                        linked_criteria=[
                            criterion.id
                            for criterion in proposal.criteria
                            if any(field_id in linked_field_ids for field_id in criterion.linked_schedule_fields)
                            and f"{schedule.id}.{column.id}" in criterion.linked_schedule_fields
                        ],
                    )
                    for column in schedule.columns
                ],
            )
        )

    criteria = [
        VendorPackCriterion(
            criterion_id=criterion.id,
            title=criterion.title,
            criterion_type=criterion.criterion_type,
            description=criterion.description,
            linked_question_ids=list(criterion.linked_question_ids),
            linked_schedule_fields=list(criterion.linked_schedule_fields),
        )
        for criterion in proposal.criteria
    ]

    return VendorPack(
        rfq_title=artifact.rfq_snapshot.general_info.subject,
        response_instructions=[
            "Submit one complete response document covering all questionnaire items and schedules.",
            "Quote all applicable RFQ line items and state exclusions or assumptions clearly.",
            "Provide evidence for technical claims so the buyer can verify qualification and scoring.",
            "Where a schedule field is requested, present the information in a clearly identifiable table or section.",
        ],
        questions=[
            VendorPackQuestion(
                id=question.id,
                text=question.text,
                purpose=question.purpose,
                linked_criteria=list(question.linked_criteria),
            )
            for question in proposal.questions
        ],
        response_schedules=schedules,
        criteria=criteria,
    )


def _schedule_field_ids(schedule_id: str, columns: list) -> list[str]:
    return [f"{schedule_id}.{column.id}" for column in columns]
