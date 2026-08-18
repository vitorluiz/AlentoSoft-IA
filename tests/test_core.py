import tempfile
import unittest
from pathlib import Path

from alento_soft_ia.audit import AuditLog
from alento_soft_ia.core import AlentoAgent, TaskStatus
from alento_soft_ia.skills import internal_policy_checklist


class CoreTests(unittest.TestCase):
    def make_agent(self, tmp_path: Path) -> AlentoAgent:
        return AlentoAgent(AuditLog(tmp_path / "audit.sqlite3"), internal_policy_checklist)

    def test_general_task_completes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            agent = self.make_agent(Path(directory))
            task = agent.create_task("Criar checklist de onboarding", "general")
            result = agent.run(task)
            self.assertEqual(result.status, TaskStatus.COMPLETED)
            self.assertEqual(result.output["status"], "draft")
            self.assertGreaterEqual(len(agent.audit.list_events()), 3)

    def test_clinical_task_waits_for_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            agent = self.make_agent(Path(directory))
            task = agent.create_task("Preparar rascunho de evolução", "clinical")
            result = agent.run(task)
            self.assertEqual(result.status, TaskStatus.WAITING_APPROVAL)

    def test_clinical_task_completes_after_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            agent = self.make_agent(Path(directory))
            task = agent.create_task("Preparar rascunho de evolução", "clinical")
            result = agent.run(task, approval=True)
            self.assertEqual(result.status, TaskStatus.COMPLETED)
            self.assertTrue(result.output["human_review_required"])


if __name__ == "__main__":
    unittest.main()
