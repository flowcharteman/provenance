import unittest
from unittest.mock import patch

from app.config.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_sec_user_agent_is_built_from_explicit_environment_values(self):
        with patch.dict(
            "os.environ",
            {
                "POSTGRES_PASSWORD": "local-only",
                "SEC_USER_AGENT_NAME": "Configured Product",
                "SEC_CONTACT_EMAIL": "contact@example.invalid",
            },
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertEqual(
            settings.sec_user_agent,
            "Configured Product contact@example.invalid",
        )
        self.assertIn("local-only", settings.database_url)

    def test_missing_sec_contact_is_not_replaced_with_a_default(self):
        with patch.dict(
            "os.environ",
            {
                "POSTGRES_PASSWORD": "local-only",
                "SEC_USER_AGENT_NAME": "Configured Product",
            },
            clear=True,
        ):
            settings = Settings.from_env()

        with self.assertRaisesRegex(ValueError, "SEC_CONTACT_EMAIL"):
            _ = settings.sec_user_agent
