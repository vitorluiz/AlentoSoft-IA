"""Skill de marketing multicanal fundamentada em fontes autorizadas."""

from __future__ import annotations

from typing import Any, Dict

from .core import Task


QUALITY_HINTS = {
    "apairar": "Possível erro ortográfico: considere revisar para 'apoiar'.",
    "publicar-mos": "Possível separação incorreta de palavras: revise a forma verbal.",
    "familias conforme": "Verifique acentuação e concordância na expressão sobre famílias.",
}


def _quality_warnings(result: Dict[str, Any]) -> list[str]:
    """Gera alertas simples de revisão; nunca transforma aviso em bloqueio."""
    warnings: list[str] = []
    for item in result.get("items", []):
        if not isinstance(item, dict):
            continue
        item_id = item.get("id", "?")
        text = " ".join(
            str(item.get(field, "")) for field in ("title", "copy", "cta")
        ).lower()
        for fragment, warning in QUALITY_HINTS.items():
            if fragment in text:
                warnings.append(f"Item {item_id}: {warning}")
    return warnings


MARKETING_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "channel": {
                        "type": "string",
                        "enum": ["instagram", "whatsapp", "blog", "linkedin", "facebook", "youtube", "paid_ads"],
                    },
                    "format": {"type": "string"},
                    "title": {"type": "string"},
                    "copy": {"type": "string"},
                    "cta": {"type": "string"},
                    "status": {"type": "string", "enum": ["draft", "blocked"]},
                    "source_section": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": [
                    "id",
                    "channel",
                    "format",
                    "title",
                    "copy",
                    "cta",
                    "status",
                    "source_section",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },
        "sources": {"type": "array", "items": {"type": "string"}},
        "missing_information": {"type": "array", "items": {"type": "string"}},
        "risk_flags": {"type": "array", "items": {"type": "string"}},
        "human_review_required": {"type": "boolean"},
        "status": {"type": "string", "enum": ["ready_for_review"]},
    },
    "required": [
        "summary",
        "items",
        "sources",
        "missing_information",
        "risk_flags",
        "human_review_required",
        "status",
    ],
    "additionalProperties": False,
}


class MarketingSkill:
    def __init__(self, provider: Any):
        self.provider = provider

    def __call__(self, task: Task) -> Dict[str, Any]:
        if not self.provider.configured:
            raise RuntimeError("Configure o endpoint do modelo antes de usar MarketingSkill.")
        source_text = str(task.context.get("source_text", "")).strip()
        source_name = str(task.context.get("source_name", "fonte não identificada"))
        channel = str(task.context.get("channel", "instagram"))
        if not source_text:
            raise RuntimeError("MarketingSkill exige fontes autorizadas da marca.")

        messages = [
            {
                "role": "system",
                "content": (
                    "Você é a skill de marketing do AlentoSoft-IA para o Granjimmy Hospital Psiquiátrico. "
                    "Responda somente no schema JSON. Use exclusivamente a fonte fornecida e o objetivo do pedido. "
                    "Escreva em português brasileiro. Não invente serviços, convênios, preços, horários, profissionais, "
                    "resultados, depoimentos, casos, dados de pacientes, estatísticas ou requisitos regulatórios. "
                    "Não faça diagnóstico, prescrição, consulta individual ou promessa de cura. "
                    "Não exponha pacientes nem crie conteúdo baseado em casos reais. "
                    "Você pode transformar, resumir e adaptar os fatos autorizados para o formato do canal; o texto final não precisa ser literal. "
                    "Não marque um item como bloqueado apenas porque a fonte não contém a frase pronta, o formato ou o canal pedido. "
                    "Cada item deve indicar canal, formato, CTA, seção da fonte e evidência textual. "
                    "Quando faltarem informações, inclua-as em missing_information. "
                    "Marque o item como blocked somente se o pedido exigir diagnóstico, prescrição, promessa de cura, exposição de paciente, dado não autorizado ou afirmação incompatível com a fonte. "
                    "Use risk_flags para avisos de revisão; um aviso não é bloqueio por si só. "
                    "Todos os conteúdos são rascunhos e human_review_required deve ser true. "
                    "O status da resposta deve ser ready_for_review. Não publique nada e não use ferramentas externas. "
                    f"Crie conteúdo somente para o canal {channel}; não crie peças para outros canais nesta execução."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Domínio: {task.domain}\n"
                    f"Objetivo: {task.goal}\n"
                    f"Canal escolhido: {channel}\n"
                    f"Fonte autorizada: {source_name}\n"
                    "--- INÍCIO DA FONTE ---\n"
                    f"{source_text}\n"
                    "--- FIM DA FONTE ---"
                ),
            },
        ]
        result = self.provider.chat_json(messages, MARKETING_SCHEMA)
        result["human_review_required"] = True
        result["status"] = "ready_for_review"
        result["quality_warnings"] = _quality_warnings(result)
        return result
