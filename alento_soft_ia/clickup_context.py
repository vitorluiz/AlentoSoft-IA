"""Adaptador local para tarefas recebidas do MCP do ClickUp.

O MCP é usado pelo agente orquestrador. Este módulo não chama o ClickUp nem
mantém cópia manual em JSON: recebe os objetos retornados pelo conector,
normaliza controles localmente e remove dados institucionais/profissionais da
fonte que poderá ser enviada a um provider cloud.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from .marketing_skill import INSTITUTIONAL_FIELDS


_CONTROL_HEADINGS = (
    "PORTA-VOZ E AUTORIDADE DA PEÇA",
    "NOTA INSTITUCIONAL OBRIGATÓRIA PARA A LEGENDA",
)
_LOCAL_ONLY_PREFIXES = (
    "Base factual autorizada:",
    "CTA:",
    "Risco editorial:",
    "Aprovações necessárias:",
)
_CHANNELS = {
    "instagram": "instagram",
    "whatsapp": "whatsapp",
    "blog": "blog",
    "linkedin": "linkedin",
    "facebook": "facebook",
    "youtube": "youtube",
    "paid ads": "paid_ads",
    "paid_ads": "paid_ads",
}


def _task_text(task: Mapping[str, Any] | None) -> str:
    if not task:
        return ""
    return str(
        task.get("markdown_description")
        or task.get("text_content")
        or task.get("description")
        or ""
    ).strip()


def _task_id(task: Mapping[str, Any] | None) -> str:
    return str((task or {}).get("id") or "unknown").strip()


def _label_value(text: str, label: str) -> str:
    pattern = rf"(?im)^\s*{re.escape(label)}\s*:\s*(.+?)\s*$"
    match = re.search(pattern, text)
    return match.group(1).strip().rstrip(" .;") if match else ""


def _custom_field_values(task: Mapping[str, Any] | None) -> dict[str, Any]:
    """Indexa campos personalizados quando o conector os devolver."""
    if not task:
        return {}
    values: dict[str, Any] = {}
    raw_fields = task.get("custom_fields") or []
    if isinstance(raw_fields, Mapping):
        return dict(raw_fields)
    if not isinstance(raw_fields, list):
        return values
    for field in raw_fields:
        if not isinstance(field, Mapping):
            continue
        name = str(field.get("name") or field.get("id") or "").strip()
        if not name:
            continue
        value = field.get("value")
        if value is None:
            value = field.get("value_text")
        if isinstance(value, str):
            candidate = value.strip()
            if candidate.startswith(("{", "[")):
                try:
                    value = json.loads(candidate)
                except json.JSONDecodeError:
                    pass
        values[name] = value
    return values


def _custom_group(
    task: Mapping[str, Any] | None,
    group_name: str,
) -> dict[str, Any]:
    values = _custom_field_values(task)
    direct = task.get(group_name) if task else None
    if isinstance(direct, Mapping):
        return dict(direct)
    for name, value in values.items():
        normalized = re.sub(r"[^a-z0-9_]", "_", name.lower())
        if normalized == group_name and isinstance(value, Mapping):
            return dict(value)
    return {}


def _channel_from_task(task: Mapping[str, Any]) -> str:
    explicit = _label_value(_task_text(task), "Canal").lower()
    if explicit in _CHANNELS:
        return _CHANNELS[explicit]
    name = str(task.get("name") or "").lower()
    match = re.search(r"\[([^|]+)\s*\|", name)
    if match:
        candidate = match.group(1).strip()
        if candidate in _CHANNELS:
            return _CHANNELS[candidate]
    return "instagram"


def _safe_source_text(text: str) -> str:
    """Conserva apenas o briefing editorial não sensível para o provider."""
    safe_lines: list[str] = []
    for line in text.splitlines():
        normalized = line.strip()
        if any(normalized.startswith(heading) for heading in _CONTROL_HEADINGS):
            break
        if any(normalized.startswith(prefix) for prefix in _LOCAL_ONLY_PREFIXES):
            continue
        if normalized:
            safe_lines.append(normalized)
    return "\n".join(safe_lines).strip()


def _institutional_metadata(
    editorial_text: str,
    professional_text: str,
    editorial_task_id: str,
) -> dict[str, Any]:
    text = "\n".join(part for part in (editorial_text, professional_text) if part)
    phone_match = re.search(r"\(\d{2}\)\s*\d{4,5}-\d{4}", text)
    cnes_match = re.search(r"\bCNES\s*([0-9]{5,})", text, re.IGNORECASE)
    sanitary_match = re.search(
        r"\bSES\s*(?:n[º°o]?\s*)?([0-9][0-9.]+)",
        text,
        re.IGNORECASE,
    )
    service_name = "PA Psiquiátrico" if re.search("PA Psiquiátrico", text, re.IGNORECASE) else ""
    service_availability = "24 horas" if re.search("24 horas", text, re.IGNORECASE) else ""
    institution = _label_value(text, "Estabelecimento")
    if not institution and re.search("Granjimmy Hospital Psiquiátrico", text, re.IGNORECASE):
        institution = "Granjimmy Hospital Psiquiátrico"
    metadata = {
        "service_name": service_name,
        "service_availability": service_availability,
        "contact_phone": phone_match.group(0) if phone_match else "",
        "institution_name": institution,
        "cnes": cnes_match.group(1) if cnes_match else "",
        "sanitary_registration": sanitary_match.group(1).rstrip(" .;") if sanitary_match else "",
        "source_reference": f"ClickUp task {_task_id({'id': editorial_task_id})}",
        "verified": bool(re.search("metadados institucionais.*verificados", text, re.IGNORECASE)),
        "verified_at": "",
        "verified_by": "",
    }
    return metadata


def _public_identification(
    professional_task: Mapping[str, Any] | None,
) -> dict[str, Any]:
    text = _task_text(professional_task)
    name = _label_value(text, "Nome informado")
    role = _label_value(text, "Função/formação informada")
    specialty = _label_value(text, "Especialização informada")
    if specialty and specialty.lower() not in role.lower():
        role = f"{role} / {specialty}" if role else specialty
    council = _label_value(text, "Conselho profissional")
    number = _label_value(text, "Número informado")
    rqe = _label_value(text, "RQE informado")
    pending = bool(
        re.search("pendente|não utilizar publicamente|não inserir nome", text, re.IGNORECASE)
    )
    validated = bool(
        re.search("estado editorial:\s*validado|autorização.*aprovada", text, re.IGNORECASE)
    ) and not pending
    status = "validated" if validated else "pending_validation"
    must_be_rendered = bool(
        re.search("identificação.*(?:deve|pode) ser renderizada|renderizar.*identificação", text, re.IGNORECASE)
    ) and not pending
    return {
        "status": status,
        "must_be_rendered": must_be_rendered,
        "professional_id": _task_id(professional_task),
        "name": name,
        "role": role,
        "council": council,
        "crm": number if "crm" in council.lower() else "",
        "rqe": rqe,
        "source_reference": f"ClickUp task {_task_id(professional_task)}",
        "authorization_required": True,
        "validation_required": status != "not_required",
    }


def _approval_gates(editorial_text: str, professional_text: str) -> dict[str, str]:
    text = f"{editorial_text}\n{professional_text}"
    gates = {
        "clinical": "pending",
        "institutional": "pending",
        "marketing": "pending",
        "public_identification": "pending",
    }
    if re.search("marketing\s*\+\s*clínico", text, re.IGNORECASE):
        gates["clinical"] = "pending"
        gates["marketing"] = "pending"
    return gates


def build_marketing_context(
    editorial_task: Mapping[str, Any],
    professional_task: Mapping[str, Any] | None = None,
    institutional_task: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Transforma resultados MCP em contexto seguro para ``AlentoAgent``.

    O texto enviado para a geração contém somente a parte editorial sanitizada.
    Os controles permanecem no contexto local e são anexados pela
    ``MarketingSkill`` depois da resposta do provider.
    """
    editorial_text = _task_text(editorial_task)
    professional_text = _task_text(professional_task)
    institutional_text = _task_text(institutional_task)
    full_control_text = "\n".join(
        part for part in (editorial_text, professional_text, institutional_text) if part
    )
    institutional = _institutional_metadata(
        full_control_text,
        professional_text,
        _task_id(editorial_task),
    )
    institutional.update(_custom_group(editorial_task, "institutional_metadata"))
    institutional.update(_custom_group(institutional_task, "institutional_metadata"))
    public_identification = _public_identification(professional_task)
    public_identification.update(_custom_group(professional_task, "public_identification"))
    render_plan = {
        "design_copy_item_ids": [],
        "caption_metadata_fields": INSTITUTIONAL_FIELDS
        if "NOTA INSTITUCIONAL OBRIGATÓRIA" in full_control_text
        else [],
        "internal_only_metadata_fields": [
            "source_reference",
            "verified",
            "verified_at",
            "verified_by",
        ],
    }
    render_plan.update(_custom_group(editorial_task, "render_plan"))
    approval_gates = _approval_gates(editorial_text, professional_text)
    approval_gates.update(_custom_group(editorial_task, "approval_gates"))
    goal = _label_value(editorial_text, "Objetivo")
    editorial_id = _task_id(editorial_task)
    return {
        "source_name": f"clickup://task/{editorial_id}",
        "source_kind": "clickup_mcp",
        "mcp_source_verified": True,
        "source_text": _safe_source_text(editorial_text),
        "channel": _channel_from_task(editorial_task),
        "institutional_metadata": institutional,
        "public_identification": public_identification,
        "render_plan": render_plan,
        "approval_gates": approval_gates,
        "clickup_task_id": _task_id(editorial_task),
        "clickup_professional_task_id": _task_id(professional_task),
        "clickup_institutional_task_id": _task_id(institutional_task),
        "clickup_goal": goal,
    }
