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
            "Identificar objetivo e responsável.",
            "Reunir somente documentos autorizados.",
            "Validar campos obrigatórios e prazos.",
            "Registar revisão humana antes da publicação.",
        ],
        "sources": [],
        "human_review_required": task.domain != "general",
        "status": "draft",
    }
