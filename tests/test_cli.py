import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_controls_file_is_loaded_from_private_json(self):
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            controls = Path(directory) / "clickup-controls.json"
            controls.write_text(
                json.dumps(
                    {
                        "institutional_metadata": {
                            "service_name": "PA institucional",
                            "verified": True,
                        },
                        "public_identification": {
                            "status": "pending_validation",
                            "must_be_rendered": False,
                        },
                        "render_plan": {"caption_metadata_fields": []},
                        "approval_gates": {"clinical": "pending"},
                    }
                ),
                encoding="utf-8",
            )
            controls.chmod(0o600)
            workspace = Path(directory) / "workspace"
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
                    "Teste de controles ClickUp",
                    "--workspace",
                    str(workspace),
                    "--controls-file",
                    str(controls),
                ],
                cwd=project_root,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            result = json.loads(completed.stdout)

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
