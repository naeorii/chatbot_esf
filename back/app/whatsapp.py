import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import httpx

from app.appointment_store import AppointmentCreate, save_appointment
from app.chat_flow import FlowOption, FlowResult, handle_chat
from app.whatsapp_store import claim_message, get_session, release_message, save_session


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IncomingMessage:
    message_id: str
    sender: str
    text: Optional[str] = None
    option_id: Optional[str] = None


def whatsapp_is_configured() -> bool:
    return bool(
        os.getenv("META_WHATSAPP_TOKEN")
        and os.getenv("META_PHONE_NUMBER_ID")
        and os.getenv("META_VERIFY_TOKEN")
        and os.getenv("META_APP_SECRET")
    )


def verify_webhook_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    app_secret = os.getenv("META_APP_SECRET")
    if not app_secret:
        return False
    if not signature or not signature.startswith("sha256="):
        return False

    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature.removeprefix("sha256="), expected)


def parse_incoming_messages(payload: Dict[str, Any]) -> List[IncomingMessage]:
    incoming: List[IncomingMessage] = []
    if payload.get("object") != "whatsapp_business_account":
        return incoming

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                parsed = parse_message(message)
                if parsed:
                    incoming.append(parsed)

    return incoming


def parse_message(message: Dict[str, Any]) -> Optional[IncomingMessage]:
    message_id = str(message.get("id", "")).strip()
    sender = str(message.get("from", "")).strip()
    if not message_id or not sender:
        return None

    message_type = message.get("type")
    if message_type == "text":
        return IncomingMessage(
            message_id=message_id,
            sender=sender,
            text=str(message.get("text", {}).get("body", "")).strip(),
        )

    if message_type == "interactive":
        interactive = message.get("interactive", {})
        reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
        option_id = str(reply.get("id", "")).strip()
        if option_id:
            return IncomingMessage(message_id=message_id, sender=sender, option_id=option_id)

    if message_type == "button":
        option_id = str(message.get("button", {}).get("payload", "")).strip()
        if option_id:
            return IncomingMessage(message_id=message_id, sender=sender, option_id=option_id)

    return IncomingMessage(message_id=message_id, sender=sender)


async def process_webhook_payload(payload: Dict[str, Any]) -> None:
    for incoming in parse_incoming_messages(payload):
        if not claim_message(incoming.message_id):
            continue

        try:
            await mark_message_as_read(incoming.message_id)
            current_node = get_session(incoming.sender)
            if incoming.text is None and incoming.option_id is None:
                await send_text(
                    incoming.sender,
                    "Consigo atender mensagens de texto e as opções do menu. Digite oi para começar.",
                )
                continue

            result = handle_chat(
                message=incoming.text,
                option_id=incoming.option_id,
                current_node=current_node,
            )
            result = persist_appointment(result, current_node)
            save_session(incoming.sender, result.current_node)
            await send_flow_result(incoming.sender, result)
        except Exception:
            release_message(incoming.message_id)
            logger.exception("Falha ao processar uma mensagem recebida do WhatsApp.")


def persist_appointment(result: FlowResult, current_node: Optional[str]) -> FlowResult:
    if not result.appointment:
        return result

    try:
        save_appointment(
            AppointmentCreate(
                patient_name=result.appointment.patient_name,
                document=result.appointment.document,
                service=result.appointment.service,
                professional=result.appointment.professional,
                appointment_date=result.appointment.appointment_date,
                appointment_time=result.appointment.appointment_time,
            )
        )
        return result
    except ValueError:
        retry_result = handle_chat(
            option_id="agendamento_trocar_horario",
            current_node=current_node,
        )
        return FlowResult(
            current_node=retry_result.current_node,
            messages=[
                "Esse horário acabou de ser ocupado antes de salvar.",
                *retry_result.messages,
            ],
            options=retry_result.options,
            ended=retry_result.ended,
            map=retry_result.map,
            image=retry_result.image,
        )


async def send_flow_result(recipient: str, result: FlowResult) -> None:
    body = "\n\n".join(result.messages)
    if result.options:
        await send_options(recipient, body, result.options)
    elif body:
        await send_text(recipient, body)

    if result.map:
        await send_location(
            recipient,
            latitude=result.map.latitude,
            longitude=result.map.longitude,
            name=result.map.label,
            address=result.map.address,
        )

    if result.image:
        image_url = public_url(result.image.url)
        if image_url:
            await send_image(recipient, image_url, result.image.caption or result.image.alt)


async def send_options(recipient: str, body: str, options: Iterable[FlowOption]) -> None:
    option_list = list(options)
    if len(option_list) <= 3 and all(len(option.label) <= 20 for option in option_list):
        interactive = {
            "type": "button",
            "body": {"text": body[:1024]},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": option.id, "title": option.label},
                    }
                    for option in option_list
                ]
            },
        }
    else:
        interactive = {
            "type": "list",
            "body": {"text": body[:1024]},
            "action": {
                "button": "Ver opções",
                "sections": [
                    {
                        "title": "Atendimento",
                        "rows": [
                            {"id": option.id, "title": compact_title(option.label)}
                            for option in option_list[:10]
                        ],
                    }
                ],
            },
        }

    await graph_request(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "interactive",
            "interactive": interactive,
        }
    )


async def send_text(recipient: str, text: str) -> None:
    await graph_request(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": True, "body": text[:4096]},
        }
    )


async def send_location(
    recipient: str,
    latitude: float,
    longitude: float,
    name: str,
    address: str,
) -> None:
    await graph_request(
        {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "location",
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "name": name,
                "address": address,
            },
        }
    )


async def send_image(recipient: str, image_url: str, caption: str) -> None:
    await graph_request(
        {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "image",
            "image": {"link": image_url, "caption": caption[:1024]},
        }
    )


async def mark_message_as_read(message_id: str) -> None:
    await graph_request(
        {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
    )


async def graph_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    token = os.getenv("META_WHATSAPP_TOKEN")
    phone_number_id = os.getenv("META_PHONE_NUMBER_ID")
    if not token or not phone_number_id:
        raise RuntimeError("A integração do WhatsApp ainda não está configurada.")

    api_version = os.getenv("META_GRAPH_API_VERSION", "v25.0")
    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def public_url(path: str) -> Optional[str]:
    if path.startswith(("http://", "https://")):
        return path

    base_url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if not base_url:
        return None
    return f"{base_url}/{path.lstrip('/')}"


def compact_title(title: str) -> str:
    return title if len(title) <= 24 else f"{title[:23]}…"
