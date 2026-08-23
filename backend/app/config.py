"""
InsightFlow AI â€” Application Configuration
Loads environment variables and provides typed settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    google_api_key: str = Field(default="", description="Google Gemini API key (legacy, optional)")
    jina_api_key: str = Field(default="", description="Jina AI API key for embeddings")
    tokenrouter_api_key: str = Field(default="", description="TokenRouter API key for default free model")

    # Application Settings
    app_name: str = "InsightFlow AI"
    app_version: str = "1.0.0"
    debug: bool = False

    # Session Settings
    max_sessions: int = 20
    session_ttl_minutes: int = 30

    # Upload Settings
    max_file_size_mb: int = 10
    max_chunk_count: int = 500
    max_document_chars: int = 20000  # ~5K tokens limit for demo (protects embedding quota)

    # RAG Settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    retriever_top_k: int = 3

    # CORS Origins (comma-separated for env var)
    cors_origins: str = "*"  # Allow all origins for local development. Lock down for production.

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# Singleton instance
settings = Settings()
