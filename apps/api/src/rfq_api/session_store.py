from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import uuid4

from .models import LockedFrameworkArtifact, RFQDraft, RubricProposal, SessionSnapshot, SessionStatus
from .seeds import build_seed_rfq


@dataclass
class SessionRecord:
    session_id: str
    status: SessionStatus
    rfq_draft: RFQDraft
    rubric_proposal: RubricProposal | None
    locked_artifact: LockedFrameworkArtifact | None
    updated_at: datetime

    def snapshot(self) -> SessionSnapshot:
        return SessionSnapshot(
            session_id=self.session_id,
            status=self.status,
            rfq_draft=self.rfq_draft,
            rubric_proposal=self.rubric_proposal,
            locked_artifact=self.locked_artifact,
            updated_at=self.updated_at,
        )


class SessionStore:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
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
                rfq_draft=build_seed_rfq(),
                rubric_proposal=None,
                locked_artifact=None,
                updated_at=datetime.now(UTC),
            )
            self._records[new_id] = record
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

    def lock_artifact(self, session_id: str, artifact: LockedFrameworkArtifact) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if not record:
                return None
            record.locked_artifact = artifact
            record.status = SessionStatus.LOCKED
            record.updated_at = datetime.now(UTC)
            return record

    def cleanup_expired(self) -> None:
        cutoff = datetime.now(UTC) - self._ttl
        expired_ids = [session_id for session_id, record in self._records.items() if record.updated_at < cutoff]
        for session_id in expired_ids:
            self._records.pop(session_id, None)
