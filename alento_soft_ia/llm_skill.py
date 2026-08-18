"""Skill administrativa baseada em LLM, com saída JSON verificável."""

from __future__ import annotations

from typing import Any, Dict

from .core import Task


OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "description": {"type": "string"},
                    "responsible": {"type": "string"},
                    "status": {"type": "string", "enum": ["pending", "done", "blocked"]},
                },
                "required": ["id", "description", "responsible", "status"],
                "additionalProperties": False,
            },
        },
        "sources": {"type": "array", "items": {"type": "string"}},
        "human_review_required": {"type": "boolean"},
        "status": {"type": "string", "enum": ["draft", "ready_for_review"]},
    },
    "required": ["summary", "items", "sources", "human_review_required", "status"],
    "additionalProperties": False,
}


class LLMPolicySkill:
    def __init__(self, provider: Any):
        self.provider = provider

    def __call__(self, task: Task) -> Dict[str, Any]:
        if not self.provider.configured:
            raise RuntimeError("Configure o endpoint do modelo antes de usar LLMPolicySkill.")
        messages = [
            {
                "role": "system",
                "content": (
                    "Você é uma skill administrativa conservadora do AlentoSoft-IA. "
                    "Responda somente no schema JSON recebido. Não invente fatos, políticas, "
                    "prazos ou responsáveis. Se uma informação não estiver disponível, use "
                    "'Não informado' e marque status como 'blocked'. Não acesse dados externos. "
                    "Defina human_review_required como true e status como 'ready_for_review'."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Domínio: {task.domain}\n"
                    f"Objetivo: {task.goal}\n"
                    "Crie um checklist administrativo com itens numerados, responsável e status."
                ),
            },
        ]
        result = self.provider.chat_json(messages, OUTPUT_SCHEMA)
        result["human_review_required"] = True
        if result.get("status") not in {"draft", "ready_for_review"}:
            result["status"] = "ready_for_review"
        return result
