import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
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
