import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from alento_soft_ia.policy_watch import FetchResult, PolicyWatch, WatchSource


class PolicyWatchTests(unittest.TestCase):
    def test_first_run_creates_baselines_without_alerts(self):
        sources = (
            WatchSource(
                "google-hours",
                "Google Business Profile",
                "Horários",
                "https://example.test/hours",
                "business_operations",
                "critical",
            ),
        )

        def fetcher(source):
            return FetchResult(
                200,
                "<html><title>Horários</title><script>segredo de script</script><p>Atendimento 24 horas</p></html>",
                "Horários",
            )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            watch = PolicyWatch(root / "watch.sqlite3", root / "reports", sources, fetcher)
            run = watch.run(datetime(2026, 8, 18, tzinfo=timezone.utc))
            report = run.report_path.read_text(encoding="utf-8")

        self.assertEqual(run.changes, ())
        self.assertEqual(run.baselines, ("google-hours",))
        self.assertIn("Nenhuma alteração", report)
        self.assertNotIn("segredo de script", report)

    def test_second_run_detects_change_and_stores_diff(self):
        sources = (
            WatchSource(
                "google-hours",
                "Google Business Profile",
                "Horários",
                "https://example.test/hours",
                "business_operations",
                "critical",
            ),
        )
        versions = ["Atendimento 24 horas", "Atendimento das 8h às 18h"]

        def fetcher(source):
            return FetchResult(200, f"<p>{versions.pop(0)}</p>", "Horários")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            watch = PolicyWatch(root / "watch.sqlite3", root / "reports", sources, fetcher)
            first = watch.run(datetime(2026, 8, 18, tzinfo=timezone.utc))
            second = watch.run(datetime(2026, 8, 25, tzinfo=timezone.utc))
            report = second.report_path.read_text(encoding="utf-8")

        self.assertEqual(first.changes, ())
        self.assertEqual(len(second.changes), 1)
        self.assertEqual(second.changes[0].severity, "critical")
        self.assertIn("Atendimento 24 horas", report)
        self.assertIn("Atendimento das 8h às 18h", report)
        self.assertIn("[CRITICAL] Google Business Profile", report)

    def test_fetch_error_is_recorded_without_fake_change(self):
        sources = (
            WatchSource(
                "linkedin",
                "LinkedIn",
                "Ajuda",
                "https://example.test/linkedin",
                "platform_help",
                "important",
            ),
        )

        def fetcher(source):
            return FetchResult(503, "", error="HTTP 503")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = PolicyWatch(root / "watch.sqlite3", root / "reports", sources, fetcher).run()

        self.assertEqual(run.changes, ())
        self.assertEqual(run.errors, ("Ajuda: HTTP 503",))


    def test_partial_run_warns_when_one_source_fails(self):
        sources = (
            WatchSource("ok", "Meta", "Fonte OK", "https://example.test/ok", "help", "important"),
            WatchSource("bad", "Google", "Fonte lenta", "https://example.test/bad", "help", "critical"),
        )
        calls = {"ok": 0, "bad": 0}

        def fetcher(source):
            calls[source.id] += 1
            if source.id == "bad":
                return FetchResult(0, "", error="timeout após 5s")
            return FetchResult(200, "conteúdo público", "Fonte OK")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = PolicyWatch(root / "watch.sqlite3", root / "reports", sources, fetcher, max_workers=2).run()
            report = run.report_path.read_text(encoding="utf-8")

        self.assertEqual(calls, {"ok": 1, "bad": 1})
        self.assertEqual(run.baselines, ("ok",))
        self.assertEqual(run.errors, ("Fonte lenta: timeout após 5s",))
        self.assertIn("Resultado parcial", report)
        self.assertIn("não é possível concluir", report)


if __name__ == "__main__":
    unittest.main()
