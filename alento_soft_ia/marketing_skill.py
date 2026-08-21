"""Skill de marketing multicanal fundamentada em fontes autorizadas."""

from __future__ import annotations

from typing import Any, Dict

from .core import Task


QUALITY_HINTS = {
    "apairar": "Possível erro ortográfico: considere revisar para 'apoiar'.",
    "publicar-mos": "Possível separação incorreta de palavras: revise a forma verbal.",
    "familias conforme": "Verifique acentuação e concordância na expressão sobre famílias.",
}

INSTITUTIONAL_FIELDS = [
    "service_name",
    "service_availability",
    "contact_phone",
    "institution_name",
    "cnes",
    "sanitary_registration",
]


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


def _local_institutional_metadata(task: Task) -> Dict[str, Any]:
    """Normaliza metadados institucionais fora do payload de copy.

    Esses dados são aplicados localmente a partir do contexto controlado. Eles
    não são incluídos nas mensagens enviadas ao LLM, evitando misturar regras
    de renderização com o texto criativo.
    """
    source = task.context.get("institutional_metadata") or {}
    metadata = {
        field: str(source.get(field, "")).strip() for field in INSTITUTIONAL_FIELDS
    }
    metadata["source_reference"] = str(
        source.get("source_reference", "cadastro institucional restrito")
    ).strip()
    metadata["verified"] = bool(source.get("verified", False))
    metadata["verified_at"] = str(source.get("verified_at", "")).strip()
    metadata["verified_by"] = str(source.get("verified_by", "")).strip()
    return metadata


def _local_public_identification(task: Task) -> Dict[str, Any]:
    """Mantém identificação profissional como controle local e bloqueador."""
    source = task.context.get("public_identification") or {}
    status = str(source.get("status", "pending_validation")).strip()
    if status not in {"not_required", "pending_validation", "validated"}:
        status = "pending_validation"
    return {
        "status": status,
        "must_be_rendered": bool(source.get("must_be_rendered", False)),
        "professional_id": str(source.get("professional_id", "")).strip(),
        "name": str(source.get("name", "")).strip(),
        "role": str(source.get("role", "")).strip(),
        "council": str(source.get("council", "")).strip(),
        "crm": str(source.get("crm", "")).strip(),
        "rqe": str(source.get("rqe", "")).strip(),
        "source_reference": str(
            source.get("source_reference", "cadastro interno restrito")
        ).strip(),
        "authorization_required": True,
        "validation_required": status != "not_required",
    }


def _local_render_plan(task: Task, result: Dict[str, Any]) -> Dict[str, Any]:
    """Define o que pode chegar ao designer, à legenda ou ficar interno."""
    requested = task.context.get("render_plan") or {}
    item_ids = [
        item.get("id")
        for item in result.get("items", [])
        if isinstance(item, dict) and isinstance(item.get("id"), int)
    ]
    caption_fields = [
        field for field in requested.get("caption_metadata_fields", [])
        if field in INSTITUTIONAL_FIELDS
    ]
    internal_fields = [
        field
        for field in requested.get(
            "internal_only_metadata_fields",
            ["source_reference", "verified", "verified_at", "verified_by"],
        )
        if isinstance(field, str)
    ]
    return {
        "design_copy_item_ids": item_ids,
        "caption_metadata_fields": caption_fields,
        "internal_only_metadata_fields": internal_fields,
        "do_not_render_in_design": [
            "institutional_metadata",
            "public_identification",
            "source_section",
            "evidence",
            "risk_flags",
            "approval_gates",
        ],
    }


def _local_approval_gates(task: Task) -> Dict[str, Any]:
    """Mantém aprovação clínica/institucional separada da geração de copy."""
    source = task.context.get("approval_gates") or {}
    allowed = {"pending", "approved", "rejected", "not_required"}
    gates = {}
    for name in ("clinical", "institutional", "marketing", "public_identification"):
        value = str(source.get(name, "pending")).strip()
        gates[name] = value if value in allowed else "pending"
    return gates


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
                        "enum": [
                            "instagram",
                            "whatsapp",
                            "blog",
                            "linkedin",
                            "facebook",
                            "youtube",
                            "paid_ads",
                        ],
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
                    f"Crie conteúdo somente para o canal {channel}; não crie peças para outros canais nesta execução. "
                    "O campo copy contém somente texto que pode ser considerado para a peça. "
                    "Não misture metadados institucionais, fontes, evidências, instruções internas ou identificação profissional em copy, title ou cta. "
                    "Esses controles serão aplicados localmente em campos separados após a geração."
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
        result["institutional_metadata"] = _local_institutional_metadata(task)
        result["public_identification"] = _local_public_identification(task)
        result["render_plan"] = _local_render_plan(task, result)
        result["approval_gates"] = _local_approval_gates(task)
        result["quality_warnings"] = _quality_warnings(result)
        return result
