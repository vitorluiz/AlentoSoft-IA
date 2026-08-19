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


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.workspace)
    root.mkdir(parents=True, exist_ok=True)
    audit = AuditLog(root / "audit.sqlite3")
    skill = internal_policy_checklist
    context = {}
    if args.source_file:
        context = {
            "source_name": args.source_file.name,
            "source_text": args.source_file.read_text(encoding="utf-8"),
            "channel": args.channel,
        }
    provider = None
    if args.provider != "demo":
        provider = build_provider(args.provider, args.domain, context, model=args.model)
        skill = MarketingSkill(provider) if args.domain == "marketing" else LLMPolicySkill(provider)
    agent = AlentoAgent(audit_log=audit, skill=skill)
    task = agent.create_task(goal=args.goal, domain=args.domain, context=context)
    started = time.perf_counter()
    task = agent.run(task, approval=args.approve)
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
        "provider": getattr(provider, "name", args.provider),
    }
    if args.preview:
        response["preview"] = next(
            (step.result for step in task.steps if step.id == "draft"),
            None,
        )
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
