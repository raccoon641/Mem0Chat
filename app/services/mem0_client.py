from __future__ import annotations

import os
from typing import Any, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings


class Mem0Client:
    def __init__(self) -> None:
        self.api_key = get_settings().mem0_api_key
        self._client = None
        if self.api_key:
            try:
                # Delayed import so environments without the SDK still work
                from mem0 import Client  # type: ignore

                self._client = Client(api_key=self.api_key)
            except Exception:
                self._client = None

    def is_configured(self) -> bool:
        return self._client is not None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def create_memory(self, user_external_id: str, memory_type: str, text: Optional[str] = None, media_path: Optional[str] = None, labels: Optional[list[str]] = None) -> Optional[str]:
        if not self._client:
            return None
        payload: dict[str, Any] = {
            "user_id": user_external_id,
            "type": memory_type,
        }
        if text:
            payload["text"] = text
        if labels:
            payload["labels"] = labels
        if media_path and os.path.exists(media_path):
            payload["media_path"] = media_path
        try:
            result = self._client.memories.create(**payload)  # type: ignore[attr-defined]
            # Assume result contains an id-like field
            mem_id = result.get("id") if isinstance(result, dict) else None
            return mem_id
        except Exception:
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def search(self, user_external_id: str, query: str) -> list[dict[str, Any]]:
        if not self._client:
            return []
        try:
            result = self._client.memories.search(user_id=user_external_id, query=query)  # type: ignore[attr-defined]
            return result if isinstance(result, list) else []
        except Exception:
            return []


mem0_client_singleton = Mem0Client() 