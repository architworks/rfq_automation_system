from rfq_api.models import OFFICIAL_AWARD_BASIS

from .conftest import build_valid_rubric_proposal


def test_create_and_fetch_session(client) -> None:
    created = client.post("/sessions", json={})
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    fetched = client.get(f"/sessions/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["rfq_draft"]["general_info"]["subject"] == "RFQ for global launch marketing services for new kids health drink"


def test_generate_rubric_returns_schema_valid_proposal(client) -> None:
    created = client.post("/sessions", json={})
    session_id = created.json()["session_id"]

    generated = client.post(f"/sessions/{session_id}/rubric/generate")
    assert generated.status_code == 200
    assert generated.json()["rubric_proposal"]["official_award_basis"] == OFFICIAL_AWARD_BASIS


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
