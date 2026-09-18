import asyncio
import hashlib
import hmac
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app import appointment_store
from app.main import app
from app.whatsapp import (
    compact_title,
    parse_incoming_messages,
    process_webhook_payload,
    verify_webhook_signature,
)
from app.whatsapp_store import claim_message, get_session, save_session


class WhatsAppIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        appointment_store.DATABASE_PATH = Path(self.temporary_directory.name) / "test.sqlite3"
        self.environment = patch.dict(
            os.environ,
            {
                "META_VERIFY_TOKEN": "verify-test",
                "META_APP_SECRET": "app-secret-test",
                "META_WHATSAPP_TOKEN": "token-test",
                "META_PHONE_NUMBER_ID": "phone-id-test",
            },
            clear=False,
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_webhook_verification(self) -> None:
        client = TestClient(app)
        response = client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "verify-test",
                "hub.challenge": "12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "12345")

    def test_signature_validation(self) -> None:
        body = b'{"object":"whatsapp_business_account"}'
        digest = hmac.new(b"app-secret-test", body, hashlib.sha256).hexdigest()

        self.assertTrue(verify_webhook_signature(body, f"sha256={digest}"))
        self.assertFalse(verify_webhook_signature(body, "sha256=invalid"))

    def test_parses_list_reply(self) -> None:
        payload = webhook_payload(
            {
                "id": "wamid.reply",
                "from": "5551999999999",
                "type": "interactive",
                "interactive": {"list_reply": {"id": "servicos"}},
            }
        )

        messages = parse_incoming_messages(payload)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].option_id, "servicos")

    def test_session_and_duplicate_message_storage(self) -> None:
        save_session("5551999999999", "informacoes")

        self.assertEqual(get_session("5551999999999"), "informacoes")
        self.assertTrue(claim_message("wamid.unique"))
        self.assertFalse(claim_message("wamid.unique"))

    def test_processes_each_message_only_once(self) -> None:
        payload = webhook_payload(
            {
                "id": "wamid.once",
                "from": "5551999999999",
                "type": "text",
                "text": {"body": "oi"},
            }
        )

        with (
            patch("app.whatsapp.mark_message_as_read", new_callable=AsyncMock) as mark_read,
            patch("app.whatsapp.send_flow_result", new_callable=AsyncMock) as send_result,
        ):
            asyncio.run(process_webhook_payload(payload))
            asyncio.run(process_webhook_payload(payload))

        mark_read.assert_awaited_once_with("wamid.once")
        send_result.assert_awaited_once()
        self.assertEqual(get_session("5551999999999"), "inicio")

    def test_compacts_long_menu_titles(self) -> None:
        title = compact_title("Curativos e testes rápidos")

        self.assertLessEqual(len(title), 24)
        self.assertTrue(title.endswith("…"))


def webhook_payload(message: dict) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messages": [message]}}]}],
    }


if __name__ == "__main__":
    unittest.main()
