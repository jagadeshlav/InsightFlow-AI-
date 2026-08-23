"""
InsightFlow AI â€” LLM Factory
Multi-provider LLM builder with allowlist-based model selection.
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


# â”€â”€â”€ Provider & Model Configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

PROVIDER_MODELS = {
    "direct": {
        "models": ["gemini-3.6-flash", "claude-haiku-4-5-20251001"],
        "allows_custom": False,
    },
    "tokenrouter": {
        "models": ["qwen/qwen3.8-max-free", "moonshotai/kimi-k3"],
        "allows_custom": True,
        "base_url": "https://api.tokenrouter.com/v1",
    },
    "openrouter": {
        "models": ["z-ai/glm-5.2:free", "nvidia/nemotron-3-super-120b-a12b:free"],
        "allows_custom": True,
        "base_url": "https://openrouter.ai/api/v1",
    },
}

# Default fallback (no key needed)
DEFAULT_PROVIDER = "direct"
DEFAULT_MODEL = "gemini-3.6-flash"


# â”€â”€â”€ Validation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class LLMError(Exception):
    """Raised when LLM creation or invocation fails."""

    def __init__(self, message: str, error_code: str = "LLM_ERROR", status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


def validate_provider_model(provider: Optional[str], model: Optional[str]) -> tuple[str, str]:
    """
    Validate and resolve provider/model selection.
    Returns (resolved_provider, resolved_model).
    Falls back to default if not specified.
    """
    # If no provider specified, use default
    if not provider:
        return DEFAULT_PROVIDER, DEFAULT_MODEL

    provider = provider.lower().strip()

    if provider not in PROVIDER_MODELS:
        raise LLMError(
            f"Unknown provider '{provider}'. Supported: {list(PROVIDER_MODELS.keys())}",
            "INVALID_PROVIDER",
            400,
        )

    config = PROVIDER_MODELS[provider]

    # If no model specified, use first in allowlist
    if not model:
        return provider, config["models"][0]

    model = model.strip()

    # Check if model is in allowlist or if custom is allowed
    if model in config["models"]:
        return provider, model

    if config.get("allows_custom"):
        # Validate custom model format (basic sanity check)
        if len(model) < 2 or len(model) > 100:
            raise LLMError(
                "Custom model name must be between 2 and 100 characters.",
                "INVALID_MODEL",
                400,
            )
        return provider, model

    raise LLMError(
        f"Model '{model}' not available for provider '{provider}'. "
        f"Available: {config['models']}",
        "INVALID_MODEL",
        400,
    )


# â”€â”€â”€ LLM Builder â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_llm(provider: str, model: str, api_key: Optional[str] = None):
    """
    Build and return an LLM instance for the given provider/model.

    If api_key is None and provider is 'tokenrouter', uses server's default key.
    For 'direct' providers, api_key is required.
    """
    from langchain_anthropic import ChatAnthropic
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_openai import ChatOpenAI

    try:
        if provider == "direct":
            if "claude" in model.lower():
                if not api_key:
                    raise LLMError(
                        "API key required for Claude models. Please provide your Anthropic API key.",
                        "KEY_REQUIRED",
                        401,
                    )
                return ChatAnthropic(
                    model=model,
                    temperature=0.2,
                    anthropic_api_key=api_key,
                    max_retries=3,
                )
            elif "gemini" in model.lower():
                # Use server key if user didnt provide one
                resolved_key = api_key or settings.google_api_key
                if not resolved_key:
                    raise LLMError(
                        "API key required for Gemini models. Please provide your Google API key.",
                        "KEY_REQUIRED",
                        401,
                    )
                return ChatGoogleGenerativeAI(
                    model=model,
                    temperature=0.2,
                    google_api_key=resolved_key,
                )
            else:
                raise LLMError(
                    f"Unknown direct model: {model}",
                    "INVALID_MODEL",
                    400,
                )

        elif provider == "tokenrouter":
            # Use server key if user didn't provide one
            resolved_key = api_key or settings.tokenrouter_api_key
            if not resolved_key:
                raise LLMError(
                    "TokenRouter API key not configured. Please provide your API key.",
                    "KEY_REQUIRED",
                    401,
                )
            return ChatOpenAI(
                model=model,
                temperature=0.2,
                openai_api_key=resolved_key,
                openai_api_base=PROVIDER_MODELS["tokenrouter"]["base_url"],
                max_retries=3,
            )

        elif provider == "openrouter":
            if not api_key:
                raise LLMError(
                    "API key required for OpenRouter. Please provide your OpenRouter API key.",
                    "KEY_REQUIRED",
                    401,
                )
            return ChatOpenAI(
                model=model,
                temperature=0.2,
                openai_api_key=api_key,
                openai_api_base=PROVIDER_MODELS["openrouter"]["base_url"],
                max_retries=3,
            )

        else:
            raise LLMError(f"Unknown provider: {provider}", "INVALID_PROVIDER", 400)

    except LLMError:
        raise
    except Exception as e:
        logger.error(f"LLM creation failed: {type(e).__name__}: {e}")
        raise LLMError(
            "Failed to initialize the AI model. Please check your API key and try again.",
            "LLM_INIT_ERROR",
            500,
        )
