import hashlib
from datetime import datetime, timezone
from typing import Optional

from app.appointment_store import connect, init_db


def init_whatsapp_store() -> None:
    init_db()
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS whatsapp_sessions (
                contact_hash TEXT PRIMARY KEY,
                current_node TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS whatsapp_messages (
                message_id TEXT PRIMARY KEY,
                received_at TEXT NOT NULL
            )
            """
        )


def contact_key(phone_number: str) -> str:
    return hashlib.sha256(phone_number.encode("utf-8")).hexdigest()


def get_session(phone_number: str) -> Optional[str]:
    init_whatsapp_store()
    with connect() as connection:
        row = connection.execute(
            "SELECT current_node FROM whatsapp_sessions WHERE contact_hash = ?",
            (contact_key(phone_number),),
        ).fetchone()

    return str(row["current_node"]) if row else None


def save_session(phone_number: str, current_node: str) -> None:
    init_whatsapp_store()
    updated_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO whatsapp_sessions (contact_hash, current_node, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(contact_hash) DO UPDATE SET
                current_node = excluded.current_node,
                updated_at = excluded.updated_at
            """,
            (contact_key(phone_number), current_node, updated_at),
        )


def claim_message(message_id: str) -> bool:
    init_whatsapp_store()
    received_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO whatsapp_messages (message_id, received_at)
            VALUES (?, ?)
            """,
            (message_id, received_at),
        )

    return cursor.rowcount == 1


def release_message(message_id: str) -> None:
    init_whatsapp_store()
    with connect() as connection:
        connection.execute(
            "DELETE FROM whatsapp_messages WHERE message_id = ?",
            (message_id,),
        )
