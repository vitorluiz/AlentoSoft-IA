import tempfile
import unittest
from pathlib import Path

from alento_soft_ia.audit import AuditLog
from alento_soft_ia.clickup_context import build_marketing_context
from alento_soft_ia.core import AlentoAgent
from alento_soft_ia.marketing_skill import MarketingSkill


class RecordingProvider:
    configured = True

    def __init__(self):
        self.messages = []

    def chat_json(self, messages, schema):
        self.messages = messages
        return {
            "summary": "Rascunho editorial",
            "items": [
                {
                    "id": 1,
                    "channel": "instagram",
                    "format": "carrossel",
                    "title": "Tema educativo",
                    "copy": "Conteúdo educativo e acolhedor.",
                    "cta": "Procure orientação pelos canais oficiais.",
                    "status": "draft",
                    "source_section": "Objetivo",
                    "evidence": "Conteúdo autorizado.",
                }
            ],
            "sources": ["ClickUp"],
            "missing_information": [],
            "risk_flags": [],
            "human_review_required": True,
            "status": "ready_for_review",
        }


class ClickUpContextTests(unittest.TestCase):
    def test_build_context_separates_clickup_controls_from_cloud_source(self):
        editorial_task = {
            "id": "task-editorial-001",
            "name": "[Instagram | Carrossel] Tema educativo",
            "markdown_description": (
                "RASCUNHO — NÃO PUBLICAR SEM APROVAÇÃO\n"
                "Canal: Instagram\n"
                "Público: Adultos e familiares.\n"
                "Objetivo: Orientar sobre quando procurar avaliação profissional.\n"
                "Mensagem principal: Mudanças persistentes e sofrimento merecem avaliação individualizada.\n"
                "Base factual autorizada: serviço institucional e canais oficiais.\n"
                "CTA: Procure orientação pelos canais oficiais.\n\n"
                "PORTA-VOZ E AUTORIDADE DA PEÇA\n"
                "Identificação a exibir: Pessoa Exemplo | Médico | CRM-XX 0000.\n"
                "NÃO INSERIR NOME NA ARTE AINDA.\n\n"
                "NOTA INSTITUCIONAL OBRIGATÓRIA PARA A LEGENDA\n"
                "Estabelecimento: Instituição Exemplo.\n"
                "CNES 1234567. SES nº 1234.567890.2026."
            ),
            "custom_fields": [],
        }
        professional_task = {
            "id": "task-professional-001",
            "markdown_description": (
                "CADASTRO INTERNO — NÃO UTILIZAR PUBLICAMENTE SEM VALIDAÇÃO DOCUMENTAL E AUTORIZAÇÃO\n"
                "Nome informado: Pessoa Exemplo\n"
                "Função/formação informada: Médico\n"
                "Especialização informada: Psiquiatria\n"
                "Conselho profissional: CRM-XX\n"
                "Número informado: 0000\n"
                "RQE informado: 0000\n"
                "Autorização de nome e imagem: PENDENTE\n"
                "Estado editorial: PENDENTE DE VALIDAÇÃO"
            ),
            "custom_fields": [],
        }

        context = build_marketing_context(editorial_task, professional_task)

        self.assertEqual(context["channel"], "instagram")
        self.assertEqual(context["institutional_metadata"]["cnes"], "1234567")
        self.assertEqual(
            context["institutional_metadata"]["sanitary_registration"],
            "1234.567890.2026",
        )
        self.assertEqual(context["public_identification"]["status"], "pending_validation")
        self.assertFalse(context["public_identification"]["must_be_rendered"])
        self.assertIn("Pessoa Exemplo", context["public_identification"]["name"])
        self.assertNotIn("Pessoa Exemplo", context["source_text"])
        self.assertNotIn("CRM-XX", context["source_text"])
        self.assertNotIn("0000", context["source_text"])

    def test_controls_are_not_sent_to_provider_cloud(self):
        editorial_task = {
            "id": "task-editorial-003",
            "name": "[Instagram | Post] Institucional",
            "markdown_description": (
                "Canal: Instagram\n"
                "Objetivo: Conteúdo educativo.\n"
                "Mensagem principal: Orientação geral e acolhedora.\n\n"
                "PORTA-VOZ E AUTORIDADE DA PEÇA\n"
                "Identificação a exibir: Pessoa Exemplo | Médico | CRM-XX 0000.\n"
                "NÃO INSERIR NOME NA ARTE AINDA."
            ),
        }
        professional_task = {
            "id": "task-professional-003",
            "markdown_description": (
                "Nome informado: Pessoa Exemplo\n"
                "Conselho profissional: CRM-XX\n"
                "Número informado: 0000\n"
                "RQE informado: 0000\n"
                "Autorização de nome e imagem: PENDENTE"
            ),
        }
        context = build_marketing_context(editorial_task, professional_task)
        provider = RecordingProvider()
        skill = MarketingSkill(provider)
        with tempfile.TemporaryDirectory() as directory:
            task = AlentoAgent(
                AuditLog(Path(directory) / "audit.sqlite3"),
                skill,
            ).create_task(
                "Criar conteúdo educativo",
                "marketing",
                context=context,
            )
            skill(task)

        prompt = "\n".join(message["content"] for message in provider.messages)
        self.assertNotIn("Pessoa Exemplo", prompt)
        self.assertNotIn("CRM-XX", prompt)
        self.assertNotIn("0000", prompt)

    def test_explicit_custom_control_groups_override_text_extraction(self):
        editorial_task = {
            "id": "task-editorial-002",
            "name": "[Instagram | Post] Institucional",
            "markdown_description": "Canal: Instagram\nObjetivo: Conteúdo educativo.",
            "custom_fields": [
                {
                    "id": "field-1",
                    "name": "institutional_metadata",
                    "value": {
                        "institution_name": "Instituição Validada",
                        "verified": True,
                    },
                },
                {
                    "id": "field-2",
                    "name": "approval_gates",
                    "value": {"institutional": "approved"},
                },
            ],
        }
        context = build_marketing_context(editorial_task)
        self.assertEqual(
            context["institutional_metadata"]["institution_name"],
            "Instituição Validada",
        )
        self.assertTrue(context["institutional_metadata"]["verified"])
        self.assertEqual(context["approval_gates"]["institutional"], "approved")


if __name__ == "__main__":
    unittest.main()
