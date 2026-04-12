from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from uuid import uuid4
import shutil
import tempfile

from .models import (
    ComparisonSettings,
    EvaluationReport,
    LLMSettings,
    LockedFrameworkArtifact,
    RFQDraft,
    RubricProposal,
    SessionSnapshot,
    SessionStatus,
    VendorDocument,
    VendorPack,
    VendorRecord,
    VendorReview,
    VendorStatus,
)
from .seeds import build_blank_rfq


@dataclass
class SessionRecord:
    session_id: str
    status: SessionStatus
    llm_settings: LLMSettings
    rfq_draft: RFQDraft
    rubric_proposal: RubricProposal | None
    locked_artifact: LockedFrameworkArtifact | None
    vendor_pack: VendorPack | None
    vendors: list[VendorRecord]
    comparison_settings: ComparisonSettings | None
    evaluation_report: EvaluationReport | None
    updated_at: datetime
    vendor_reviews: dict[str, VendorReview] = field(default_factory=dict)
    document_paths: dict[str, Path] = field(default_factory=dict)

    def snapshot(self) -> SessionSnapshot:
        ordered_reviews = [
            self.vendor_reviews[vendor.id]
            for vendor in self.vendors
            if vendor.id in self.vendor_reviews
        ]
        return SessionSnapshot(
            session_id=self.session_id,
            status=self.status,
            llm_settings=self.llm_settings,
            rfq_draft=self.rfq_draft,
            rubric_proposal=self.rubric_proposal,
            locked_artifact=self.locked_artifact,
            vendor_pack=self.vendor_pack,
            vendors=self.vendors,
            comparison_settings=self.comparison_settings,
            vendor_reviews=ordered_reviews,
            evaluation_report=self.evaluation_report,
            updated_at=self.updated_at,
        )


class SessionStore:
    def __init__(self, ttl_seconds: int, storage_root: str | None = None) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        base_root = Path(storage_root) if storage_root else Path(tempfile.gettempdir()) / "rfq_api_sessions"
        self._storage_root = base_root
        self._storage_root.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, SessionRecord] = {}
        self._lock = Lock()

    def create_or_hydrate(self, session_id: str | None = None) -> SessionRecord:
        with self._lock:
            self.cleanup_expired()
            if session_id and session_id in self._records:
                record = self._records[session_id]
                record.updated_at = datetime.now(UTC)
                return record

            new_id = session_id or str(uuid4())
            record = SessionRecord(
                session_id=new_id,
                status=SessionStatus.DRAFT,
                llm_settings=LLMSettings(),
                rfq_draft=build_blank_rfq(),
                rubric_proposal=None,
                locked_artifact=None,
                vendor_pack=None,
                vendors=[],
                comparison_settings=None,
                evaluation_report=None,
                updated_at=datetime.now(UTC),
            )
            self._records[new_id] = record
            return record

    def save_llm_settings(self, session_id: str, llm_settings: LLMSettings) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            record.llm_settings = llm_settings
            record.updated_at = datetime.now(UTC)
            return record

    def get(self, session_id: str) -> SessionRecord | None:
        with self._lock:
            self.cleanup_expired()
            record = self._records.get(session_id)
            if record:
                record.updated_at = datetime.now(UTC)
            return record

    def save_rfq(self, session_id: str, rfq_draft: RFQDraft) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            record.rfq_draft = rfq_draft
            record.rubric_proposal = None
            record.locked_artifact = None
            record.status = SessionStatus.DRAFT
            self._reset_phase_two_state(record)
            record.updated_at = datetime.now(UTC)
            return record

    def save_rubric(self, session_id: str, rubric: RubricProposal) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            record.rubric_proposal = rubric
            record.status = SessionStatus.PROPOSAL_READY
            record.updated_at = datetime.now(UTC)
            return record

    def lock_artifact(
        self,
        session_id: str,
        artifact: LockedFrameworkArtifact,
        vendor_pack: VendorPack,
        comparison_settings: ComparisonSettings | None,
    ) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            record.locked_artifact = artifact
            record.vendor_pack = vendor_pack
            record.comparison_settings = comparison_settings
            record.status = SessionStatus.LOCKED
            record.updated_at = datetime.now(UTC)
            return record

    def add_vendor(self, session_id: str, name: str) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            record.vendors.append(
                VendorRecord(
                    id=f"vendor_{uuid4().hex[:8]}",
                    name=name,
                    status=VendorStatus.NO_DOCUMENT,
                )
            )
            record.evaluation_report = None
            record.updated_at = datetime.now(UTC)
            return record

    def rename_vendor(self, session_id: str, vendor_id: str, name: str) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            vendor = self._find_vendor(record, vendor_id)
            if vendor is None:
                return None
            vendor.name = name
            record.evaluation_report = None
            record.updated_at = datetime.now(UTC)
            return record

    def delete_vendor(self, session_id: str, vendor_id: str) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            vendor = self._find_vendor(record, vendor_id)
            if vendor is None:
                return None
            record.vendors = [entry for entry in record.vendors if entry.id != vendor_id]
            record.vendor_reviews.pop(vendor_id, None)
            self._remove_vendor_document(record, vendor_id)
            record.evaluation_report = None
            record.updated_at = datetime.now(UTC)
            return record

    def save_vendor_document(
        self,
        session_id: str,
        vendor_id: str,
        document: VendorDocument,
        content: bytes,
    ) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            vendor = self._find_vendor(record, vendor_id)
            if vendor is None:
                return None

            vendor_dir = self._vendor_dir(session_id, vendor_id)
            if vendor_dir.exists():
                shutil.rmtree(vendor_dir)
            vendor_dir.mkdir(parents=True, exist_ok=True)

            file_path = vendor_dir / document.file_name
            file_path.write_bytes(content)

            vendor.document = document
            vendor.status = VendorStatus.UPLOADED
            vendor.warnings = list(document.warnings)
            vendor.extraction_error = None
            vendor.last_extracted_at = None
            vendor.last_evaluated_at = None

            record.document_paths[vendor_id] = file_path
            record.vendor_reviews.pop(vendor_id, None)
            record.evaluation_report = None
            record.updated_at = datetime.now(UTC)
            return record

    def get_vendor_document_path(self, session_id: str, vendor_id: str) -> Path | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            return record.document_paths.get(vendor_id)

    def save_vendor_review(self, session_id: str, review: VendorReview) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            vendor = self._find_vendor(record, review.vendor_id)
            if vendor is None:
                return None

            record.vendor_reviews[review.vendor_id] = review
            vendor.status = (
                VendorStatus.EVALUATION_READY
                if record.comparison_settings is not None
                else VendorStatus.EXTRACTED
            )
            vendor.extraction_error = None
            vendor.last_extracted_at = review.created_at
            vendor.warnings = list(dict.fromkeys([*vendor.warnings, *review.warnings]))
            vendor.last_evaluated_at = None
            record.evaluation_report = None
            record.updated_at = datetime.now(UTC)
            return record

    def set_vendor_extraction_error(self, session_id: str, vendor_id: str, message: str) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            vendor = self._find_vendor(record, vendor_id)
            if vendor is None:
                return None
            vendor.extraction_error = message
            vendor.status = VendorStatus.UPLOADED
            record.updated_at = datetime.now(UTC)
            return record

    def get_vendor_review(self, session_id: str, vendor_id: str) -> VendorReview | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            return record.vendor_reviews.get(vendor_id)

    def save_comparison_settings(
        self,
        session_id: str,
        comparison_settings: ComparisonSettings,
    ) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            record.comparison_settings = comparison_settings
            for vendor in record.vendors:
                if vendor.id in record.vendor_reviews and vendor.status != VendorStatus.EVALUATED:
                    vendor.status = VendorStatus.EVALUATION_READY
            record.evaluation_report = None
            record.updated_at = datetime.now(UTC)
            return record

    def save_evaluation_report(self, session_id: str, evaluation_report: EvaluationReport) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            record.evaluation_report = evaluation_report
            now = evaluation_report.generated_at
            evaluated_vendor_ids = {result.vendor_id for result in evaluation_report.technical_results}
            for vendor in record.vendors:
                if vendor.id in evaluated_vendor_ids:
                    vendor.status = VendorStatus.EVALUATED
                    vendor.last_evaluated_at = now
            record.updated_at = datetime.now(UTC)
            return record

    def cleanup_expired(self) -> None:
        cutoff = datetime.now(UTC) - self._ttl
        expired_ids = [session_id for session_id, record in self._records.items() if record.updated_at < cutoff]
        for session_id in expired_ids:
            self._records.pop(session_id, None)
            session_dir = self._session_dir(session_id)
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)

    def _reset_phase_two_state(self, record: SessionRecord) -> None:
        record.vendor_pack = None
        record.vendors = []
        record.comparison_settings = None
        record.vendor_reviews.clear()
        record.document_paths.clear()
        record.evaluation_report = None
        session_dir = self._session_dir(record.session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)

    def _remove_vendor_document(self, record: SessionRecord, vendor_id: str) -> None:
        record.document_paths.pop(vendor_id, None)
        vendor_dir = self._vendor_dir(record.session_id, vendor_id)
        if vendor_dir.exists():
            shutil.rmtree(vendor_dir, ignore_errors=True)

    def _find_vendor(self, record: SessionRecord, vendor_id: str) -> VendorRecord | None:
        return next((vendor for vendor in record.vendors if vendor.id == vendor_id), None)

    def _session_dir(self, session_id: str) -> Path:
        return self._storage_root / session_id

    def _vendor_dir(self, session_id: str, vendor_id: str) -> Path:
        return self._session_dir(session_id) / "vendors" / vendor_id
