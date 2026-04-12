from rfq_api.models import OFFICIAL_AWARD_BASIS

from .conftest import build_valid_rubric_proposal


def test_create_and_fetch_session(client) -> None:
    created = client.post("/sessions", json={})
    assert created.status_code == 200
    session_id = created.json()["session_id"]
    assert created.json()["llm_settings"]["reasoning_effort"] == "high"

    fetched = client.get(f"/sessions/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["rfq_draft"]["general_info"]["subject"] == ""
    assert fetched.json()["rfq_draft"]["buyer_priorities"] == []
    assert fetched.json()["rfq_draft"]["mandatory_conditions"] == []
    assert fetched.json()["llm_settings"]["reasoning_effort"] == "high"


def test_get_rfq_templates_returns_blank_and_sample_variants(client) -> None:
    blank = client.get("/rfq-templates/blank")
    assert blank.status_code == 200
    assert blank.json()["general_info"]["subject"] == ""
    assert blank.json()["line_items"] == []

    sample = client.get("/rfq-templates/sample")
    assert sample.status_code == 200
    assert sample.json()["general_info"]["subject"] == "RFQ for global launch marketing services for new kids health drink"
    assert len(sample.json()["line_items"]) == 8


def test_generate_rubric_returns_schema_valid_proposal(client) -> None:
    created = client.post("/sessions", json={})
    session_id = created.json()["session_id"]

    generated = client.post(f"/sessions/{session_id}/rubric/generate")
    assert generated.status_code == 200
    assert generated.json()["rubric_proposal"]["official_award_basis"] == OFFICIAL_AWARD_BASIS


def test_generate_rubric_repairs_invalid_first_draft_before_lock(client) -> None:
    client.fake_llm.return_invalid_rubric_once = True  # type: ignore[attr-defined]
    created = client.post("/sessions", json={})
    session_id = created.json()["session_id"]

    generated = client.post(f"/sessions/{session_id}/rubric/generate")
    assert generated.status_code == 200
    assert client.fake_llm.generate_attempt_count == 2  # type: ignore[attr-defined]
    assert client.fake_llm.last_repair_feedback is not None  # type: ignore[attr-defined]

    locked = client.post(f"/sessions/{session_id}/rubric/lock")
    assert locked.status_code == 200


def test_generate_rubric_returns_best_effort_proposal_when_repair_still_invalid(client) -> None:
    client.fake_llm.return_invalid_rubric_always = True  # type: ignore[attr-defined]
    created = client.post("/sessions", json={})
    session_id = created.json()["session_id"]

    generated = client.post(f"/sessions/{session_id}/rubric/generate")
    assert generated.status_code == 200
    assert generated.json()["rubric_proposal"] is not None
    assert client.fake_llm.generate_attempt_count == 2  # type: ignore[attr-defined]

    locked = client.post(f"/sessions/{session_id}/rubric/lock")
    assert locked.status_code == 200
    assert len(locked.json()["governance"]["rubric_warnings"]) >= 1


def test_update_llm_settings_persists_and_is_used_for_generation(client) -> None:
    created = client.post("/sessions", json={})
    session_id = created.json()["session_id"]

    updated = client.put(f"/sessions/{session_id}/llm-settings", json={"reasoning_effort": "xhigh"})
    assert updated.status_code == 200
    assert updated.json()["llm_settings"]["reasoning_effort"] == "xhigh"

    generated = client.post(f"/sessions/{session_id}/rubric/generate")
    assert generated.status_code == 200
    assert client.fake_llm.last_reasoning_efforts[-1] == "xhigh"  # type: ignore[attr-defined]


def test_patch_rubric_persists_edits(client) -> None:
    created = client.post("/sessions", json={})
    session_id = created.json()["session_id"]
    client.post(f"/sessions/{session_id}/rubric/generate")

    proposal = build_valid_rubric_proposal().model_dump(mode="json")
    proposal["criteria"][1]["title"] = "Updated Governance Criterion"
    patched = client.patch(f"/sessions/{session_id}/rubric", json=proposal)

    assert patched.status_code == 200
    assert patched.json()["rubric_proposal"]["criteria"][1]["title"] == "Updated Governance Criterion"


def test_lock_freezes_artifact_and_prevents_mutation(client) -> None:
    created = client.post("/sessions", json={})
    session_id = created.json()["session_id"]
    client.post(f"/sessions/{session_id}/rubric/generate")

    locked = client.post(f"/sessions/{session_id}/rubric/lock")
    assert locked.status_code == 200
    assert locked.json()["governance"]["official_award_basis"] == OFFICIAL_AWARD_BASIS

    proposal = build_valid_rubric_proposal().model_dump(mode="json")
    mutated = client.patch(f"/sessions/{session_id}/rubric", json=proposal)
    assert mutated.status_code == 409


def test_get_artifact_returns_locked_json(client) -> None:
    created = client.post("/sessions", json={})
    session_id = created.json()["session_id"]
    client.post(f"/sessions/{session_id}/rubric/generate")
    client.post(f"/sessions/{session_id}/rubric/lock")

    artifact = client.get(f"/sessions/{session_id}/artifact")
    assert artifact.status_code == 200
    assert artifact.headers["content-type"].startswith("application/json")
    assert OFFICIAL_AWARD_BASIS in artifact.text
