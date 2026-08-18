"""Valida a saída JSON da CLI do AlentoSoft-IA."""

from __future__ import annotations

import json
import sys
from pathlib import Path


payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["status"] in {"completed", "waiting_approval", "failed"}
assert "elapsed_seconds" in payload
assert "provider" in payload
print(f"status={payload['status']} provider={payload['provider']} elapsed={payload['elapsed_seconds']}s")
