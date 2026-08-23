"""
Tests for InsightFlow AI — Sample document endpoints.
Tests mock embedding to avoid external API calls.
"""

from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.sample_loader import sample_store

client = TestClient(app)


def _setup_mock_sample_store():
    """Set up sample_store with a mock vector store."""
    mock_vector_store = MagicMock()
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [
        MagicMock(
            page_content="Luffy oka chinna pillaadu tana journey start chesthaadu... athane mana Monkey D. Luffy!",
            metadata={"source_filename": "one_piece_story_tenglish.txt", "chunk_index": 3},
        ),
        MagicMock(
            page_content="Shanks tana favorite Straw Hat ni Luffy thalapai petti antadu...",
            metadata={"source_filename": "one_piece_story_tenglish.txt", "chunk_index": 7},
        ),
    ]
    mock_vector_store.as_retriever.return_value = mock_retriever

    sample_store._vector_stores["one_piece"] = mock_vector_store
    sample_store._chunk_counts["one_piece"] = 150
    sample_store._loaded = True


class TestSampleList:
    """Tests for GET /api/samples."""

    def setup_method(self):
        _setup_mock_sample_store()

    def test_list_samples_returns_200(self):
        response = client.get("/api/samples")
        assert response.status_code == 200

    def test_list_samples_structure(self):
        response = client.get("/api/samples")
        data = response.json()
        assert "samples" in data
        assert len(data["samples"]) >= 1

    def test_sample_has_required_fields(self):
        response = client.get("/api/samples")
        data = response.json()
        sample = data["samples"][0]
        assert "id" in sample
        assert "title" in sample
        assert "description" in sample
        assert "chunk_count" in sample

    def test_one_piece_sample_listed(self):
        response = client.get("/api/samples")
        data = response.json()
        ids = [s["id"] for s in data["samples"]]
        assert "one_piece" in ids


class TestSampleChat:
    """Tests for POST /api/samples/{sample_id}/chat."""

    def setup_method(self):
        _setup_mock_sample_store()

    @patch("app.main.get_llm")
    @patch("app.main.query_rag")
    def test_sample_chat_success(self, mock_query, mock_get_llm):
        """Sample chat should work with default model."""
        mock_get_llm.return_value = MagicMock()
        mock_query.return_value = {
            "answer": "Luffy anedi Monkey D. Luffy, future Pirate King!",
            "retrieved_chunks": [
                {"content": "Luffy oka chinna pillaadu...", "metadata": {"chunk_index": 3}},
            ],
        }

        response = client.post("/api/samples/one_piece/chat", json={
            "question": "Who is Luffy?",
        })

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["provider"] == "tokenrouter"
        assert data["model"] == "qwen/qwen3.8-max-free"
        assert len(data["retrieved_chunks"]) > 0

    def test_sample_not_found(self):
        """Non-existent sample should return 404."""
        response = client.post("/api/samples/nonexistent/chat", json={
            "question": "test?",
        })
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "SAMPLE_NOT_FOUND"

    def test_sample_chat_empty_question(self):
        """Empty question should fail validation."""
        response = client.post("/api/samples/one_piece/chat", json={
            "question": "",
        })
        assert response.status_code == 422

    def test_sample_not_indexed(self):
        """If vector store is None (not indexed), return 503."""
        sample_store._vector_stores.pop("one_piece", None)

        response = client.post("/api/samples/one_piece/chat", json={
            "question": "Who is Luffy?",
        })
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "SAMPLE_NOT_READY"

    @patch("app.main.get_llm")
    @patch("app.main.query_rag")
    def test_sample_chat_with_custom_provider(self, mock_query, mock_get_llm):
        """Sample chat with explicit provider should use that provider."""
        mock_get_llm.return_value = MagicMock()
        mock_query.return_value = {
            "answer": "Luffy's dream is to become Pirate King.",
            "retrieved_chunks": [],
        }

        response = client.post("/api/samples/one_piece/chat", json={
            "question": "What is Luffy's dream?",
            "provider": "tokenrouter",
            "model": "moonshotai/kimi-k3",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "moonshotai/kimi-k3"
