"""CLI do AlentoSoft-IA hospitalar."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import AuditLog
from .core import AlentoAgent
from .skills import internal_policy_checklist


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AlentoSoft-IA hospitalar — protótipo seguro")
    parser.add_argument("--goal", default="Preparar checklist para uma política interna do hospital")
    parser.add_argument("--domain", default="general", choices=["general", "engineering", "clinical", "hr", "finance"])
    parser.add_argument("--approve", action="store_true", help="Simula aprovação humana explícita")
    parser.add_argument("--workspace", default="workspaces/demo")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.workspace)
    root.mkdir(parents=True, exist_ok=True)
    audit = AuditLog(root / "audit.sqlite3")
    agent = AlentoAgent(audit_log=audit, skill=internal_policy_checklist)
    task = agent.create_task(goal=args.goal, domain=args.domain)
    task = agent.run(task, approval=args.approve)

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
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
