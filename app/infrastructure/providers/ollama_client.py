from typing import Any

import requests

from app.config import settings
from app.core import ProviderError


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self._base_url = (
            base_url or settings.ollama_base_url
        ).rstrip("/")
        self._timeout = timeout or settings.ollama_timeout

    def generate(
        self,
        model: str,
        prompt: str,
    ) -> str:
        try:
            response = requests.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()

            data: dict[str, Any] = response.json()

        except requests.RequestException as exc:
            raise ProviderError(
                f"Ollama request failed: {exc}"
            ) from exc

        except ValueError as exc:
            raise ProviderError(
                "Ollama returned invalid JSON."
            ) from exc

        response_text = data.get("response")

        if not isinstance(response_text, str):
            raise ProviderError(
                "Ollama response does not contain valid text."
            )

        return response_text