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
            errors.append("A saída deve ser um objeto estruturado.")
        if not result.get("summary"):
            errors.append("A saída não contém resumo.")
        if task.domain in self.SENSITIVE_DOMAINS and not result.get("human_review_required", False):
            errors.append("Domínio sensível exige revisão humana explícita.")
        return {"ok": not errors, "errors": errors}


class AlentoAgent:
    """Orquestrador mínimo do AlentoSoft-IA para planear-validar-aprovar."""

    def __init__(self, audit_log: Any, skill: Callable[[Task], Dict[str, Any]]):
        self.audit = audit_log
        self.skill = skill
        self.planner = Planner()
        self.validator = Validator()

    def create_task(self, goal: str, domain: str) -> Task:
        task = Task(id=str(uuid4()), goal=goal, domain=domain)
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
                    if task.domain in Validator.SENSITIVE_DOMAINS and not approval:
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
