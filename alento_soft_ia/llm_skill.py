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
                    "source_section": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": [
                    "id",
                    "description",
                    "responsible",
                    "status",
                    "source_section",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },
        "sources": {"type": "array", "items": {"type": "string"}},
        "missing_information": {"type": "array", "items": {"type": "string"}},
        "human_review_required": {"type": "boolean"},
        "status": {"type": "string", "enum": ["draft", "ready_for_review"]},
    },
    "required": [
        "summary",
        "items",
        "sources",
        "missing_information",
        "human_review_required",
        "status",
    ],
    "additionalProperties": False,
}


class LLMPolicySkill:
    def __init__(self, provider: Any):
        self.provider = provider

    def __call__(self, task: Task) -> Dict[str, Any]:
        if not self.provider.configured:
            raise RuntimeError("Configure o endpoint do modelo antes de usar LLMPolicySkill.")
        source_text = str(task.context.get("source_text", "")).strip()
        source_name = str(task.context.get("source_name", "fonte não identificada"))
        if not source_text:
            raise RuntimeError("A skill fundamentada exige uma fonte autorizada.")
        messages = [
            {
                "role": "system",
                "content": (
                    "Você é uma skill administrativa fundamentada do AlentoSoft-IA. "
                    "Responda somente no schema JSON recebido e use exclusivamente a fonte fornecida. "
                    "Não invente fatos, políticas, prazos, responsáveis, requisitos legais ou sistemas. "
                    "Cada item deve citar a seção da fonte e uma evidência textual curta. "
                    "Se algo não estiver na fonte, não o transforme em requisito: marque como blocked, "
                    "adicione-o em missing_information e escreva 'Não informado na fonte'. "
                    "Mantenha a natureza fictícia do documento. Defina human_review_required como true "
                    "e status como ready_for_review."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Domínio: {task.domain}\n"
                    f"Objetivo: {task.goal}\n"
                    f"Fonte autorizada: {source_name}\n"
                    "--- INÍCIO DA FONTE ---\n"
                    f"{source_text}\n"
                    "--- FIM DA FONTE ---"
                ),
            },
        ]
        result = self.provider.chat_json(messages, OUTPUT_SCHEMA)
        result["human_review_required"] = True
        if result.get("status") not in {"draft", "ready_for_review"}:
            result["status"] = "ready_for_review"
        return result
