"""CLI do AlentoSoft-IA hospitalar."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from .audit import AuditLog
from .core import AlentoAgent
from .llm_skill import LLMPolicySkill
from .marketing_skill import MarketingSkill
from .routing import build_provider
from .skills import internal_policy_checklist


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AlentoSoft-IA hospitalar — protótipo seguro")
    parser.add_argument("--goal", default="Preparar checklist para uma política interna do hospital")
    parser.add_argument("--domain", default="general", choices=["general", "engineering", "clinical", "hr", "finance", "marketing"])
    parser.add_argument("--approve", action="store_true", help="Simula aprovação humana explícita")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Mostra o rascunho gerado sem aprovar nem publicar a tarefa",
    )
    parser.add_argument("--workspace", default="workspaces/demo")
    parser.add_argument("--source-file", type=Path, help="Documento autorizado usado como fonte da skill")
    parser.add_argument(
        "--channel",
        default="instagram",
        choices=["instagram", "whatsapp", "blog", "linkedin", "facebook", "youtube", "paid_ads"],
        help="Canal único para a execução da skill de marketing",
    )
    parser.add_argument(
        "--provider",
        choices=["demo", "ollama", "openai", "openrouter", "hybrid"],
        default=os.getenv("ALENTO_PROVIDER", "demo"),
        help="Provider local, cloud explícito ou roteamento híbrido fail-closed",
    )
    parser.add_argument(
        "--model",
        help="Modelo explícito; caso omitido, usa MODEL_NAME, OPENAI_MODEL ou OPENROUTER_MODEL",
    )
    return parser


def run_task(
    *,
    goal: str,
    domain: str,
    provider_name: str,
    context: dict,
    workspace: str = "workspaces/demo",
    approve: bool = False,
    preview: bool = False,
    model: str | None = None,
) -> dict:
    """Executa uma tarefa a partir de contexto fornecido pelo agente.

    O contexto pode ser criado por ``clickup_context.build_marketing_context``
    depois de o agente consultar o MCP. Não há ficheiro intermediário nem
    necessidade de o utilizador copiar dados do ClickUp.
    """
    root = Path(workspace)
    root.mkdir(parents=True, exist_ok=True)
    audit = AuditLog(root / "audit.sqlite3")
    skill = internal_policy_checklist
    provider = None
    if provider_name != "demo":
        routing_context = {
            "source_name": context.get("source_name", ""),
            "source_text": context.get("source_text", ""),
        }
        provider = build_provider(
            provider_name,
            domain,
            routing_context,
            model=model,
        )
        skill = MarketingSkill(provider) if domain == "marketing" else LLMPolicySkill(provider)
    agent = AlentoAgent(audit_log=audit, skill=skill)
    task = agent.create_task(goal=goal, domain=domain, context=context)
    started = time.perf_counter()
    task = agent.run(task, approval=approve)
    elapsed_seconds = round(time.perf_counter() - started, 3)

    response = {
        "task_id": task.id,
        "status": task.status.value,
        "domain": task.domain,
        "steps": [
            {
                "id": step.id,
                "title": step.title,
                "status": step.status,
                "validation": step.validation,
            }
            for step in task.steps
        ],
        "output": task.output,
        "errors": task.errors,
        "elapsed_seconds": elapsed_seconds,
        "provider": getattr(provider, "name", provider_name),
        "controls_loaded": any(
            key in context
            for key in (
                "institutional_metadata",
                "public_identification",
                "render_plan",
                "approval_gates",
            )
        ),
    }
    if preview:
        response["preview"] = next(
            (step.result for step in task.steps if step.id == "draft"),
            None,
        )
    return response


def main() -> None:
    args = build_parser().parse_args()
    context = {"channel": args.channel}
    if args.source_file:
        context.update(
            {
                "source_name": args.source_file.name,
                "source_text": args.source_file.read_text(encoding="utf-8"),
            }
        )
    response = run_task(
        goal=args.goal,
        domain=args.domain,
        provider_name=args.provider,
        context=context,
        workspace=args.workspace,
        approve=args.approve,
        preview=args.preview,
        model=args.model,
    )
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
