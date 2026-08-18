"""Skill baseada em LLM, opcional e com saída JSON estruturada."""

from __future__ import annotations

from typing import Any, Dict

from .core import Task
from .provider import OpenAICompatibleProvider


OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "items": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}},
        "human_review_required": {"type": "boolean"},
        "status": {"type": "string"},
    },
    "required": ["summary", "items", "sources", "human_review_required", "status"],
    "additionalProperties": False,
}


class LLMPolicySkill:
    def __init__(self, provider: OpenAICompatibleProvider):
        self.provider = provider

    def __call__(self, task: Task) -> Dict[str, Any]:
        if not self.provider.configured:
            raise RuntimeError("Configure o endpoint do modelo antes de usar LLMPolicySkill.")
        messages = [
            {
                "role": "system",
                "content": (
                    "Você é uma skill administrativa conservadora. Produza somente JSON válido. "
                    "Não invente fatos, não acesse dados externos e marque sempre quando houver revisão humana."
                ),
            },
            {
                "role": "user",
                "content": f"Domínio: {task.domain}\nObjetivo: {task.goal}",
            },
        ]
        result = self.provider.chat_json(messages, OUTPUT_SCHEMA)
        result["human_review_required"] = bool(result.get("human_review_required", True))
        return result
