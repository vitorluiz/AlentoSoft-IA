import json
import unittest
from unittest.mock import patch

from alento_soft_ia.provider import OllamaProvider


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.payload


class OllamaProviderTests(unittest.TestCase):
    def test_native_payload_disables_thinking_and_uses_schema(self):
        schema = {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        }
        response = {"message": {"content": '{"summary": "ok"}'}}
        provider = OllamaProvider(
            base_url="http://localhost:11434/api",
            model="qwen3.5:4b-q4_K_M",
            think=False,
            keep_alive="10m",
        )

        with patch("urllib.request.urlopen", return_value=FakeResponse(response)) as mocked:
            result = provider.chat_json([{"role": "user", "content": "teste"}], schema)

        request = mocked.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(result, {"summary": "ok"})
        self.assertFalse(payload["think"])
        self.assertEqual(payload["format"], schema)
        self.assertEqual(payload["keep_alive"], "10m")
        self.assertEqual(payload["options"]["temperature"], 0)


if __name__ == "__main__":
    unittest.main()
