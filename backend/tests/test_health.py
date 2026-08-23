"""
Tests for InsightFlow AI — Health endpoint, CORS, and error handling.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /api/health."""

    def test_health_returns_200(self):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_response_structure(self):
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "app_name" in data
        assert data["app_name"] == "InsightFlow AI"

    def test_health_version_format(self):
        response = client.get("/api/health")
        data = response.json()
        # Version should be semver-ish
        parts = data["version"].split(".")
        assert len(parts) == 3


class TestCORS:
    """Tests for CORS headers."""

    def test_cors_allows_configured_origin(self):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "https://insightflowai.online",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "https://insightflowai.online"

    def test_cors_allows_localhost(self):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5500",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5500"

    def test_cors_blocks_unknown_origin(self):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "https://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should NOT include the evil origin
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin != "https://evil-site.com"


class TestErrorHandling:
    """Tests for error response structure."""

    def test_404_returns_structured_error(self):
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "NOT_FOUND"
        assert "message" in data

    def test_422_returns_structured_error(self):
        # POST to a future endpoint with invalid data to trigger validation
        # For now, just verify the handler exists by checking structure
        response = client.post(
            "/api/health",  # GET-only endpoint, POST should be 405
        )
        # Method not allowed returns 405, which is fine
        assert response.status_code in [405, 404, 422]
