"""
InsightFlow AI - Sample Document Loader
Pre-indexes sample documents on startup for instant demo chat.
Uses in-memory ChromaDB (re-embeds on each server start).
"""

import logging
from pathlib import Path
from typing import Optional

from app.config import settings
from app.rag_engine import parse_document, chunk_documents

logger = logging.getLogger(__name__)

# --- Sample Registry ---

SAMPLES_DIR = Path(__file__).parent.parent / "samples"

SAMPLE_REGISTRY = {
    "one_piece": {
        "title": "One Piece: The Ultimate Epic Saga (Tenglish)",
        "description": "Complete One Piece story from Romance Dawn to Final Saga, written in Tenglish (Telugu + English). Great for testing multi-language RAG!",
        "filename": "one_piece_story_tenglish.txt",
    },
}


# --- Sample Store ---

class SampleStore:
    """
    Manages pre-indexed sample documents.
    Embeds on startup (requires GOOGLE_API_KEY).
    Shared read-only vector stores - not tied to user sessions.
    """

    def __init__(self):
        self._vector_stores: dict = {}
        self._chunk_counts: dict = {}
        self._loaded: bool = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def get_sample_ids(self) -> list[str]:
        return list(SAMPLE_REGISTRY.keys())

    def get_sample_info(self, sample_id: str) -> Optional[dict]:
        if sample_id not in SAMPLE_REGISTRY:
            return None
        info = SAMPLE_REGISTRY[sample_id].copy()
        info["id"] = sample_id
        info["chunk_count"] = self._chunk_counts.get(sample_id, 0)
        return info

    def get_all_samples_info(self) -> list[dict]:
        return [self.get_sample_info(sid) for sid in SAMPLE_REGISTRY]

    def get_vector_store(self, sample_id: str):
        return self._vector_stores.get(sample_id)

    def load_samples(self):
        """Load sample documents on startup."""
        if not settings.google_api_key:
            logger.warning(
                "GOOGLE_API_KEY not configured - sample documents will NOT be pre-indexed. "
                "Set the key in .env to enable instant sample chat."
            )
            for sample_id in SAMPLE_REGISTRY:
                self._chunk_counts[sample_id] = 0
            self._loaded = True
            return

        logger.info(f"Loading {len(SAMPLE_REGISTRY)} sample document(s)...")

        for sample_id, meta in SAMPLE_REGISTRY.items():
            try:
                self._load_single_sample(sample_id, meta)
            except Exception as e:
                logger.error(f"Failed to load sample '{sample_id}': {type(e).__name__}: {e}")
                self._chunk_counts[sample_id] = 0

        self._loaded = True
        logger.info(
            f"Sample loading complete. "
            f"{len(self._vector_stores)}/{len(SAMPLE_REGISTRY)} loaded successfully."
        )

    def _load_single_sample(self, sample_id: str, meta: dict):
        """Load, chunk, and embed a single sample document."""
        from app.rag_engine import create_vector_store

        filepath = SAMPLES_DIR / meta["filename"]

        if not filepath.exists():
            logger.warning(f"Sample file not found: {filepath}")
            self._chunk_counts[sample_id] = 0
            return

        logger.info(f"Loading sample: {sample_id} ({meta['filename']})")

        file_bytes = filepath.read_bytes()
        documents = parse_document(file_bytes, meta["filename"])
        chunks = chunk_documents(documents, meta["filename"])
        self._chunk_counts[sample_id] = len(chunks)

        vector_store = create_vector_store(f"sample_{sample_id}", chunks)
        self._vector_stores[sample_id] = vector_store

        logger.info(f"Sample '{sample_id}' loaded: {len(chunks)} chunks embedded")


# --- Singleton ---

sample_store = SampleStore()