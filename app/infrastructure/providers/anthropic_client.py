from typing import Any

import requests

from app.config import settings
from app.core import ProviderError


class AnthropicClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com/v1",
        timeout: int | None = None,
    ) -> None:
        self._api_key = api_key or settings.anthropic_api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout or settings.cloud_timeout

    def generate(self, model: str, prompt: str) -> str:
        if not self._api_key:
            raise ProviderError("Anthropic API key is not configured.")

        try:
            response = requests.post(
                f"{self._base_url}/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        except requests.RequestException as exc:
            raise ProviderError(
                f"Anthropic request failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise ProviderError(
                "Anthropic returned invalid JSON."
            ) from exc

        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "Invalid Anthropic response format."
            ) from exc