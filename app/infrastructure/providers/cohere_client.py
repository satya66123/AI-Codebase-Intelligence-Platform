from typing import Any

import requests

from app.config import settings
from app.core import ProviderError


class CohereClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.cohere.com/v2",
        timeout: int | None = None,
    ) -> None:
        self._api_key = api_key or settings.cohere_api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout or settings.cloud_timeout

    def generate(self, model: str, prompt: str) -> str:
        if not self._api_key:
            raise ProviderError("Cohere API key is not configured.")

        try:
            response = requests.post(
                f"{self._base_url}/chat",
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
                f"Cohere request failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise ProviderError(
                "Cohere returned invalid JSON."
            ) from exc

        try:
            return data["message"]["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "Invalid Cohere response format."
            ) from exc