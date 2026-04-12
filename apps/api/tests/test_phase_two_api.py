from __future__ import annotations

import pytest

def test_vendor_pack_is_derived_from_locked_artifact(client) -> None:
    session_id = _lock_session(client)

    response = client.get(f"/sessions/{session_id}/vendor-pack")

    assert response.status_code == 200
    payload = response.json()
    assert payload["rfq_title"] == "RFQ for global launch marketing services for new kids health drink"
    assert payload["official_award_basis"] == "QCBS 70/30"
    assert payload["questions"][0]["id"] == "q1"
    assert payload["response_schedules"][0]["columns"][0]["field_id"].startswith("pricing_schedule.")


def test_upload_replace_and_review_flow(client) -> None:
    session_id = _lock_session(client)
    snapshot = client.post(f"/sessions/{session_id}/vendors", json={"name": "Alpha"})
    vendor_id = snapshot.json()["vendors"][0]["id"]

    first_upload = client.put(
        f"/sessions/{session_id}/vendors/{vendor_id}/document",
        files={"file": ("alpha.docx", b"alpha document", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert first_upload.status_code == 200
    assert first_upload.json()["vendors"][0]["document"]["file_name"] == "alpha.docx"

    second_upload = client.put(
        f"/sessions/{session_id}/vendors/{vendor_id}/document",
        files={"file": ("alpha_v2.pdf", b"%PDF-1.4 replacement", "application/pdf")},
    )
    assert second_upload.status_code == 200
    assert second_upload.json()["vendors"][0]["document"]["file_name"] == "alpha_v2.pdf"
    assert second_upload.json()["vendors"][0]["warnings"] == []

    extracted = client.post(f"/sessions/{session_id}/vendors/{vendor_id}/extract")
    assert extracted.status_code == 200
    assert extracted.json()["vendors"][0]["status"] == "evaluation_ready"

    review = client.get(f"/sessions/{session_id}/vendors/{vendor_id}/review")
    assert review.status_code == 200
    payload = review.json()
    assert payload["raw_extraction"]["document_summary"] == "Extracted proposal summary for Alpha."
    assert len(payload["raw_extraction"]["schedule_answers"]) == 8
    assert payload["raw_extraction"]["commercial_claims"] == []
    assert payload["normalized_pricing"][0]["comparability_status"] == "comparable"


def test_bulk_extract_runs_for_all_uploaded_vendors(client) -> None:
    session_id = _lock_session(client)
    alpha = client.post(f"/sessions/{session_id}/vendors", json={"name": "Alpha"})
    beta = client.post(f"/sessions/{session_id}/vendors", json={"name": "Beta"})
    gamma = client.post(f"/sessions/{session_id}/vendors", json={"name": "Gamma"})
    alpha_id = alpha.json()["vendors"][0]["id"]
    beta_id = beta.json()["vendors"][-1]["id"]
    gamma_id = gamma.json()["vendors"][-1]["id"]

    uploaded_alpha = client.put(
        f"/sessions/{session_id}/vendors/{alpha_id}/document",
        files={"file": ("alpha.pdf", b"%PDF-1.4 alpha", "application/pdf")},
    )
    assert uploaded_alpha.status_code == 200
    uploaded_beta = client.put(
        f"/sessions/{session_id}/vendors/{beta_id}/document",
        files={"file": ("beta.docx", b"beta document", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert uploaded_beta.status_code == 200

    extracted = client.post(f"/sessions/{session_id}/vendors/extract")
    assert extracted.status_code == 200
    payload = extracted.json()
    vendors_by_id = {vendor["id"]: vendor for vendor in payload["vendors"]}
    assert vendors_by_id[alpha_id]["status"] == "evaluation_ready"
    assert vendors_by_id[beta_id]["status"] == "evaluation_ready"
    assert vendors_by_id[gamma_id]["status"] == "no_document"

    alpha_review = client.get(f"/sessions/{session_id}/vendors/{alpha_id}/review")
    beta_review = client.get(f"/sessions/{session_id}/vendors/{beta_id}/review")
    assert alpha_review.status_code == 200
    assert beta_review.status_code == 200


def test_locked_session_applies_automatic_fx_normalization(client) -> None:
    session_id = _lock_session(client)
    vendor_id = _add_and_extract_vendor(client, session_id, "Euro", "euro.pdf")

    session = client.get(f"/sessions/{session_id}")
    assert session.status_code == 200
    assert session.json()["comparison_settings"]["base_currency"] == "USD"

    review = client.get(f"/sessions/{session_id}/vendors/{vendor_id}/review")
    assert review.status_code == 200
    first_line = review.json()["normalized_pricing"][0]
    assert first_line["comparability_status"] == "comparable"
    assert first_line["base_currency_total"] == pytest.approx(111.2545)


def test_evaluation_run_excludes_disqualified_and_non_comparable_vendors(client) -> None:
    session_id = _lock_session(client)
    alpha_id = _add_and_extract_vendor(client, session_id, "Alpha", "alpha.pdf")
    beta_id = _add_and_extract_vendor(client, session_id, "Beta", "beta.pdf")
    gamma_id = _add_and_extract_vendor(client, session_id, "Gamma", "gamma.pdf")
    delta_id = _add_and_extract_vendor(client, session_id, "Delta", "delta.pdf")

    evaluation = client.post(f"/sessions/{session_id}/evaluation/run")
    assert evaluation.status_code == 200
    payload = evaluation.json()

    assert payload["official_recommendation"]["winner_vendor_id"] == alpha_id
    assert payload["official_recommendation"]["eligible_vendor_ids"] == [alpha_id, beta_id]

    commercial_by_vendor = {
        item["vendor_id"]: item
        for item in payload["commercial_results"]
    }
    technical_by_vendor = {
        item["vendor_id"]: item
        for item in payload["technical_results"]
    }

    assert commercial_by_vendor[alpha_id]["commercial_score"] == 100.0
    assert commercial_by_vendor[beta_id]["commercial_score"] == 90.91
    assert commercial_by_vendor[delta_id]["award_ready"] is False
    assert "Missing FX rate for AED in the stored FX snapshot." in commercial_by_vendor[delta_id]["blockers"]
    assert technical_by_vendor[gamma_id]["passed_gate"] is False
    assert any("Failed technical cutoff" in reason for reason in technical_by_vendor[gamma_id]["disqualification_reasons"])

    advisory_winners = {item["winner_vendor_id"] for item in payload["advisory_scenarios"]}
    assert gamma_id not in advisory_winners
    assert delta_id not in advisory_winners

    results = client.get(f"/sessions/{session_id}/results")
    assert results.status_code == 200
    assert results.json()["official_recommendation"]["winner_vendor_id"] == alpha_id


def _lock_session(client) -> str:
    created = client.post("/sessions", json={})
    session_id = created.json()["session_id"]
    sample_rfq = client.get("/rfq-templates/sample")
    assert sample_rfq.status_code == 200
    saved_rfq = client.put(f"/sessions/{session_id}/rfq", json=sample_rfq.json())
    assert saved_rfq.status_code == 200
    client.post(f"/sessions/{session_id}/rubric/generate")
    client.post(f"/sessions/{session_id}/rubric/lock")
    return session_id


def _add_and_extract_vendor(client, session_id: str, vendor_name: str, file_name: str) -> str:
    created_vendor = client.post(f"/sessions/{session_id}/vendors", json={"name": vendor_name})
    assert created_vendor.status_code == 201
    vendor_id = created_vendor.json()["vendors"][-1]["id"]

    uploaded = client.put(
        f"/sessions/{session_id}/vendors/{vendor_id}/document",
        files={"file": (file_name, b"%PDF-1.4 vendor document", "application/pdf")},
    )
    assert uploaded.status_code == 200

    extracted = client.post(f"/sessions/{session_id}/vendors/{vendor_id}/extract")
    assert extracted.status_code == 200
    return vendor_id
