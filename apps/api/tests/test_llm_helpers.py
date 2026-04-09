from rfq_api.seeds import build_seed_rfq
from rfq_api.services.llm import (
    CriterionDraft,
    GeneratedEvidenceCheck,
    GeneratedQuestion,
    GeneratedResponseSchedule,
    GeneratedScheduleColumn,
    GeneratedSection,
    LLMRubricProposal,
    OpenAIResponsesClient,
)
from rfq_api.models import CriterionType


def test_build_rfq_brief_is_readable_text() -> None:
    brief = OpenAIResponsesClient._build_rfq_brief(build_seed_rfq())

    assert brief.startswith("RFQ summary")
    assert '"general_info"' not in brief
    assert "Scope" in brief
    assert "Mandatory conditions" in brief
    assert "Requested line items" in brief
    assert "Strategy & Creative Development" in brief


def test_compose_rubric_backfills_question_and_schedule_links() -> None:
    generated = LLMRubricProposal(
        sections=[
            GeneratedSection(
                id="sec_technical",
                title="Technical",
                description="Technical section.",
            ),
            GeneratedSection(
                id="sec_commercial",
                title="Commercial",
                description="Commercial section.",
            ),
        ],
        criteria=[
            CriterionDraft(
                id="crit_1",
                section_id="sec_technical",
                title="Launch governance",
                description="Governance depth.",
                criterion_type=CriterionType.TECHNICAL_CUTOFF_BACKED,
                weight=60,
                min_cutoff=30,
                max_score=60,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_1",
                        label="Governance evidence",
                        description="Provide governance proof.",
                    )
                ],
            ),
            CriterionDraft(
                id="crit_2",
                section_id="sec_commercial",
                title="Commercial quote",
                description="Commercial readiness.",
                criterion_type=CriterionType.COMMERCIAL,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_2",
                        label="Commercial quote",
                        description="Provide commercial data.",
                    )
                ],
            ),
            CriterionDraft(
                id="crit_3",
                section_id="sec_technical",
                title="Delivery quality",
                description="Delivery quality.",
                criterion_type=CriterionType.TECHNICAL_SCORED_ONLY,
                weight=40,
                max_score=40,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_3",
                        label="Delivery proof",
                        description="Provide delivery evidence.",
                    )
                ],
            ),
            CriterionDraft(
                id="crit_4",
                section_id="sec_technical",
                title="Capability fit",
                description="Capability fit.",
                criterion_type=CriterionType.MAC,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_4",
                        label="Capability proof",
                        description="Provide capability evidence.",
                    )
                ],
            ),
            CriterionDraft(
                id="crit_5",
                section_id="sec_technical",
                title="Program control",
                description="Program control.",
                criterion_type=CriterionType.TECHNICAL_SCORED_ONLY,
                weight=0,
                max_score=0,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_5",
                        label="Control proof",
                        description="Provide control evidence.",
                    )
                ],
            ),
            CriterionDraft(
                id="crit_6",
                section_id="sec_commercial",
                title="Pricing clarity",
                description="Pricing clarity.",
                criterion_type=CriterionType.COMMERCIAL,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_6",
                        label="Pricing proof",
                        description="Provide pricing evidence.",
                    )
                ],
            ),
        ],
        aggregate_technical_threshold=70,
        questions=[
            GeneratedQuestion(
                id="q_1",
                text="Describe governance.",
                purpose="Check governance.",
                linked_criteria=["crit_1", "unknown_criterion"],
            ),
            GeneratedQuestion(
                id="q_2",
                text="Describe delivery quality.",
                purpose="Check delivery.",
                linked_criteria=["crit_3"],
            ),
            GeneratedQuestion(
                id="q_3",
                text="Describe capability fit.",
                purpose="Check capability.",
                linked_criteria=["crit_4"],
            ),
            GeneratedQuestion(
                id="q_4",
                text="Describe program control.",
                purpose="Check control.",
                linked_criteria=["crit_5"],
            ),
            GeneratedQuestion(
                id="q_5",
                text="Describe pricing clarity.",
                purpose="Check pricing.",
                linked_criteria=["crit_6"],
            ),
        ],
        response_schedules=[
            GeneratedResponseSchedule(
                id="pricing_schedule",
                name="Pricing",
                purpose="Capture pricing.",
                linked_criteria=["crit_1", "crit_2"],
                columns=[
                    GeneratedScheduleColumn(
                        id="total_fee",
                        label="Total Fee",
                        description="Total fee value.",
                        required=True,
                    )
                ],
            ),
            GeneratedResponseSchedule(
                id="timeline_schedule",
                name="Timeline",
                purpose="Capture timeline.",
                linked_criteria=["crit_3", "crit_4"],
                columns=[
                    GeneratedScheduleColumn(
                        id="delivery_model",
                        label="Delivery Model",
                        description="Delivery model.",
                        required=True,
                    )
                ],
            ),
        ],
        generation_rationale=[
            "Governance and delivery are core evaluation themes.",
            "Commercial fields are separated for downstream comparison.",
        ],
    )

    proposal = OpenAIResponsesClient._compose_rubric(generated)

    assert proposal.criteria[0].linked_question_ids == ["q_1"]
    assert proposal.criteria[0].linked_schedule_fields == ["pricing_schedule.total_fee"]
    assert proposal.criteria[1].linked_question_ids == []
    assert proposal.criteria[1].linked_schedule_fields == ["pricing_schedule.total_fee"]
    assert proposal.questions[0].linked_criteria == ["crit_1"]
