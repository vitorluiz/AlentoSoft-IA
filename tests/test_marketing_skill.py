import tempfile
import unittest
from pathlib import Path

from alento_soft_ia.audit import AuditLog
from alento_soft_ia.core import AlentoAgent, TaskStatus
from alento_soft_ia.marketing_skill import MARKETING_SCHEMA, MarketingSkill


class FakeProvider:
    configured = True

    def __init__(self, result):
        self.result = result
        self.schema = None

    def chat_json(self, messages, schema):
        self.schema = schema
        return self.result


class MarketingSkillTests(unittest.TestCase):
    def _item(self, status="draft"):
        return {
            "id": 1,
            "channel": "instagram",
            "format": "carrossel",
            "title": "Acolhimento em saúde mental",
            "copy": "Conteúdo educativo para orientar famílias.",
            "cta": "Fale com o atendimento pelos canais oficiais.",
            "status": status,
            "source_section": "Pilares da marca",
            "evidence": "A marca publica acolhimento, suporte às famílias e cuidado humanizado.",
        }

    def _result(self, item_status="draft"):
        return {
            "summary": "Plano de conteúdo para Instagram",
            "items": [self._item(item_status)],
            "sources": ["granjimmy_contexto_marca.md"],
            "missing_information": [],
            "risk_flags": ["Revisar pela instituição antes de publicar."],
            "human_review_required": True,
            "status": "ready_for_review",
        }

    def _task(self, skill):
        return AlentoAgent(AuditLog(Path(tempfile.mkdtemp()) / "audit.sqlite3"), skill).create_task(
            "Criar uma semana de conteúdo para Instagram e WhatsApp",
            "marketing",
            context={
                "source_name": "granjimmy_contexto_marca.md",
                "source_text": "A marca valoriza acolhimento, suporte às famílias e cuidado humanizado.",
            },
        )

    def test_marketing_skill_uses_schema_and_requires_review(self):
        provider = FakeProvider(self._result())
        skill = MarketingSkill(provider)
        result = skill(self._task(skill))
        self.assertEqual(provider.schema, MARKETING_SCHEMA)
        self.assertTrue(result["human_review_required"])
        self.assertEqual(result["status"], "ready_for_review")

    def test_marketing_draft_waits_for_approval(self):
        skill = MarketingSkill(FakeProvider(self._result()))
        with tempfile.TemporaryDirectory() as directory:
            agent = AlentoAgent(AuditLog(Path(directory) / "audit.sqlite3"), skill)
            task = agent.create_task(
                "Criar conteúdo educativo",
                "marketing",
                context={"source_name": "marca", "source_text": "Acolhimento e suporte às famílias."},
            )
            result = agent.run(task)
            self.assertEqual(result.status, TaskStatus.WAITING_APPROVAL)
            result = agent.run(task, approval=True)
            self.assertEqual(result.status, TaskStatus.COMPLETED)

    def test_marketing_blocked_item_blocks_publication(self):
        skill = MarketingSkill(FakeProvider(self._result("blocked")))
        with tempfile.TemporaryDirectory() as directory:
            agent = AlentoAgent(AuditLog(Path(directory) / "audit.sqlite3"), skill)
            task = agent.create_task(
                "Criar anúncio com promessa de cura",
                "marketing",
                context={"source_name": "marca", "source_text": "Acolhimento institucional."},
            )
            result = agent.run(task, approval=True)
            self.assertEqual(result.status, TaskStatus.BLOCKED)


if __name__ == "__main__":
    unittest.main()
