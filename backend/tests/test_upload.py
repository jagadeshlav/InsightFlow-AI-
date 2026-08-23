"""
Tests for InsightFlow AI — Document upload endpoint.
Tests mock the embedding step to avoid calling external APIs.
"""

import io
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.session_store import session_store

client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _mock_create_vector_store(session_id, chunks):
    """Mock vector store creation — returns a fake object."""
    mock_store = MagicMock()
    mock_store.as_retriever.return_value = MagicMock()
    return mock_store


class TestUploadValidation:
    """Tests for file validation logic."""

    def setup_method(self):
        """Clear session store before each test."""
        session_store._sessions.clear()

    @patch("app.main.create_vector_store", side_effect=_mock_create_vector_store)
    def test_upload_valid_txt(self, mock_embed):
        """Valid TXT file should return 200 with session info."""
        file_path = FIXTURES_DIR / "sample.txt"
        with open(file_path, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("test_document.txt", f, "text/plain")},
            )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["filename"] == "test_document.txt"
        assert data["chunk_count"] > 0
        assert data["status"] == "ready"

    def test_upload_unsupported_extension(self):
        """Unsupported file type should return 415."""
        fake_file = io.BytesIO(b"some content")
        response = client.post(
            "/api/upload",
            files={"file": ("image.png", fake_file, "image/png")},
        )
        assert response.status_code == 415
        data = response.json()
        assert data["error_code"] == "UNSUPPORTED_FILE_TYPE"

    def test_upload_empty_file(self):
        """Empty file should return 422."""
        empty_file = io.BytesIO(b"")
        response = client.post(
            "/api/upload",
            files={"file": ("empty.txt", empty_file, "text/plain")},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "EMPTY_FILE"

    def test_upload_file_too_large(self):
        """File exceeding 10MB should return 413."""
        large_content = b"x" * (11 * 1024 * 1024)
        large_file = io.BytesIO(large_content)
        response = client.post(
            "/api/upload",
            files={"file": ("large.txt", large_file, "text/plain")},
        )
        assert response.status_code == 413
        data = response.json()
        assert data["error_code"] == "FILE_TOO_LARGE"

    def test_upload_csv_not_supported(self):
        """CSV files should not be supported."""
        csv_file = io.BytesIO(b"name,age\nAlice,30\nBob,25")
        response = client.post(
            "/api/upload",
            files={"file": ("data.csv", csv_file, "text/csv")},
        )
        assert response.status_code == 415

    def test_upload_exe_not_supported(self):
        """Executable files should not be supported."""
        exe_file = io.BytesIO(b"\x4d\x5a" + b"\x00" * 100)
        response = client.post(
            "/api/upload",
            files={"file": ("malware.exe", exe_file, "application/octet-stream")},
        )
        assert response.status_code == 415


class TestUploadParsing:
    """Tests for document parsing and chunking."""

    def setup_method(self):
        """Clear session store before each test."""
        session_store._sessions.clear()

    @patch("app.main.create_vector_store", side_effect=_mock_create_vector_store)
    def test_txt_produces_chunks(self, mock_embed):
        """TXT file should be parsed and chunked correctly."""
        file_path = FIXTURES_DIR / "sample.txt"
        with open(file_path, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("rag_explainer.txt", f, "text/plain")},
            )
        data = response.json()
        assert data["chunk_count"] >= 2

    @patch("app.main.create_vector_store", side_effect=_mock_create_vector_store)
    def test_session_id_is_uuid(self, mock_embed):
        """Session ID should be a valid UUID4."""
        import uuid
        file_path = FIXTURES_DIR / "sample.txt"
        with open(file_path, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("test.txt", f, "text/plain")},
            )
        data = response.json()
        parsed_uuid = uuid.UUID(data["session_id"], version=4)
        assert str(parsed_uuid) == data["session_id"]

    @patch("app.main.create_vector_store", side_effect=_mock_create_vector_store)
    def test_different_uploads_get_different_sessions(self, mock_embed):
        """Each upload should get a unique session ID."""
        file_path = FIXTURES_DIR / "sample.txt"

        with open(file_path, "rb") as f:
            response1 = client.post(
                "/api/upload",
                files={"file": ("doc1.txt", f, "text/plain")},
            )
        with open(file_path, "rb") as f:
            response2 = client.post(
                "/api/upload",
                files={"file": ("doc2.txt", f, "text/plain")},
            )

        assert response1.json()["session_id"] != response2.json()["session_id"]

    @patch("app.main.create_vector_store", side_effect=_mock_create_vector_store)
    def test_session_stored_after_upload(self, mock_embed):
        """Upload should create a session in session_store."""
        file_path = FIXTURES_DIR / "sample.txt"
        with open(file_path, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("stored.txt", f, "text/plain")},
            )
        data = response.json()
        session = session_store.get_session(data["session_id"])
        assert session is not None
        assert session.filename == "stored.txt"
        assert session.status == "ready"

    @patch("app.main.create_vector_store", side_effect=Exception("API unavailable"))
    def test_embedding_failure_returns_503(self, mock_embed):
        """If embedding fails, return 503 and cleanup session."""
        file_path = FIXTURES_DIR / "sample.txt"
        with open(file_path, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("fail.txt", f, "text/plain")},
            )
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "EMBEDDING_FAILED"


class TestSessionDelete:
    """Tests for DELETE /api/sessions/{session_id}."""

    def setup_method(self):
        """Clear session store before each test."""
        session_store._sessions.clear()

    @patch("app.main.create_vector_store", side_effect=_mock_create_vector_store)
    def test_delete_existing_session(self, mock_embed):
        """Deleting an existing session should succeed."""
        file_path = FIXTURES_DIR / "sample.txt"
        with open(file_path, "rb") as f:
            upload_resp = client.post(
                "/api/upload",
                files={"file": ("delete_me.txt", f, "text/plain")},
            )
        session_id = upload_resp.json()["session_id"]

        response = client.delete(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "deleted" in data["message"].lower()

        # Verify it's gone
        assert session_store.get_session(session_id) is None

    def test_delete_nonexistent_session(self):
        """Deleting a non-existent session should return 404."""
        response = client.delete("/api/sessions/non-existent-id-12345")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "SESSION_NOT_FOUND"
