import os
import unittest
from unittest.mock import patch

from alento_soft_ia.policy_watch import _send_email


class PolicyWatchNotificationTests(unittest.TestCase):
    @patch("alento_soft_ia.policy_watch.smtplib.SMTP_SSL")
    def test_email_uses_implicit_ssl_on_port_465(self, smtp_ssl):
        with patch.dict(
            os.environ,
            {
                "POLICY_WATCH_SMTP_HOST": "smtp.granjimmy.com.br",
                "POLICY_WATCH_SMTP_PORT": "465",
                "POLICY_WATCH_SMTP_USER": "naoresponda=granjimmy.com.br",
                "POLICY_WATCH_SMTP_PASSWORD": "senha-apenas-no-teste",
                "POLICY_WATCH_EMAIL_FROM": "naoresponda@granjimmy.com.br",
                "POLICY_WATCH_EMAIL_TO": "responsavel@example.com",
            },
            clear=False,
        ):
            _send_email("relatório de teste", "Vigia de teste")

        smtp_ssl.assert_called_once()
        smtp_ssl.return_value.__enter__.return_value.login.assert_called_once_with(
            "naoresponda=granjimmy.com.br", "senha-apenas-no-teste"
        )
        smtp_ssl.return_value.__enter__.return_value.send_message.assert_called_once()

    @patch("alento_soft_ia.policy_watch.smtplib.SMTP")
    def test_email_uses_starttls_on_port_587(self, smtp):
        with patch.dict(
            os.environ,
            {
                "POLICY_WATCH_SMTP_HOST": "smtp.example.com",
                "POLICY_WATCH_SMTP_PORT": "587",
                "POLICY_WATCH_SMTP_USER": "user",
                "POLICY_WATCH_SMTP_PASSWORD": "password",
                "POLICY_WATCH_EMAIL_FROM": "from@example.com",
                "POLICY_WATCH_EMAIL_TO": "to@example.com",
            },
            clear=False,
        ):
            _send_email("relatório de teste", "Vigia de teste")

        smtp.assert_called_once()
        smtp.return_value.__enter__.return_value.starttls.assert_called_once()
        smtp.return_value.__enter__.return_value.login.assert_called_once_with("user", "password")


if __name__ == "__main__":
    unittest.main()
