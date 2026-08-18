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
from .provider import OllamaProvider
from .skills import internal_policy_checklist


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AlentoSoft-IA hospitalar — protótipo seguro")
    parser.add_argument("--goal", default="Preparar checklist para uma política interna do hospital")
    parser.add_argument("--domain", default="general", choices=["general", "engineering", "clinical", "hr", "finance"])
    parser.add_argument("--approve", action="store_true", help="Simula aprovação humana explícita")
    parser.add_argument("--workspace", default="workspaces/demo")
    parser.add_argument("--source-file", type=Path, help="Documento autorizado usado como fonte da skill")
    parser.add_argument(
        "--provider",
        choices=["demo", "ollama"],
        default=os.getenv("ALENTO_PROVIDER", "demo"),
        help="Usa a skill determinística ou o endpoint Ollama local",
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
        }
    if args.provider == "ollama":
        skill = LLMPolicySkill(OllamaProvider())
    agent = AlentoAgent(audit_log=audit, skill=skill)
    task = agent.create_task(goal=args.goal, domain=args.domain, context=context)
    started = time.perf_counter()
    task = agent.run(task, approval=args.approve)
    elapsed_seconds = round(time.perf_counter() - started, 3)

    print(json.dumps({
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
        "provider": args.provider,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
