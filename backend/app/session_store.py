"""
InsightFlow AI — Session Store
In-memory session management with TTL and capacity limits.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a single user session with uploaded document data."""

    session_id: str
    filename: str
    chunk_count: int
    chunks: list = field(default_factory=list)
    vector_store: Any = None  # ChromaDB collection reference
    status: str = "chunked"  # "chunked" → "embedding" → "ready"
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    def touch(self):
        """Update last accessed time."""
        self.last_accessed = time.time()

    @property
    def is_expired(self) -> bool:
        """Check if session has exceeded TTL."""
        elapsed_minutes = (time.time() - self.last_accessed) / 60
        return elapsed_minutes > settings.session_ttl_minutes

    @property
    def is_ready(self) -> bool:
        """Check if session is ready for chat (embeddings done)."""
        return self.status == "ready" and self.vector_store is not None


class SessionStore:
    """
    In-memory session manager with TTL expiry and max capacity.

    Key behaviors:
    - Max sessions enforced (oldest evicted when full)
    - TTL-based expiry (lazy cleanup on access)
    - Thread-safe for single-worker deployment (no locks needed)
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    @property
    def count(self) -> int:
        """Number of active sessions."""
        return len(self._sessions)

    def create_session(self, filename: str, chunk_count: int, chunks: list) -> Session:
        """
        Create a new session. Evicts oldest if at capacity.
        Returns the new Session object.
        """
        # Lazy cleanup before creating
        self._cleanup_expired()

        # Evict oldest if at max capacity
        if self.count >= settings.max_sessions:
            self._evict_oldest()

        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            filename=filename,
            chunk_count=chunk_count,
            chunks=chunks,
        )
        self._sessions[session_id] = session
        logger.info(f"Session created: {session_id} ({filename}, {chunk_count} chunks) — total: {self.count}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID. Returns None if not found or expired.
        Updates last_accessed on successful retrieval.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if session.is_expired:
            logger.info(f"Session expired: {session_id}")
            self.delete_session(session_id)
            return None

        session.touch()
        return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and free its resources.
        Returns True if deleted, False if not found.
        """
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False

        # Clean up ChromaDB collection if exists
        if session.vector_store is not None:
            try:
                # Delete the collection to free memory
                session.vector_store = None
            except Exception as e:
                logger.warning(f"Error cleaning up vector store for {session_id}: {e}")

        session.chunks = []  # Free chunk memory
        logger.info(f"Session deleted: {session_id} — total: {self.count}")
        return True

    def _cleanup_expired(self):
        """Remove all expired sessions (lazy cleanup)."""
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if session.is_expired
        ]
        for sid in expired_ids:
            self.delete_session(sid)

        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired session(s)")

    def _evict_oldest(self):
        """Evict the least recently accessed session."""
        if not self._sessions:
            return

        oldest_id = min(
            self._sessions,
            key=lambda sid: self._sessions[sid].last_accessed,
        )
        logger.warning(f"Evicting oldest session (capacity full): {oldest_id}")
        self.delete_session(oldest_id)


# ─── Singleton Instance ───────────────────────────────────────────────────────

session_store = SessionStore()
