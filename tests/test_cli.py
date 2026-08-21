import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_run_task_accepts_agent_context_without_controls_file(self):
        from alento_soft_ia.main import run_task

        with tempfile.TemporaryDirectory() as workspace:
            result = run_task(
                goal="Teste de controles ClickUp",
                domain="general",
                provider_name="demo",
                context={
                    "channel": "instagram",
                    "institutional_metadata": {"verified": True},
                    "public_identification": {
                        "status": "pending_validation",
                        "must_be_rendered": False,
                    },
                    "render_plan": {},
                    "approval_gates": {"clinical": "pending"},
                },
                workspace=workspace,
            )

        self.assertTrue(result["controls_loaded"])

    def test_preview_includes_draft_without_approval(self):
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as workspace:
            env = {**os.environ, "PYTHONPATH": str(project_root)}
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alento_soft_ia.main",
                    "--provider",
                    "demo",
                    "--domain",
                    "general",
                    "--goal",
                    "Criar checklist de demonstração",
                    "--workspace",
                    workspace,
                    "--preview",
                ],
                cwd=project_root,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            result = json.loads(completed.stdout)

        self.assertEqual(result["status"], "completed")
        self.assertIn("preview", result)
        self.assertIsNotNone(result["preview"])
        self.assertEqual(result["preview"], result["output"])


if __name__ == "__main__":
    unittest.main()
