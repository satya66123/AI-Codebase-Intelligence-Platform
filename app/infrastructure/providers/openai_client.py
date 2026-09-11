from typing import Any

import requests

from app.config import settings
from app.core import ProviderError


class OpenAIClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: int | None = None,
    ) -> None:
        self._api_key = api_key or settings.openai_api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout or settings.cloud_timeout

    def generate(self, model: str, prompt: str) -> str:
        if not self._api_key:
            raise ProviderError("OpenAI API key is not configured.")

        try:
            response = requests.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
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
                f"OpenAI request failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise ProviderError(
                "OpenAI returned invalid JSON."
            ) from exc

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "Invalid OpenAI response format."
            ) from exc