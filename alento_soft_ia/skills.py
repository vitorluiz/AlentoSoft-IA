"""Skills iniciais, intencionalmente não clínicas."""

from __future__ import annotations

from typing import Any, Dict

from .core import Task


def internal_policy_checklist(task: Task) -> Dict[str, Any]:
    """Produz um resultado determinístico para validar a infraestrutura.

    Em produção, esta função será substituída por um adaptador LLM com saída
    JSON estrita e por recuperação de documentos autorizados.
    """

    return {
        "summary": f"Checklist inicial para: {task.goal}",
        "items": [
            {"id": 1, "description": "Identificar objetivo e responsável.", "responsible": "Não informado", "status": "pending", "source_section": "Demonstração do protótipo", "evidence": "Regra determinística do teste."},
            {"id": 2, "description": "Reunir somente documentos autorizados.", "responsible": "Não informado", "status": "pending", "source_section": "Demonstração do protótipo", "evidence": "Regra determinística do teste."},
            {"id": 3, "description": "Validar campos obrigatórios e prazos.", "responsible": "Não informado", "status": "pending", "source_section": "Demonstração do protótipo", "evidence": "Regra determinística do teste."},
            {"id": 4, "description": "Registar revisão humana antes da publicação.", "responsible": "Não informado", "status": "pending", "source_section": "Demonstração do protótipo", "evidence": "Regra determinística do teste."},
        ],
        "sources": ["Demonstração do protótipo"],
        "missing_information": [],
        "human_review_required": task.domain != "general",
        "status": "draft",
    }
