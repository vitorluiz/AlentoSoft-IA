import tempfile
import unittest
from pathlib import Path

from alento_soft_ia.audit import AuditLog
from alento_soft_ia.core import AlentoAgent, TaskStatus
from alento_soft_ia.llm_skill import LLMPolicySkill, OUTPUT_SCHEMA
from alento_soft_ia.skills import internal_policy_checklist


class FakeProvider:
    configured = True

    def __init__(self, result):
        self.result = result
        self.schema = None

    def chat_json(self, messages, schema):
        self.schema = schema
        return self.result


class ValidationTests(unittest.TestCase):
    def test_demo_skill_matches_structured_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = AlentoAgent(AuditLog(Path(directory) / "audit.sqlite3"), internal_policy_checklist)
            task = agent.create_task("Criar checklist administrativo", "general")
            result = agent.run(task)
            self.assertEqual(result.status, TaskStatus.COMPLETED)

    def test_incompatible_json_is_rejected(self):
        def bad_skill(_task):
            return {"checklist": [{"item": "sem schema"}]}

        with tempfile.TemporaryDirectory() as directory:
            agent = AlentoAgent(AuditLog(Path(directory) / "audit.sqlite3"), bad_skill)
            task = agent.create_task("Criar checklist administrativo", "general")
            result = agent.run(task)
            self.assertEqual(result.status, TaskStatus.FAILED)
            self.assertTrue(any("Campos obrigatórios ausentes" in error for error in result.errors))

    def test_llm_skill_sends_schema_and_requires_review(self):
        provider = FakeProvider({
            "summary": "Checklist administrativo",
            "items": [{"id": 1, "description": "Conferir documentos", "responsible": "RH", "status": "pending", "source_section": "Seção 1", "evidence": "Conferir documentos."}],
            "sources": ["fonte fictícia"],
            "missing_information": [],
            "human_review_required": False,
            "status": "draft",
        })
        skill = LLMPolicySkill(provider)
        with tempfile.TemporaryDirectory() as directory:
            task = AlentoAgent(AuditLog(Path(directory) / "audit.sqlite3"), skill).create_task(
                "Criar checklist", "general", context={"source_name": "fonte fictícia", "source_text": "Seção 1: conferir documentos."}
            )
            result = skill(task)
        self.assertEqual(provider.schema, OUTPUT_SCHEMA)
        self.assertTrue(result["human_review_required"])
        self.assertEqual(result["status"], "draft")


if __name__ == "__main__":
    unittest.main()
