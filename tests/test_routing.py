import json
import os
import unittest
import urllib.error
from email.message import Message
from unittest.mock import patch

from alento_soft_ia.provider import OpenAICompatibleProvider, OllamaProvider
from alento_soft_ia.routing import build_provider


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.payload


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.context = {
            "source_name": "granjimmy_contexto_minimo.md",
            "source_text": "Fonte pública autorizada de marketing.",
        }

    def test_hybrid_keeps_clinical_on_ollama(self):
        provider = build_provider("hybrid", "clinical", self.context)
        self.assertIsInstance(provider, OllamaProvider)
        self.assertEqual(provider.name, "ollama")

    def test_cloud_provider_rejects_clinical_domain(self):
        with self.assertRaisesRegex(RuntimeError, "somente o domínio marketing"):
            build_provider("openai", "clinical", self.context)

    def test_cloud_provider_rejects_unknown_marketing_source(self):
        context = {**self.context, "source_name": "profissionais-granjimmy"}
        with self.assertRaisesRegex(RuntimeError, "lista autorizada"):
            build_provider("openrouter", "marketing", context)

    @patch.dict(
        os.environ,
        {"OPENROUTER_API_KEY": "test-key", "OPENROUTER_MODEL": "test/model"},
        clear=False,
    )
    def test_hybrid_routes_allowlisted_marketing_to_openrouter(self):
        provider = build_provider("hybrid", "marketing", self.context)
        self.assertIsInstance(provider, OpenAICompatibleProvider)
        self.assertEqual(provider.name, "openrouter")
        self.assertTrue(provider.configured)

    def test_http_429_exposes_safe_quota_diagnostic(self):
        provider = OpenAICompatibleProvider(
            base_url="https://example.test/v1",
            api_key="secret-key-that-must-not-appear",
            model="test/model",
            require_api_key=True,
            name="test-cloud",
        )
        error_body = json.dumps(
            {
                "error": {
                    "message": "Provider returned error",
                    "type": "429",
                    "code": 429,
                    "metadata": {
                        "error_type": "rate_limit_exceeded",
                        "provider_name": "Google",
                        "provider_code": "model_capacity",
                    },
                }
            }
        ).encode("utf-8")
        http_error = urllib.error.HTTPError(
            "https://example.test/v1/chat/completions",
            429,
            "Too Many Requests",
            {},
            None,
        )
        http_error.read = lambda: error_body
        http_error.headers = Message()
        http_error.headers.add_header("Retry-After", "7")
        http_error.headers.add_header("X-RateLimit-Remaining", "0")

        with patch("urllib.request.urlopen", side_effect=http_error):
            with self.assertRaisesRegex(RuntimeError, r"Provider HTTP 429: rate_limit_exceeded; provider=Google") as raised:
                provider.chat_json([{"role": "user", "content": "teste"}], {"type": "object"})

        self.assertNotIn("secret-key-that-must-not-appear", str(raised.exception))
        self.assertIn("provider_code=model_capacity", str(raised.exception))
        self.assertIn("Retry-After=7", str(raised.exception))
        self.assertIn("X-RateLimit-Remaining=0", str(raised.exception))

    def test_openai_compatible_provider_sends_schema(self):
        schema = {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
            "additionalProperties": False,
        }
        response = {"choices": [{"message": {"content": '{"summary": "ok"}'}}]}
        provider = OpenAICompatibleProvider(
            base_url="https://example.test/v1",
            api_key="test-key",
            model="test/model",
            require_api_key=True,
            name="test-cloud",
        )

        with patch("urllib.request.urlopen", return_value=FakeResponse(response)) as mocked:
            result = provider.chat_json([{"role": "user", "content": "teste"}], schema)

        request = mocked.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(result, {"summary": "ok"})
        self.assertEqual(payload["model"], "test/model")
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertTrue(payload["response_format"]["json_schema"]["strict"])


if __name__ == "__main__":
    unittest.main()
