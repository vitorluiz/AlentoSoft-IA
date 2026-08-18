import tempfile
import unittest
from pathlib import Path

from alento_soft_ia.memory import DomainMemory
from alento_soft_ia.policy import get_policy
from alento_soft_ia.tools import ToolRegistry
from alento_soft_ia.workspace import Workspace


class SecurityTests(unittest.TestCase):
    def test_workspace_blocks_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace")
            with self.assertRaises(PermissionError):
                workspace.write_text("../outside.txt", "blocked")

    def test_clinical_global_memory_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = DomainMemory(Path(directory) / "memory.sqlite3")
            with self.assertRaises(PermissionError):
                memory.put("clinical", "global:patient_facts", "blocked")

    def test_tool_policy_blocks_external_domain_tool(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = ToolRegistry(Workspace(directory))
            with self.assertRaises(PermissionError):
                registry.call("clinical", "shell", command="echo blocked")

    def test_sensitive_policy_requires_approval(self) -> None:
        self.assertTrue(get_policy("clinical").human_approval_required)
        self.assertFalse(get_policy("clinical").can_write_external_system)


if __name__ == "__main__":
    unittest.main()
