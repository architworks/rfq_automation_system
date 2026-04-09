from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .models import (
    CreateSessionRequest,
    DownloadMetadata,
    GovernanceInfo,
    LockedFrameworkArtifact,
    OFFICIAL_AWARD_BASIS,
    RFQDraft,
    RubricProposal,
    SessionSnapshot,
    SessionStatus,
)
from .services.llm import LLMClient, LLMConfigurationError, OpenAIResponsesClient, RubricGenerationError
from .services.rubric_generation import RubricGenerationService
from .services.validation import validate_rubric_proposal
from .session_store import SessionStore


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    local_origins = {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        settings.frontend_origin,
    }
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(local_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/sessions", response_model=SessionSnapshot)
    def create_session(
        payload: CreateSessionRequest | None = None,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        session_id = payload.session_id if payload else None
        return store.create_or_hydrate(session_id).snapshot()

    @app.get("/sessions/{session_id}", response_model=SessionSnapshot)
    def get_session(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        record = store.get(session_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return record.snapshot()

    @app.put("/sessions/{session_id}/rfq", response_model=SessionSnapshot)
    def save_rfq(
        session_id: str,
        rfq_draft: RFQDraft,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        record = store.get(session_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        if record.status == SessionStatus.LOCKED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Locked sessions cannot be modified.")
        saved = store.save_rfq(session_id, rfq_draft)
        return saved.snapshot()

    @app.post("/sessions/{session_id}/rubric/generate", response_model=SessionSnapshot)
    def generate_rubric(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
        generation_service: RubricGenerationService = Depends(get_rubric_generation_service),
    ) -> SessionSnapshot:
        record = store.get(session_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        if record.status == SessionStatus.LOCKED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Locked sessions cannot be modified.")

        try:
            proposal = generation_service.generate(record.rfq_draft)
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except RubricGenerationError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        saved = store.save_rubric(session_id, proposal)
        return saved.snapshot()

    @app.patch("/sessions/{session_id}/rubric", response_model=SessionSnapshot)
    def save_rubric(
        session_id: str,
        rubric_proposal: RubricProposal,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        record = store.get(session_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        if record.status == SessionStatus.LOCKED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Locked sessions cannot be modified.")
        saved = store.save_rubric(session_id, rubric_proposal)
        return saved.snapshot()

    @app.post("/sessions/{session_id}/rubric/lock", response_model=LockedFrameworkArtifact)
    def lock_rubric(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
    ) -> LockedFrameworkArtifact:
        record = store.get(session_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        if record.rubric_proposal is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No rubric proposal exists for this session.")
        if record.status == SessionStatus.LOCKED and record.locked_artifact is not None:
            return record.locked_artifact

        issues = validate_rubric_proposal(record.rubric_proposal)
        if issues:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[issue.model_dump() for issue in issues],
            )

        artifact = LockedFrameworkArtifact(
            locked_at=datetime.now(UTC),
            rfq_snapshot=record.rfq_draft,
            rubric_snapshot=record.rubric_proposal,
            governance=GovernanceInfo(
                official_award_basis=OFFICIAL_AWARD_BASIS,
                technical_threshold_strategy="RFQ-specific threshold proposed by AI and approved by buyer before lock.",
                advisory_outputs=["LCS", "QBS", "RFQ-specific AI scenarios"],
                persistence_scope="Browser session plus in-memory backend session state with TTL.",
            ),
            download_metadata=DownloadMetadata(
                file_name=f"locked-framework-{session_id}.json",
            ),
        )
        store.lock_artifact(session_id, artifact)
        return artifact

    @app.get("/sessions/{session_id}/artifact")
    def get_artifact(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
    ) -> Response:
        record = store.get(session_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        if record.locked_artifact is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locked artifact not found for this session.")

        payload = json.dumps(record.locked_artifact.model_dump(mode="json"), indent=2)
        headers = {
            "Content-Disposition": f'attachment; filename="{record.locked_artifact.download_metadata.file_name}"'
        }
        return Response(content=payload, media_type="application/json", headers=headers)

    return app


@lru_cache(maxsize=1)
def get_session_store() -> SessionStore:
    settings = get_settings()
    return SessionStore(ttl_seconds=settings.session_ttl_seconds)


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:
    try:
        return OpenAIResponsesClient(settings)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


def get_rubric_generation_service(
    llm_client: LLMClient = Depends(get_llm_client),
) -> RubricGenerationService:
    return RubricGenerationService(llm_client)


app = create_app()


def run() -> None:
    uvicorn.run("rfq_api.main:app", host="0.0.0.0", port=8000, reload=True)
