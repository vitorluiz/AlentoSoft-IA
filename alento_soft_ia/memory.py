"""Memória simples por domínio, com separação lógica."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Tuple


class DomainMemory:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    UNIQUE(domain, key)
                )
                """
            )

    def put(self, domain: str, key: str, value: str) -> None:
        if domain == "clinical" and key.startswith("global:"):
            raise PermissionError("Memória clínica global bloqueada")
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO memories(domain, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(domain, key) DO UPDATE SET value=excluded.value",
                (domain, key, value),
            )

    def get(self, domain: str, key: str) -> str | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT value FROM memories WHERE domain = ? AND key = ?",
                (domain, key),
            ).fetchone()
        return row[0] if row else None

    def list_domain(self, domain: str) -> List[Tuple[str, str]]:
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                "SELECT key, value FROM memories WHERE domain = ? ORDER BY key",
                (domain,),
            ).fetchall()
        return [(row[0], row[1]) for row in rows]
