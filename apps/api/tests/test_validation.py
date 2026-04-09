from rfq_api.models import CriterionType
from rfq_api.services.validation import validate_rubric_proposal

from .conftest import build_valid_rubric_proposal


def test_validator_accepts_valid_rubric() -> None:
    proposal = build_valid_rubric_proposal()
    assert validate_rubric_proposal(proposal) == []


def test_mac_cannot_have_weight() -> None:
    proposal = build_valid_rubric_proposal()
    proposal.criteria[0].weight = 10
    issues = validate_rubric_proposal(proposal)
    assert any(issue.field == "criteria[0].weight" for issue in issues)


def test_cutoff_backed_requires_valid_cutoff_range() -> None:
    proposal = build_valid_rubric_proposal()
    proposal.criteria[1].min_cutoff = 99
    issues = validate_rubric_proposal(proposal)
    assert any(issue.field == "criteria[1].min_cutoff" for issue in issues)


def test_lock_rejects_missing_evidence_mapping() -> None:
    proposal = build_valid_rubric_proposal()
    proposal.criteria[2].evidence_checks = []
    proposal.criteria[2].linked_question_ids = []
    proposal.criteria[2].linked_schedule_fields = []
    issues = validate_rubric_proposal(proposal)
    assert any(issue.field == "criteria[2].evidence" for issue in issues)


def test_technical_weights_must_total_one_hundred() -> None:
    proposal = build_valid_rubric_proposal()
    proposal.criteria[1].weight = 30
    issues = validate_rubric_proposal(proposal)
    assert any(issue.field == "criteria" for issue in issues)


def test_deterministic_scoring_requires_rules() -> None:
    proposal = build_valid_rubric_proposal()
    proposal.criteria[3].deterministic_scoring.rules = []
    issues = validate_rubric_proposal(proposal)
    assert any(issue.field == "criteria[3].deterministic_scoring.rules" for issue in issues)


def test_session_ttl_cleanup_removes_stale_records() -> None:
    from datetime import UTC, datetime, timedelta

    from rfq_api.session_store import SessionStore

    store = SessionStore(ttl_seconds=1)
    record = store.create_or_hydrate()
    record.updated_at = datetime.now(UTC) - timedelta(seconds=5)
    store.cleanup_expired()
    assert store.get(record.session_id) is None
