from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .models import (
    ComparisonSettings,
    CreateSessionRequest,
    CreateVendorRequest,
    DownloadMetadata,
    EvaluationReport,
    GovernanceInfo,
    LockedFrameworkArtifact,
    OFFICIAL_AWARD_BASIS,
    RFQDraft,
    RubricProposal,
    SessionSnapshot,
    SessionStatus,
    UpdateLLMSettingsRequest,
    UpdateVendorRequest,
    VendorDocument,
    VendorPack,
    VendorReview,
    VendorStatus,
)
from .services.documents import build_visual_fidelity_warnings, validate_document_name
from .services.evaluation import EvaluationContext, run_evaluation
from .services.llm import (
    LLMClient,
    LLMConfigurationError,
    LLMTaskError,
    OpenAIResponsesClient,
    RubricGenerationError,
)
from .services.review import build_vendor_review
from .services.rubric_generation import RubricGenerationService, normalize_rubric_proposal
from .services.validation import validate_rubric_proposal
from .services.vendor_pack import build_vendor_pack
from .seeds import build_blank_rfq, build_sample_rfq
from .session_store import SessionStore


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.2.0")
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

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "status": "ok",
        }

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
        }

    @app.get("/rfq-templates/{template_name}", response_model=RFQDraft)
    def get_rfq_template(template_name: Literal["blank", "sample"]) -> RFQDraft:
        if template_name == "blank":
            return build_blank_rfq()
        return build_sample_rfq()

    @app.post("/sessions", response_model=SessionSnapshot)
    def create_session(
        payload: CreateSessionRequest | None = None,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        session_id = payload.session_id if payload else None
        record = store.create_or_hydrate(session_id)
        record = _ensure_vendor_pack(record.session_id, record, store)
        return record.snapshot()

    @app.get("/sessions/{session_id}", response_model=SessionSnapshot)
    def get_session(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        record = _get_record_or_404(session_id, store)
        return record.snapshot()

    @app.put("/sessions/{session_id}/llm-settings", response_model=SessionSnapshot)
    def save_llm_settings(
        session_id: str,
        payload: UpdateLLMSettingsRequest,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        record = _get_record_or_404(session_id, store)
        saved = store.save_llm_settings(
            session_id,
            record.llm_settings.model_copy(update={"reasoning_effort": payload.reasoning_effort}),
        )
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return saved.snapshot()

    @app.put("/sessions/{session_id}/rfq", response_model=SessionSnapshot)
    def save_rfq(
        session_id: str,
        rfq_draft: RFQDraft,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        record = _get_record_or_404(session_id, store)
        if record.status == SessionStatus.LOCKED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Locked sessions cannot be modified.")
        saved = store.save_rfq(session_id, rfq_draft)
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return saved.snapshot()

    @app.post("/sessions/{session_id}/rubric/generate", response_model=SessionSnapshot)
    def generate_rubric(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
        generation_service: RubricGenerationService = Depends(get_rubric_generation_service),
    ) -> SessionSnapshot:
        record = _get_record_or_404(session_id, store)
        if record.status == SessionStatus.LOCKED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Locked sessions cannot be modified.")

        try:
            proposal = generation_service.generate(record.rfq_draft, record.llm_settings)
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except RubricGenerationError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        saved = store.save_rubric(session_id, proposal)
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return saved.snapshot()

    @app.patch("/sessions/{session_id}/rubric", response_model=SessionSnapshot)
    def save_rubric(
        session_id: str,
        rubric_proposal: RubricProposal,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        record = _get_record_or_404(session_id, store)
        if record.status == SessionStatus.LOCKED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Locked sessions cannot be modified.")
        saved = store.save_rubric(session_id, rubric_proposal)
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return saved.snapshot()

    @app.post("/sessions/{session_id}/rubric/lock", response_model=LockedFrameworkArtifact)
    def lock_rubric(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
    ) -> LockedFrameworkArtifact:
        record = _get_record_or_404(session_id, store)
        if record.rubric_proposal is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No rubric proposal exists for this session.")
        if record.status == SessionStatus.LOCKED and record.locked_artifact is not None:
            _ensure_vendor_pack(session_id, record, store)
            return record.locked_artifact

        normalized_proposal = normalize_rubric_proposal(record.rubric_proposal)
        issues = validate_rubric_proposal(normalized_proposal)

        artifact = LockedFrameworkArtifact(
            locked_at=datetime.now(UTC),
            rfq_snapshot=record.rfq_draft,
            rubric_snapshot=normalized_proposal,
            governance=GovernanceInfo(
                official_award_basis=OFFICIAL_AWARD_BASIS,
                technical_threshold_strategy="RFQ-specific threshold proposed by AI and approved by buyer before lock.",
                advisory_outputs=["LCS", "QBS", "RFQ-specific AI scenarios"],
                persistence_scope="Browser session plus in-memory backend session state with TTL-managed temp files.",
                rubric_warnings=issues,
            ),
            download_metadata=DownloadMetadata(
                file_name=f"locked-framework-{session_id}.json",
            ),
        )
        vendor_pack = build_vendor_pack(artifact)
        saved = store.lock_artifact(session_id, artifact, vendor_pack)
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return artifact

    @app.get("/sessions/{session_id}/artifact")
    def get_artifact(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
    ) -> Response:
        record = _get_record_or_404(session_id, store)
        if record.locked_artifact is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locked artifact not found for this session.")

        payload = json.dumps(record.locked_artifact.model_dump(mode="json"), indent=2)
        headers = {
            "Content-Disposition": f'attachment; filename="{record.locked_artifact.download_metadata.file_name}"'
        }
        return Response(content=payload, media_type="application/json", headers=headers)

    @app.get("/sessions/{session_id}/vendor-pack", response_model=VendorPack)
    def get_vendor_pack(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
    ) -> VendorPack:
        record = _get_locked_record_or_409(session_id, store)
        if record.vendor_pack is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor pack not found for this session.")
        return record.vendor_pack

    @app.get("/sessions/{session_id}/vendor-pack/export")
    def export_vendor_pack(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
    ) -> Response:
        record = _get_locked_record_or_409(session_id, store)
        if record.vendor_pack is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor pack not found for this session.")
        payload = json.dumps(record.vendor_pack.model_dump(mode="json"), indent=2)
        headers = {
            "Content-Disposition": f'attachment; filename="vendor-pack-{session_id}.json"'
        }
        return Response(content=payload, media_type="application/json", headers=headers)

    @app.post(
        "/sessions/{session_id}/vendors",
        response_model=SessionSnapshot,
        status_code=status.HTTP_201_CREATED,
    )
    def create_vendor(
        session_id: str,
        payload: CreateVendorRequest,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        _get_locked_record_or_409(session_id, store)
        saved = store.add_vendor(session_id, payload.name.strip())
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return saved.snapshot()

    @app.patch("/sessions/{session_id}/vendors/{vendor_id}", response_model=SessionSnapshot)
    def update_vendor(
        session_id: str,
        vendor_id: str,
        payload: UpdateVendorRequest,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        _require_vendor(session_id, vendor_id, store)
        saved = store.rename_vendor(session_id, vendor_id, payload.name.strip())
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")
        return saved.snapshot()

    @app.delete("/sessions/{session_id}/vendors/{vendor_id}", response_model=SessionSnapshot)
    def delete_vendor(
        session_id: str,
        vendor_id: str,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        _require_vendor(session_id, vendor_id, store)
        saved = store.delete_vendor(session_id, vendor_id)
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")
        return saved.snapshot()

    @app.put("/sessions/{session_id}/vendors/{vendor_id}/document", response_model=SessionSnapshot)
    async def upload_vendor_document(
        session_id: str,
        vendor_id: str,
        file: UploadFile = File(...),
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        _require_vendor(session_id, vendor_id, store)
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must have a filename.")

        extension, mime_type = validate_document_name(file.filename)
        content = await file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

        document = VendorDocument(
            file_name=file.filename,
            mime_type=mime_type,
            extension=extension,
            size_bytes=len(content),
            uploaded_at=datetime.now(UTC),
            warnings=build_visual_fidelity_warnings(extension),
        )
        saved = store.save_vendor_document(session_id, vendor_id, document, content)
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")
        return saved.snapshot()

    @app.post("/sessions/{session_id}/vendors/{vendor_id}/extract", response_model=SessionSnapshot)
    def extract_vendor_document(
        session_id: str,
        vendor_id: str,
        store: SessionStore = Depends(get_session_store),
        llm_client: LLMClient = Depends(get_llm_client),
    ) -> SessionSnapshot:
        try:
            review = _extract_vendor_review(
                session_id=session_id,
                vendor_id=vendor_id,
                store=store,
                llm_client=llm_client,
            )
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except LLMTaskError as exc:
            store.set_vendor_extraction_error(session_id, vendor_id, str(exc))
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        saved = store.save_vendor_review(session_id, review)
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")
        return saved.snapshot()

    @app.post("/sessions/{session_id}/vendors/extract", response_model=SessionSnapshot)
    def extract_uploaded_vendor_documents(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
        llm_client: LLMClient = Depends(get_llm_client),
    ) -> SessionSnapshot:
        record = _get_locked_record_or_409(session_id, store)
        vendor_ids = [
            vendor.id
            for vendor in record.vendors
            if vendor.document is not None and vendor.status == VendorStatus.UPLOADED
        ]
        if not vendor_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No uploaded vendor documents are waiting for extraction.",
            )

        for vendor_id in vendor_ids:
            try:
                review = _extract_vendor_review(
                    session_id=session_id,
                    vendor_id=vendor_id,
                    store=store,
                    llm_client=llm_client,
                )
            except LLMConfigurationError as exc:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
            except LLMTaskError as exc:
                store.set_vendor_extraction_error(session_id, vendor_id, str(exc))
                continue

            saved = store.save_vendor_review(session_id, review)
            if saved is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")

        refreshed = _get_record_or_404(session_id, store)
        return refreshed.snapshot()

    @app.get("/sessions/{session_id}/vendors/{vendor_id}/review", response_model=VendorReview)
    def get_vendor_review(
        session_id: str,
        vendor_id: str,
        store: SessionStore = Depends(get_session_store),
    ) -> VendorReview:
        _require_vendor(session_id, vendor_id, store)
        review = store.get_vendor_review(session_id, vendor_id)
        if review is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor review not found.")
        return review

    @app.put("/sessions/{session_id}/comparison-settings", response_model=SessionSnapshot)
    def save_comparison_settings(
        session_id: str,
        comparison_settings: ComparisonSettings,
        store: SessionStore = Depends(get_session_store),
    ) -> SessionSnapshot:
        record = _get_locked_record_or_409(session_id, store)
        saved = store.save_comparison_settings(session_id, comparison_settings)
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        current = _get_locked_record_or_409(session_id, store)
        for review in list(current.vendor_reviews.values()):
            refreshed_review = build_vendor_review(
                vendor_id=review.vendor_id,
                document=review.document,
                raw_extraction=review.raw_extraction,
                artifact=current.locked_artifact,
                comparison_settings=comparison_settings,
                created_at=review.created_at,
            )
            store.save_vendor_review(session_id, refreshed_review)

        refreshed_record = _get_locked_record_or_409(session_id, store)
        return refreshed_record.snapshot()

    @app.post("/sessions/{session_id}/evaluation/run", response_model=EvaluationReport)
    def run_session_evaluation(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
        llm_client: LLMClient = Depends(get_llm_client),
    ) -> EvaluationReport:
        record = _get_locked_record_or_409(session_id, store)
        if record.comparison_settings is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Comparison settings must be provided before running the official evaluation.",
            )

        try:
            report = run_evaluation(
                EvaluationContext(
                    artifact=record.locked_artifact,
                    comparison_settings=record.comparison_settings,
                    vendors=record.vendors,
                    reviews_by_vendor=dict(record.vendor_reviews),
                    llm_settings=record.llm_settings,
                ),
                llm_client,
            )
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except LLMTaskError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        saved = store.save_evaluation_report(session_id, report)
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return report

    @app.get("/sessions/{session_id}/results", response_model=EvaluationReport)
    def get_results(
        session_id: str,
        store: SessionStore = Depends(get_session_store),
    ) -> EvaluationReport:
        record = _get_locked_record_or_409(session_id, store)
        if record.evaluation_report is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation results are not available yet.")
        return record.evaluation_report

    return app


def _get_record_or_404(session_id: str, store: SessionStore):
    record = store.get(session_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return _ensure_vendor_pack(session_id, record, store)


def _get_locked_record_or_409(session_id: str, store: SessionStore):
    record = _get_record_or_404(session_id, store)
    if record.locked_artifact is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lock the framework before entering this step.")
    return record


def _require_vendor(session_id: str, vendor_id: str, store: SessionStore):
    record = _get_locked_record_or_409(session_id, store)
    vendor = next((item for item in record.vendors if item.id == vendor_id), None)
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")
    return record


def _extract_vendor_review(
    *,
    session_id: str,
    vendor_id: str,
    store: SessionStore,
    llm_client: LLMClient,
) -> VendorReview:
    record = _require_vendor(session_id, vendor_id, store)
    vendor = next(vendor for vendor in record.vendors if vendor.id == vendor_id)
    if vendor.document is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vendor document has not been uploaded yet.")
    if record.locked_artifact is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lock the framework before extracting vendor responses.")

    document_path = store.get_vendor_document_path(session_id, vendor_id)
    if document_path is None or not document_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored vendor document could not be found.")
    document_bytes = document_path.read_bytes()

    raw_extraction = llm_client.extract_vendor_response(
        artifact=record.locked_artifact,
        vendor=vendor,
        document=vendor.document,
        document_bytes=document_bytes,
        llm_settings=record.llm_settings,
    )
    return build_vendor_review(
        vendor_id=vendor_id,
        document=vendor.document,
        raw_extraction=raw_extraction,
        artifact=record.locked_artifact,
        comparison_settings=record.comparison_settings,
    )


def _ensure_vendor_pack(session_id: str, record, store: SessionStore):
    if record.locked_artifact is None or record.vendor_pack is not None:
        return record
    vendor_pack = build_vendor_pack(record.locked_artifact)
    saved = store.lock_artifact(session_id, record.locked_artifact, vendor_pack)
    return saved or record


@lru_cache(maxsize=1)
def get_session_store() -> SessionStore:
    settings = get_settings()
    return SessionStore(ttl_seconds=settings.session_ttl_seconds, storage_root=settings.storage_root)


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
