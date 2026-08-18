"""Adaptadores de modelos locais para o AlentoSoft-IA."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


def _post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    import urllib.request

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


class OllamaProvider:
    """Cliente para a API nativa do Ollama.

    A API nativa é usada para controlar explicitamente `think`, `format` e
    `keep_alive`, que são importantes para o Qwen3.5 em máquinas sem GPU.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        think: Optional[bool] = None,
        keep_alive: Optional[str] = None,
    ):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api")).rstrip("/")
        self.model = model or os.getenv("MODEL_NAME", "qwen3.5:4b-q4_K_M")
        raw_think = os.getenv("OLLAMA_THINK", "false") if think is None else str(think).lower()
        self.think = raw_think in {"1", "true", "yes", "on"}
        self.keep_alive = keep_alive or os.getenv("OLLAMA_KEEP_ALIVE", "10m")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def chat_json(self, messages: List[Dict[str, str]], schema: Dict[str, Any]) -> Dict[str, Any]:
        if not self.configured:
            raise RuntimeError("Modelo Ollama não configurado. Defina MODEL_NAME.")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": self.think,
            "format": schema,
            "keep_alive": self.keep_alive,
            "options": {"temperature": 0},
        }
        body = _post_json(f"{self.base_url}/chat", payload)
        content = body.get("message", {}).get("content", "")
        if not content:
            raise RuntimeError("Ollama devolveu uma resposta sem conteúdo.")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama não devolveu JSON válido.") from exc


class OpenAICompatibleProvider:
    """Cliente opcional para endpoints compatíveis com OpenAI, como vLLM."""

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
        body = _post_json(
            f"{self.base_url}/chat/completions",
            payload,
            {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None,
        )
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
