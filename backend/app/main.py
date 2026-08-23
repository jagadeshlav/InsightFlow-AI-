"""
InsightFlow AI â€” FastAPI Application
Main entry point for the backend server.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import HealthResponse, ErrorResponse, UploadResponse, SessionDeleteResponse, ChatRequest, ChatResponse, RetrievedChunk, SampleInfo, SampleListResponse, SampleChatRequest
from app.rag_engine import validate_file, parse_document, chunk_documents, create_vector_store, query_rag, FileValidationError
from app.session_store import session_store
from app.llm_factory import get_llm, validate_provider_model, LLMError
from app.sample_loader import sample_store

# â”€â”€â”€ Logging Setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# â”€â”€â”€ Lifespan â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan â€” startup and shutdown logic."""
    logger.info(f"ðŸš€ {settings.app_name} v{settings.app_version} starting...")
    logger.info(f"   CORS origins: {settings.cors_origin_list}")
    logger.info(f"   Max sessions: {settings.max_sessions}")
    logger.info(f"   Session TTL: {settings.session_ttl_minutes} min")

    # Load pre-indexed sample documents in background (non-blocking for port binding)
    sample_store.load_samples_background()

    yield
    logger.info(f"ðŸ‘‹ {settings.app_name} shutting down...")


# â”€â”€â”€ App Factory â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Document Q&A RAG API â€” Upload documents, ask questions, get AI-powered answers.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# â”€â”€â”€ CORS Middleware â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# â”€â”€â”€ Global Exception Handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler â€” never expose internal details to the client."""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again.",
        ).model_dump(),
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error_code="NOT_FOUND",
            message=f"Endpoint not found: {request.method} {request.url.path}",
        ).model_dump(),
    )


@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    """Custom validation error handler â€” don't expose raw Pydantic errors."""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Invalid request data. Please check your input.",
        ).model_dump(),
    )


# â”€â”€â”€ Health Endpoint â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint â€” confirms the API is running."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        app_name=settings.app_name,
    )


# â”€â”€â”€ Upload Endpoint â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.post("/api/upload", response_model=UploadResponse, tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document (PDF, TXT, DOCX) for RAG processing.
    Validates, parses, and chunks the document.
    Returns session_id for subsequent chat requests.
    """
    # Read file content (bounded read to prevent memory issues)
    file_bytes = await file.read()
    file_size = len(file_bytes)
    filename = file.filename or "unknown"

    # Validate file
    try:
        validate_file(filename, file_size)
    except FileValidationError as e:
        status_code = 415 if e.error_code == "UNSUPPORTED_FILE_TYPE" else 413 if e.error_code == "FILE_TOO_LARGE" else 422
        return JSONResponse(
            status_code=status_code,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
            ).model_dump(),
        )

    # Parse document
    try:
        documents = parse_document(file_bytes, filename)
    except FileValidationError as e:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
            ).model_dump(),
        )

    # Chunk documents
    chunks = chunk_documents(documents, filename)

    # Create session
    session = session_store.create_session(
        filename=filename,
        chunk_count=len(chunks),
        chunks=chunks,
    )

    # Create vector store with embeddings (this is the slow part)
    try:
        session.status = "embedding"
        vector_store = create_vector_store(session.session_id, chunks)
        session.vector_store = vector_store
        session.status = "ready"
    except Exception as e:
        logger.error(f"Embedding failed for session {session.session_id}: {e}")
        session_store.delete_session(session.session_id)
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error_code="EMBEDDING_FAILED",
                message="Failed to process document embeddings. The embedding service may be temporarily unavailable. Please try again.",
            ).model_dump(),
        )

    logger.info(f"Upload complete: session={session.session_id}, file='{filename}', chunks={len(chunks)}, status=ready")

    return UploadResponse(
        session_id=session.session_id,
        filename=filename,
        chunk_count=len(chunks),
        status="ready",
    )


# â”€â”€â”€ Session Delete Endpoint â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.delete("/api/sessions/{session_id}", response_model=SessionDeleteResponse, tags=["Sessions"])
async def delete_session(session_id: str):
    """Delete a session and free its resources."""
    deleted = session_store.delete_session(session_id)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error_code="SESSION_NOT_FOUND",
                message="Session not found or already expired.",
            ).model_dump(),
        )
    return SessionDeleteResponse(
        message="Session deleted successfully.",
        session_id=session_id,
    )


# â”€â”€â”€ Sample Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/api/samples", response_model=SampleListResponse, tags=["Samples"])
async def list_samples():
    """List available pre-indexed sample documents."""
    samples_info = sample_store.get_all_samples_info()
    samples = [
        SampleInfo(
            id=s["id"],
            title=s["title"],
            description=s["description"],
            chunk_count=s["chunk_count"],
        )
        for s in samples_info
    ]
    return SampleListResponse(samples=samples)


@app.post("/api/samples/{sample_id}/chat", response_model=ChatResponse, tags=["Samples"])
async def chat_with_sample(sample_id: str, request: SampleChatRequest):
    """
    Chat with a pre-indexed sample document.
    No upload needed â€” instant Q&A!
    """
    # Validate sample exists
    sample_info = sample_store.get_sample_info(sample_id)
    if sample_info is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error_code="SAMPLE_NOT_FOUND",
                message=f"Sample '{sample_id}' not found. Use GET /api/samples to see available samples.",
            ).model_dump(),
        )

    # Get pre-indexed vector store
    vector_store = sample_store.get_vector_store(sample_id)
    if vector_store is None:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error_code="SAMPLE_NOT_READY",
                message="Sample document not yet indexed. Server may still be starting up, or embedding key is not configured.",
            ).model_dump(),
        )

    # Validate and resolve provider/model
    try:
        resolved_provider, resolved_model = validate_provider_model(
            request.provider, request.model
        )
    except LLMError as e:
        return JSONResponse(
            status_code=e.status_code,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
            ).model_dump(),
        )

    # Build LLM
    try:
        llm = get_llm(resolved_provider, resolved_model, request.api_key)
    except LLMError as e:
        return JSONResponse(
            status_code=e.status_code,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
            ).model_dump(),
        )

    # Execute RAG query
    try:
        result = query_rag(vector_store, request.question, llm)
    except Exception as e:
        error_msg = str(e).lower()

        if "401" in error_msg or "unauthorized" in error_msg or "invalid api key" in error_msg:
            return JSONResponse(
                status_code=401,
                content=ErrorResponse(
                    error_code="INVALID_API_KEY",
                    message="Invalid API key. Please check your key and try again.",
                ).model_dump(),
            )
        elif "429" in error_msg or "rate limit" in error_msg:
            return JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    error_code="RATE_LIMITED",
                    message="Model is busy (rate limited). Please wait a moment or try a different model.",
                ).model_dump(),
            )
        elif "403" in error_msg or "insufficient" in error_msg:
            return JSONResponse(
                status_code=403,
                content=ErrorResponse(
                    error_code="INSUFFICIENT_CREDITS",
                    message="Insufficient credits on this provider. Try the free default model (leave API key empty).",
                ).model_dump(),
            )
        else:
            logger.error(f"Sample RAG query failed: {type(e).__name__}: {e}")
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error_code="CHAT_ERROR",
                    message=f"Failed to generate answer: {type(e).__name__}: {str(e)[:200]}",
                ).model_dump(),
            )

    # Build response
    retrieved_chunks = [
        RetrievedChunk(content=chunk["content"], metadata=chunk["metadata"])
        for chunk in result["retrieved_chunks"]
    ]

    return ChatResponse(
        answer=result["answer"],
        retrieved_chunks=retrieved_chunks,
        provider=resolved_provider,
        model=resolved_model,
    )


# â”€â”€â”€ Chat Endpoint â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_with_document(request: ChatRequest):
    """
    Ask a question about an uploaded document.
    Retrieves relevant chunks and generates an AI answer.
    """
    # Get session
    session = session_store.get_session(request.session_id)
    if session is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error_code="SESSION_NOT_FOUND",
                message="Session not found or expired. Please upload your document again.",
            ).model_dump(),
        )

    if not session.is_ready:
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                error_code="SESSION_NOT_READY",
                message="Document is still being processed. Please wait and try again.",
            ).model_dump(),
        )

    # Validate and resolve provider/model
    try:
        resolved_provider, resolved_model = validate_provider_model(
            request.provider, request.model
        )
    except LLMError as e:
        return JSONResponse(
            status_code=e.status_code,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
            ).model_dump(),
        )

    # Build LLM
    try:
        llm = get_llm(resolved_provider, resolved_model, request.api_key)
    except LLMError as e:
        return JSONResponse(
            status_code=e.status_code,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
            ).model_dump(),
        )

    # Execute RAG query
    try:
        result = query_rag(session.vector_store, request.question, llm)
    except Exception as e:
        error_msg = str(e).lower()

        # Map common provider errors to user-friendly messages
        if "401" in error_msg or "unauthorized" in error_msg or "invalid api key" in error_msg:
            return JSONResponse(
                status_code=401,
                content=ErrorResponse(
                    error_code="INVALID_API_KEY",
                    message="Invalid API key. Please check your key and try again.",
                ).model_dump(),
            )
        elif "429" in error_msg or "rate limit" in error_msg:
            return JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    error_code="RATE_LIMITED",
                    message="Model is busy (rate limited). Please wait a moment or try a different model.",
                ).model_dump(),
            )
        elif "403" in error_msg or "insufficient" in error_msg or "no credits" in error_msg:
            return JSONResponse(
                status_code=403,
                content=ErrorResponse(
                    error_code="INSUFFICIENT_CREDITS",
                    message="Insufficient credits on this provider. Try the free default model (leave API key empty).",
                ).model_dump(),
            )
        else:
            logger.error(f"RAG query failed: {type(e).__name__}: {e}")
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error_code="CHAT_ERROR",
                    message="Failed to generate an answer. Please try again.",
                ).model_dump(),
            )

    # Build response
    retrieved_chunks = [
        RetrievedChunk(content=chunk["content"], metadata=chunk["metadata"])
        for chunk in result["retrieved_chunks"]
    ]

    return ChatResponse(
        answer=result["answer"],
        retrieved_chunks=retrieved_chunks,
        provider=resolved_provider,
        model=resolved_model,
    )


# â”€â”€â”€ Run with Uvicorn (local dev) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
