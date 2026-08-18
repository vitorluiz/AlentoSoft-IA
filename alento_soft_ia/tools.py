"""Ferramentas seguras do MVP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from .policy import get_policy
from .workspace import Workspace


@dataclass
class Tool:
    name: str
    handler: Callable[..., Any]


class ToolRegistry:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.tools: Dict[str, Tool] = {
            "read_workspace": Tool("read_workspace", self._read_workspace),
            "write_workspace": Tool("write_workspace", self._write_workspace),
            "list_workspace": Tool("list_workspace", self._list_workspace),
        }

    def call(self, domain: str, name: str, **kwargs: Any) -> Any:
        policy = get_policy(domain)
        if name not in policy.allowed_tools:
            raise PermissionError(f"Ferramenta '{name}' não autorizada no domínio '{domain}'")
        if name not in self.tools:
            raise KeyError(f"Ferramenta desconhecida: {name}")
        return self.tools[name].handler(**kwargs)

    def _read_workspace(self, path: str) -> Dict[str, str]:
        return {"path": path, "content": self.workspace.read_text(path)}

    def _write_workspace(self, path: str, content: str) -> Dict[str, str]:
        self.workspace.write_text(path, content)
        return {"path": path, "status": "written"}

    def _list_workspace(self) -> Dict[str, list[str]]:
        return {"files": self.workspace.list_files()}
