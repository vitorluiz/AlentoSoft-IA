"""Adaptador opcional para endpoints compatíveis com OpenAI."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


class OpenAICompatibleProvider:
    """Cliente mínimo sem dependência obrigatória do SDK OpenAI.

    A classe só é usada quando MODEL_BASE_URL e MODEL_NAME estão definidos.
    O protótipo continua executável em modo demo sem uma LLM configurada.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = (base_url or os.getenv("MODEL_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("MODEL_API_KEY", "")
        self.model = model or os.getenv("MODEL_NAME", "")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def chat_json(self, messages: List[Dict[str, str]], schema: Dict[str, Any]) -> Dict[str, Any]:
        if not self.configured:
            raise RuntimeError("Modelo não configurado. Defina MODEL_BASE_URL e MODEL_NAME.")

        import urllib.request

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "alento_soft_ia_output",
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
