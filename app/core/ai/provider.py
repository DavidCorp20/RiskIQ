from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

import httpx


class AIProvider(ABC):
    """Provider-agnostic interface for non-deterministic AI interpretation."""

    @abstractmethod
    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class GeminiProvider(AIProvider):
    """Gemini REST provider. Returns structured JSON and never calculates risk metrics."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("AI_MODEL", "gemini-3.8-flash")
        self.timeout = timeout or float(os.getenv("AI_TIMEOUT_SECONDS", "20"))
        self.base_url = os.getenv(
            "GEMINI_API_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta",
        ).rstrip("/")

    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        payload = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": (
                            "You are RiskIQ's data-ingestion semantic mapper. "
                            "Infer column equivalence only from the supplied metadata. "
                            "Do not calculate financial risk metrics. Return JSON only."
                        )
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                f"{prompt}\n\n"
                                f"CONTEXT_JSON:\n{json.dumps(context, ensure_ascii=False, default=str)}"
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }

        url = f"{self.base_url}/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": self.api_key},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        text = (
            body.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        if not text:
            raise ValueError("Gemini returned an empty response")

        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("Gemini returned invalid JSON") from exc

        if not isinstance(result, dict):
            raise ValueError("Gemini response must be a JSON object")
        return result


class OpenAIProvider(AIProvider):
    """Placeholder provider contract; implemented when OpenAI is enabled."""

    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("OpenAIProvider is reserved for the provider abstraction")


class AnthropicProvider(AIProvider):
    """Placeholder provider contract; implemented when Anthropic is enabled."""

    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("AnthropicProvider is reserved for the provider abstraction")


class LocalLLMProvider(AIProvider):
    """Placeholder provider contract for Ollama/local inference."""

    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("LocalLLMProvider is reserved for the provider abstraction")


def get_ai_provider(name: str | None = None) -> AIProvider:
    provider_name = (name or os.getenv("AI_PROVIDER", "gemini")).strip().lower()
    providers: dict[str, type[AIProvider]] = {
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "local": LocalLLMProvider,
        "ollama": LocalLLMProvider,
    }
    provider_class = providers.get(provider_name)
    if provider_class is None:
        raise ValueError(
            f"Unsupported AI_PROVIDER '{provider_name}'. "
            "Use gemini, openai, anthropic or local."
        )
    return provider_class()
