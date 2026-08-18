"""Núcleo mínimo do AlentoSoft-IA hospitalar.

O módulo é deliberadamente conservador: sem aprovação explícita, o agente pode
planear e validar, mas não publica dados nem executa ações irreversíveis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


class TaskStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Step:
    id: str
    title: str
    kind: str
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None


@dataclass
class Task:
    id: str
    goal: str
    domain: str
    status: TaskStatus = TaskStatus.PLANNED
    steps: List[Step] = field(default_factory=list)
    output: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


class Planner:
    """Planeador determinístico para o primeiro protótipo.

    A lógica de planeamento pode ser substituída por um LLM depois, mas o
    contrato de saída permanece explícito e auditável.
    """

    def build_plan(self, goal: str, domain: str) -> List[Step]:
        steps = [
            ("understand", "Clarificar objetivo e domínio", "analysis"),
            ("gather", "Reunir dados autorizados", "retrieval"),
            ("draft", "Produzir rascunho estruturado", "generation"),
            ("validate", "Validar formato, permissões e riscos", "validation"),
            ("approve", "Aguardar aprovação humana quando necessário", "approval"),
        ]
        return [Step(id=code, title=title, kind=kind) for code, title, kind in steps]


class Validator:
    """Validações mínimas e independentes do modelo."""

    SENSITIVE_DOMAINS = {"clinical", "hr", "finance", "accounting"}

    def validate(self, task: Task, result: Dict[str, Any]) -> Dict[str, Any]:
        errors: List[str] = []
        if not isinstance(result, dict):
            return {"ok": False, "errors": ["A saída deve ser um objeto estruturado."]}

        required = {"summary", "items", "sources", "missing_information", "human_review_required", "status"}
        missing = sorted(required - set(result))
        if missing:
            errors.append(f"Campos obrigatórios ausentes: {', '.join(missing)}.")
        if not isinstance(result.get("summary"), str) or not result.get("summary", "").strip():
            errors.append("A saída não contém resumo textual.")
        if not isinstance(result.get("items"), list) or not result.get("items"):
            errors.append("A saída deve conter pelo menos um item.")
        else:
            for index, item in enumerate(result["items"], start=1):
                if not isinstance(item, dict):
                    errors.append(f"O item {index} não é um objeto estruturado.")
                    continue
                for field in ("id", "description", "responsible", "status", "source_section", "evidence"):
                    if field not in item or not str(item[field]).strip():
                        errors.append(f"O item {index} não contém '{field}'.")
        if not isinstance(result.get("sources"), list):
            errors.append("O campo sources deve ser uma lista.")
        if not isinstance(result.get("missing_information"), list):
            errors.append("O campo missing_information deve ser uma lista.")
        if not isinstance(result.get("human_review_required"), bool):
            errors.append("human_review_required deve ser booleano.")
        if result.get("status") not in {"draft", "ready_for_review"}:
            errors.append("status deve ser 'draft' ou 'ready_for_review'.")
        if task.domain in self.SENSITIVE_DOMAINS and not result.get("human_review_required", False):
            errors.append("Domínio sensível exige revisão humana explícita.")
        blocked_items = [item for item in result.get("items", []) if isinstance(item, dict) and item.get("status") == "blocked"]
        return {
            "ok": not errors,
            "errors": errors,
            "blocked": bool(blocked_items),
            "requires_approval": bool(result.get("human_review_required", False)),
        }


class AlentoAgent:
    """Orquestrador mínimo do AlentoSoft-IA para planear-validar-aprovar."""

    def __init__(self, audit_log: Any, skill: Callable[[Task], Dict[str, Any]]):
        self.audit = audit_log
        self.skill = skill
        self.planner = Planner()
        self.validator = Validator()

    def create_task(self, goal: str, domain: str, context: Optional[Dict[str, Any]] = None) -> Task:
        task = Task(id=str(uuid4()), goal=goal, domain=domain, context=context or {})
        task.steps = self.planner.build_plan(goal, domain)
        self.audit.write("task_created", {"task_id": task.id, "domain": domain, "goal": goal})
        return task

    def run(self, task: Task, approval: bool = False) -> Task:
        task.status = TaskStatus.RUNNING
        self.audit.write("task_started", {"task_id": task.id})
        try:
            for step in task.steps:
                step.status = "running"
                if step.kind == "approval":
                    draft_output = task.steps[2].result or {}
                    needs_approval = task.domain in Validator.SENSITIVE_DOMAINS or bool(
                        draft_output.get("human_review_required", False)
                    )
                    if needs_approval and not approval:
                        step.status = "waiting_approval"
                        task.status = TaskStatus.WAITING_APPROVAL
                        self.audit.write("approval_required", {"task_id": task.id})
                        return task
                    step.status = "completed"
                    continue
                if step.kind == "generation":
                    step.result = self.skill(task)
                    step.status = "completed"
                elif step.kind == "validation":
                    validation = self.validator.validate(task, task.steps[2].result or {})
                    step.validation = validation
                    if not validation["ok"]:
                        task.errors.extend(validation["errors"])
                        task.status = TaskStatus.FAILED
                        step.status = "failed"
                        self.audit.write("task_failed", {"task_id": task.id, "errors": task.errors})
                        return task
                    if validation.get("blocked"):
                        task.status = TaskStatus.BLOCKED
                        step.status = "blocked"
                        self.audit.write("task_blocked", {"task_id": task.id})
                        return task
                    step.status = "completed"
                else:
                    step.status = "completed"
            task.output = task.steps[2].result
            task.status = TaskStatus.COMPLETED
            self.audit.write("task_completed", {"task_id": task.id})
            return task
        except Exception as exc:  # pragma: no cover - defensive boundary
            task.status = TaskStatus.FAILED
            task.errors.append(str(exc))
            self.audit.write("task_failed", {"task_id": task.id, "errors": task.errors})
            return task
