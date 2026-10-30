"""Minimal client for Ollama's hosted chat API.

The API key is read from the OLLAMA_API_KEY environment variable and is never stored in code or
files. Set it in the shell for the session that runs the evaluation; do not commit it.

Only the standard library is used (urllib), so the client adds no dependency.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

BASE_URL = "https://ollama.com/api"
DEFAULT_MODEL = "gpt-oss:20b"
MAX_RETRIES = 4


class LLMError(RuntimeError):
    """Raised when the hosted model cannot answer."""


@dataclass(frozen=True)
class ChatResult:
    text: str
    tokens_out: int


class OllamaClient:
    def __init__(self, model: str = DEFAULT_MODEL, timeout: float = 180.0) -> None:
        key = os.environ.get("OLLAMA_API_KEY")
        if not key:
            raise LLMError("OLLAMA_API_KEY is not set in the environment")
        self._key = key
        self.model = model
        self.timeout = timeout

    def chat(self, system: str, user: str, temperature: float = 0.0) -> ChatResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        data = self._post("/chat", payload)
        message = data.get("message", {})
        return ChatResult(
            text=str(message.get("content", "")).strip(),
            tokens_out=int(data.get("eval_count", 0)),
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(MAX_RETRIES):
            request = urllib.request.Request(
                BASE_URL + path,
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
                    return data
            except urllib.error.HTTPError as exc:
                # 429 and 5xx are transient: back off and retry. Anything else is a real error.
                if exc.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
                    time.sleep(2**attempt)
                    continue
                raise LLMError(f"hosted model returned HTTP {exc.code}") from exc
            except urllib.error.URLError as exc:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2**attempt)
                    continue
                raise LLMError(f"could not reach the hosted model: {exc.reason}") from exc
        raise LLMError("hosted model: retries exhausted")
