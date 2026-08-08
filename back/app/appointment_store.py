import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "agendamentos.sqlite3"
VALID_STATUSES = {"novo", "confirmado", "cancelado", "atendido"}


@dataclass(frozen=True)
class AppointmentCreate:
    patient_name: str
    document: str
    service: str
    professional: str
    appointment_date: str
    appointment_time: str


@dataclass(frozen=True)
class AppointmentRecord:
    id: int
    patient_name: str
    document_masked: str
    service: str
    professional: str
    appointment_date: str
    appointment_time: str
    status: str
    created_at: str


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                document TEXT NOT NULL,
                service TEXT NOT NULL,
                professional TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'novo',
                created_at TEXT NOT NULL
            )
            """
        )


def save_appointment(appointment: AppointmentCreate) -> int:
    init_db()
    created_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO appointments (
                patient_name,
                document,
                service,
                professional,
                appointment_date,
                appointment_time,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'novo', ?)
            """,
            (
                appointment.patient_name,
                appointment.document,
                appointment.service,
                appointment.professional,
                appointment.appointment_date,
                appointment.appointment_time,
                created_at,
            ),
        )
        return int(cursor.lastrowid)


def list_appointments(
    appointment_date: Optional[str] = None,
    status: Optional[str] = None,
) -> List[AppointmentRecord]:
    init_db()
    clauses = []
    params = []

    if appointment_date:
        clauses.append("appointment_date = ?")
        params.append(appointment_date)

    if status and status != "todos":
        clauses.append("status = ?")
        params.append(status)

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT
                id,
                patient_name,
                document,
                service,
                professional,
                appointment_date,
                appointment_time,
                status,
                created_at
            FROM appointments
            {where_clause}
            ORDER BY appointment_date ASC, appointment_time ASC, id ASC
            """,
            params,
        ).fetchall()

    return [record_from_row(row) for row in rows]


def update_appointment_status(appointment_id: int, status: str) -> Optional[AppointmentRecord]:
    if status not in VALID_STATUSES:
        raise ValueError("Status invalido.")

    init_db()
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE appointments SET status = ? WHERE id = ?",
            (status, appointment_id),
        )

        if cursor.rowcount == 0:
            return None

        row = connection.execute(
            """
            SELECT
                id,
                patient_name,
                document,
                service,
                professional,
                appointment_date,
                appointment_time,
                status,
                created_at
            FROM appointments
            WHERE id = ?
            """,
            (appointment_id,),
        ).fetchone()

    return record_from_row(row) if row else None


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def record_from_row(row: sqlite3.Row) -> AppointmentRecord:
    return AppointmentRecord(
        id=int(row["id"]),
        patient_name=row["patient_name"],
        document_masked=mask_document(row["document"]),
        service=row["service"],
        professional=row["professional"],
        appointment_date=row["appointment_date"],
        appointment_time=row["appointment_time"],
        status=row["status"],
        created_at=row["created_at"],
    )


def mask_document(document: str) -> str:
    cleaned = "".join(char for char in document if char.isalnum())
    if len(cleaned) <= 4:
        return "****"

    return f"{'*' * (len(cleaned) - 4)}{cleaned[-4:]}"
