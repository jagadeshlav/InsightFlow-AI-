"""
Tests for InsightFlow AI — Chat endpoint.
Tests mock both embedding and LLM to avoid external API calls.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.session_store import session_store, Session

client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _create_ready_session():
    """Helper: create a ready session with a mock vector store."""
    session_store._sessions.clear()

    mock_vector_store = MagicMock()
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [
        MagicMock(
            page_content="The total revenue in Q3 was $4.2 million.",
            metadata={"source_filename": "report.pdf", "chunk_index": 0},
        ),
        MagicMock(
            page_content="Engineering contributed 62% of the revenue.",
            metadata={"source_filename": "report.pdf", "chunk_index": 5},
        ),
    ]
    mock_vector_store.as_retriever.return_value = mock_retriever

    session = Session(
        session_id="test-session-123",
        filename="report.pdf",
        chunk_count=50,
        chunks=[],
        vector_store=mock_vector_store,
        status="ready",
    )
    session_store._sessions["test-session-123"] = session
    return session


class TestChatEndpoint:
    """Tests for POST /api/chat."""

    def setup_method(self):
        """Reset sessions before each test."""
        session_store._sessions.clear()

    @patch("app.main.get_llm")
    def test_chat_with_default_model(self, mock_get_llm):
        """Chat with no provider/key should use default TokenRouter model."""
        _create_ready_session()

        # Mock the LLM to return a fake answer
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # Mock query_rag to return a response
        with patch("app.main.query_rag") as mock_query:
            mock_query.return_value = {
                "answer": "The total revenue in Q3 was $4.2 million.",
                "retrieved_chunks": [
                    {"content": "Q3 revenue was $4.2M...", "metadata": {"chunk_index": 0}},
                ],
            }

            response = client.post("/api/chat", json={
                "session_id": "test-session-123",
                "question": "What was the total revenue in Q3?",
            })

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == "The total revenue in Q3 was $4.2 million."
        assert data["provider"] == "tokenrouter"
        assert data["model"] == "qwen/qwen3.8-max-free"
        assert len(data["retrieved_chunks"]) > 0

    def test_chat_missing_session(self):
        """Chat with non-existent session should return 404."""
        response = client.post("/api/chat", json={
            "session_id": "non-existent-session",
            "question": "Hello?",
        })
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "SESSION_NOT_FOUND"

    def test_chat_empty_question(self):
        """Chat with empty question should return 422."""
        _create_ready_session()
        response = client.post("/api/chat", json={
            "session_id": "test-session-123",
            "question": "",
        })
        assert response.status_code == 422

    def test_chat_invalid_provider(self):
        """Chat with unknown provider should return 400."""
        _create_ready_session()
        response = client.post("/api/chat", json={
            "session_id": "test-session-123",
            "question": "test",
            "provider": "unknown_provider",
        })
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "INVALID_PROVIDER"

    @patch("app.main.get_llm")
    def test_chat_invalid_api_key_error(self, mock_get_llm):
        """LLM returning 401 should map to user-friendly message."""
        _create_ready_session()
        mock_get_llm.return_value = MagicMock()

        with patch("app.main.query_rag") as mock_query:
            mock_query.side_effect = Exception("Error code: 401 Unauthorized - invalid api key")

            response = client.post("/api/chat", json={
                "session_id": "test-session-123",
                "question": "What is revenue?",
                "provider": "tokenrouter",
                "api_key": "bad-key",
            })

        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    @patch("app.main.get_llm")
    def test_chat_rate_limited_error(self, mock_get_llm):
        """LLM returning 429 should map to rate limit message."""
        _create_ready_session()
        mock_get_llm.return_value = MagicMock()

        with patch("app.main.query_rag") as mock_query:
            mock_query.side_effect = Exception("Error 429: rate limit exceeded")

            response = client.post("/api/chat", json={
                "session_id": "test-session-123",
                "question": "test?",
            })

        assert response.status_code == 429
        data = response.json()
        assert data["error_code"] == "RATE_LIMITED"

    @patch("app.main.get_llm")
    def test_chat_insufficient_credits_error(self, mock_get_llm):
        """LLM returning 403 should map to credits message."""
        _create_ready_session()
        mock_get_llm.return_value = MagicMock()

        with patch("app.main.query_rag") as mock_query:
            mock_query.side_effect = Exception("403 Forbidden: insufficient credits")

            response = client.post("/api/chat", json={
                "session_id": "test-session-123",
                "question": "test?",
                "provider": "openrouter",
                "api_key": "some-key",
            })

        assert response.status_code == 403
        data = response.json()
        assert data["error_code"] == "INSUFFICIENT_CREDITS"

    def test_chat_session_not_ready(self):
        """Chat with session still embedding should return 409."""
        session_store._sessions.clear()
        session = Session(
            session_id="embedding-session",
            filename="doc.pdf",
            chunk_count=10,
            chunks=[],
            vector_store=None,
            status="embedding",
        )
        session_store._sessions["embedding-session"] = session

        response = client.post("/api/chat", json={
            "session_id": "embedding-session",
            "question": "test?",
        })
        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == "SESSION_NOT_READY"


class TestLLMFactory:
    """Tests for provider/model validation."""

    def test_default_fallback(self):
        """No provider/model should default to TokenRouter free model."""
        from app.llm_factory import validate_provider_model
        provider, model = validate_provider_model(None, None)
        assert provider == "tokenrouter"
        assert model == "qwen/qwen3.8-max-free"

    def test_valid_direct_provider(self):
        """Direct provider with valid model."""
        from app.llm_factory import validate_provider_model
        provider, model = validate_provider_model("direct", "claude-haiku-4-5-20251001")
        assert provider == "direct"
        assert model == "claude-haiku-4-5-20251001"

    def test_custom_model_tokenrouter(self):
        """TokenRouter should allow custom model names."""
        from app.llm_factory import validate_provider_model
        provider, model = validate_provider_model("tokenrouter", "custom/my-model")
        assert provider == "tokenrouter"
        assert model == "custom/my-model"

    def test_custom_model_not_allowed_direct(self):
        """Direct provider should NOT allow custom model names."""
        from app.llm_factory import validate_provider_model, LLMError
        import pytest
        with pytest.raises(LLMError) as exc_info:
            validate_provider_model("direct", "some-random-model")
        assert exc_info.value.error_code == "INVALID_MODEL"

    def test_invalid_provider(self):
        """Unknown provider should raise LLMError."""
        from app.llm_factory import validate_provider_model, LLMError
        import pytest
        with pytest.raises(LLMError) as exc_info:
            validate_provider_model("fakeprovider", "model")
        assert exc_info.value.error_code == "INVALID_PROVIDER"
