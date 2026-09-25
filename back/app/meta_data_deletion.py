import base64
import hashlib
import hmac
import json
from typing import Any


def decode_signed_request(signed_request: str, app_secret: str) -> dict[str, Any]:
    try:
        encoded_signature, encoded_payload = signed_request.split(".", 1)
    except ValueError as error:
        raise ValueError("invalid signed request") from error

    signature = _urlsafe_b64decode(encoded_signature)
    expected_signature = hmac.new(
        app_secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("invalid signed request signature")

    try:
        payload = json.loads(_urlsafe_b64decode(encoded_payload))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("invalid signed request payload") from error

    if not isinstance(payload, dict):
        raise ValueError("invalid signed request payload")
    return payload


def confirmation_code(user_id: str, app_secret: str) -> str:
    value = f"{user_id}:{app_secret}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:20]


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, TypeError) as error:
        raise ValueError("invalid base64 value") from error
