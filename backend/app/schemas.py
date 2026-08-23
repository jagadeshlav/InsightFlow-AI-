"""
InsightFlow AI — Request/Response Schemas
Pydantic models for API contracts.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    app_name: str


# ─── Errors ───────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: Optional[str] = None


# ─── Upload ───────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    session_id: str
    filename: str
    chunk_count: int
    status: str  # "chunked", "embedding", "ready"


# ─── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    question: str = Field(..., min_length=1, max_length=2000)
    provider: Optional[str] = None  # "direct", "tokenrouter", "openrouter"
    model: Optional[str] = None
    api_key: Optional[str] = None  # User's own key (never stored)


class RetrievedChunk(BaseModel):
    content: str
    metadata: dict = {}


class ChatResponse(BaseModel):
    answer: str
    retrieved_chunks: list[RetrievedChunk] = []
    provider: str
    model: str


# ─── Samples ──────────────────────────────────────────────────────────────────

class SampleInfo(BaseModel):
    id: str
    title: str
    description: str
    chunk_count: int


class SampleListResponse(BaseModel):
    samples: list[SampleInfo]


class SampleChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None


# ─── Sessions ─────────────────────────────────────────────────────────────────

class SessionDeleteResponse(BaseModel):
    message: str
    session_id: str
