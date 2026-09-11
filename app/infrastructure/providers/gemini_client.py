from typing import Any

import requests

from app.config import settings
from app.core import ProviderError


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: int | None = None,
    ) -> None:
        self._api_key = api_key or settings.gemini_api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout or settings.cloud_timeout

    def generate(self, model: str, prompt: str) -> str:
        if not self._api_key:
            raise ProviderError("Gemini API key is not configured.")

        try:
            response = requests.post(
                f"{self._base_url}/models/{model}:generateContent",
                params={"key": self._api_key},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ]
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        except requests.RequestException as exc:
            raise ProviderError(
                f"Gemini request failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise ProviderError(
                "Gemini returned invalid JSON."
            ) from exc

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "Invalid Gemini response format."
            ) from exc