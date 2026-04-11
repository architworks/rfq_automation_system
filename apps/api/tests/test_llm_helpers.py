from rfq_api.seeds import build_seed_rfq
from rfq_api.services.llm import (
    AIScenarioDraft,
    AIScenarioRankingDraft,
    AIScenarioSet,
    CriterionDraft,
    GeneratedDeterministicScoringGuide,
    GeneratedDeterministicScoringRule,
    GeneratedEvidenceCheck,
    GeneratedEvidenceAnchor,
    GeneratedExtractedField,
    GeneratedQuestion,
    GeneratedResponseSchedule,
    GeneratedScheduleColumn,
    GeneratedSection,
    LLMVendorExtraction,
    LLMRubricProposal,
    NarrativeCriterionScore,
    NarrativeCriterionScoreSet,
    OpenAIResponsesClient,
)
from rfq_api.models import CriterionType, DeterministicScoringType


def test_build_rfq_brief_is_readable_text() -> None:
    brief = OpenAIResponsesClient._build_rfq_brief(build_seed_rfq())

    assert brief.startswith("RFQ summary")
    assert '"general_info"' not in brief
    assert "Scope" in brief
    assert "Mandatory conditions" in brief
    assert "Requested line items" in brief
    assert "Strategy & Creative Development" in brief


def test_compose_rubric_backfills_question_and_schedule_links() -> None:
    long_question_text = (
        "Describe your governance approach across strategy, creative, production, media, compliance, "
        "stakeholder reviews, escalation handling, and launch decision-making, including named owners, "
        "approval forums, and how delivery risks would be surfaced before launch readiness."
    )
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
                criterion_type=CriterionType.MAC,
                weight=10,
                min_cutoff=5,
                max_score=10,
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
                deterministic_scoring=GeneratedDeterministicScoringGuide(
                    guide_type=DeterministicScoringType.PASS_FAIL,
                    answer_format="Yes/No confirmation",
                    summary="Pricing completeness can be checked directly.",
                    rules=[
                        GeneratedDeterministicScoringRule(
                            id="rule_pass",
                            condition="All applicable line items are quoted clearly.",
                            outcome="pass",
                        ),
                        GeneratedDeterministicScoringRule(
                            id="rule_fail",
                            condition="Any applicable line item is missing or unclear.",
                            outcome="fail",
                        ),
                    ],
                ),
            ),
        ],
        aggregate_technical_threshold=70,
        questions=[
            GeneratedQuestion(
                id="q_1",
                text=long_question_text,
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
    assert proposal.criteria[1].criterion_type == CriterionType.COMMERCIAL
    assert proposal.criteria[1].weight is None
    assert proposal.criteria[1].min_cutoff is None
    assert proposal.criteria[1].max_score is None
    assert proposal.criteria[5].deterministic_scoring is not None
    assert proposal.criteria[5].deterministic_scoring.rules[0].outcome == "pass"
    assert proposal.questions[0].text == long_question_text
    assert proposal.questions[0].linked_criteria == ["crit_1"]


def test_structured_rubric_schema_accepts_long_free_text_fields() -> None:
    long_text = (
        "This is intentionally long free text for structured outputs. "
        "It should remain valid even when the model returns a detailed explanation, "
        "vendor-facing question, or evidence check that is substantially longer than the earlier caps. "
    ) * 6

    proposal = LLMRubricProposal(
        sections=[
            GeneratedSection(
                id="sec_technical",
                title="Technical evaluation section with a much longer title than before to avoid truncation.",
                description=long_text,
            ),
            GeneratedSection(
                id="sec_commercial",
                title="Commercial evaluation section with a much longer title than before to avoid truncation.",
                description=long_text,
            ),
        ],
        criteria=[
            CriterionDraft(
                id="crit_1",
                section_id="sec_technical",
                title="Criterion title that remains readable even when it is fairly long and specific to the RFQ.",
                description=long_text,
                criterion_type=CriterionType.MAC,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_1",
                        label="Evidence check label that should no longer be constrained by short title limits.",
                        description=long_text,
                    )
                ],
            ),
            CriterionDraft(
                id="crit_2",
                section_id="sec_technical",
                title="Critical technical scored criterion title that may require more detail than a short cap allows.",
                description=long_text,
                criterion_type=CriterionType.TECHNICAL_CUTOFF_BACKED,
                weight=60,
                min_cutoff=42,
                max_score=60,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_2",
                        label="Long evidence check label for technical scoring.",
                        description=long_text,
                    )
                ],
            ),
            CriterionDraft(
                id="crit_3",
                section_id="sec_technical",
                title="Narrative technical criterion title.",
                description=long_text,
                criterion_type=CriterionType.TECHNICAL_SCORED_ONLY,
                weight=40,
                max_score=40,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_3",
                        label="Narrative evidence check label.",
                        description=long_text,
                    )
                ],
            ),
            CriterionDraft(
                id="crit_4",
                section_id="sec_commercial",
                title="Commercial criterion title.",
                description=long_text,
                criterion_type=CriterionType.COMMERCIAL,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_4",
                        label="Commercial evidence check label.",
                        description=long_text,
                    )
                ],
            ),
            CriterionDraft(
                id="crit_5",
                section_id="sec_technical",
                title="Additional MAC criterion title.",
                description=long_text,
                criterion_type=CriterionType.MAC,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_5",
                        label="Additional evidence check label.",
                        description=long_text,
                    )
                ],
            ),
            CriterionDraft(
                id="crit_6",
                section_id="sec_commercial",
                title="Additional commercial criterion title.",
                description=long_text,
                criterion_type=CriterionType.COMMERCIAL,
                evidence_checks=[
                    GeneratedEvidenceCheck(
                        id="ev_6",
                        label="Additional commercial evidence check label.",
                        description=long_text,
                    )
                ],
            ),
        ],
        aggregate_technical_threshold=70,
        questions=[
            GeneratedQuestion(id="q_1", text=long_text, purpose=long_text, linked_criteria=["crit_1"]),
            GeneratedQuestion(id="q_2", text=long_text, purpose=long_text, linked_criteria=["crit_2"]),
            GeneratedQuestion(id="q_3", text=long_text, purpose=long_text, linked_criteria=["crit_3"]),
            GeneratedQuestion(id="q_4", text=long_text, purpose=long_text, linked_criteria=["crit_4"]),
            GeneratedQuestion(id="q_5", text=long_text, purpose=long_text, linked_criteria=["crit_5"]),
        ],
        response_schedules=[
            GeneratedResponseSchedule(
                id="schedule_1",
                name="Long schedule name for technical inputs that should not be clipped.",
                purpose=long_text,
                linked_criteria=["crit_2", "crit_3"],
                columns=[
                    GeneratedScheduleColumn(
                        id="col_1",
                        label="Long schedule column label that should remain intact.",
                        description=long_text,
                        required=True,
                    )
                ],
            ),
            GeneratedResponseSchedule(
                id="schedule_2",
                name="Long commercial schedule name that should not be clipped.",
                purpose=long_text,
                linked_criteria=["crit_4"],
                columns=[
                    GeneratedScheduleColumn(
                        id="col_2",
                        label="Long commercial column label.",
                        description=long_text,
                        required=True,
                    )
                ],
            ),
        ],
        generation_rationale=[long_text, long_text],
    )

    assert proposal.criteria[0].description == long_text
    assert proposal.questions[0].text == long_text
    assert proposal.response_schedules[0].columns[0].description == long_text
    assert proposal.generation_rationale[0] == long_text


def test_other_structured_output_schemas_accept_long_free_text_fields() -> None:
    long_text = (
        "This is intentionally long free text for extraction, scoring, and scenario generation. "
        "It should remain valid even when the model returns detailed evidence, explanations, or scenario notes. "
    ) * 8

    extraction = LLMVendorExtraction(
        document_summary=long_text,
        question_answers=[
            GeneratedExtractedField(
                id="field_1",
                label="Detailed extracted field label that should not be clipped.",
                question_id="q_1",
                criterion_ids=["crit_1"],
                state="answered",
                raw_value=long_text,
                normalized_hint=long_text,
                notes=long_text,
                evidence=[
                    GeneratedEvidenceAnchor(
                        id="ev_1",
                        snippet=long_text,
                        locator=long_text,
                        source_label="Detailed source label that should not be clipped.",
                    )
                ],
            )
        ],
        warnings=[long_text],
    )
    scores = NarrativeCriterionScoreSet(
        scores=[
            NarrativeCriterionScore(
                criterion_id="crit_1",
                score=88,
                confidence=0.72,
                explanation=long_text,
                evidence_refs=["ev_1"],
                risks=[long_text],
            )
        ]
    )
    scenarios = AIScenarioSet(
        scenarios=[
            AIScenarioDraft(
                scenario_name="Scenario one name that should remain fully readable.",
                winner_vendor_id="vendor_1",
                weighting_or_rule_basis=long_text,
                explanation=long_text,
                evidence_refs=["ev_1"],
                ranking=[AIScenarioRankingDraft(vendor_id="vendor_1", score=95, notes=[long_text])],
            ),
            AIScenarioDraft(
                scenario_name="Scenario two name that should remain fully readable.",
                winner_vendor_id="vendor_1",
                weighting_or_rule_basis=long_text,
                explanation=long_text,
                evidence_refs=["ev_1"],
                ranking=[AIScenarioRankingDraft(vendor_id="vendor_1", score=94, notes=[long_text])],
            ),
            AIScenarioDraft(
                scenario_name="Scenario three name that should remain fully readable.",
                winner_vendor_id="vendor_1",
                weighting_or_rule_basis=long_text,
                explanation=long_text,
                evidence_refs=["ev_1"],
                ranking=[AIScenarioRankingDraft(vendor_id="vendor_1", score=93, notes=[long_text])],
            ),
        ]
    )

    assert extraction.document_summary == long_text
    assert extraction.question_answers[0].evidence[0].snippet == long_text
    assert scores.scores[0].explanation == long_text
    assert scenarios.scenarios[0].weighting_or_rule_basis == long_text
