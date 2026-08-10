import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional


VALID_STATUSES = {"novo", "confirmado", "cancelado", "atendido"}
DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "agendamentos.sqlite3"


def get_database_path() -> Path:
    configured_path = os.getenv("APPOINTMENTS_DB_PATH") or os.getenv("DATABASE_PATH")
    if configured_path:
        return Path(configured_path).expanduser()

    configured_dir = os.getenv("APPOINTMENTS_DATA_DIR") or os.getenv("RENDER_DISK_PATH")
    if configured_dir:
        return Path(configured_dir).expanduser() / "agendamentos.sqlite3"

    render_data_dir = Path("/var/data")
    if os.getenv("RENDER") and render_data_dir.exists():
        return render_data_dir / "agendamentos.sqlite3"

    return DEFAULT_DATABASE_PATH


DATABASE_PATH = get_database_path()


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
                created_at TEXT NOT NULL,
                deleted_at TEXT
            )
            """
        )
        ensure_deleted_at_column(connection)


def save_appointment(appointment: AppointmentCreate) -> int:
    init_db()
    created_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        if is_slot_booked_on_connection(
            connection,
            appointment.appointment_date,
            appointment.appointment_time,
        ):
            raise ValueError("Horário indisponível.")

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

def is_appointment_slot_booked(appointment_date: str, appointment_time: str) -> bool:
    init_db()
    with connect() as connection:
        return is_slot_booked_on_connection(connection, appointment_date, appointment_time)


def is_slot_booked_on_connection(
    connection: sqlite3.Connection,
    appointment_date: str,
    appointment_time: str,
) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM appointments
        WHERE appointment_date = ?
          AND appointment_time = ?
          AND status != 'cancelado'
          AND deleted_at IS NULL
        LIMIT 1
        """,
        (appointment_date, appointment_time),
    ).fetchone()

    return row is not None


def list_appointments(
    appointment_date: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[AppointmentRecord]:
    init_db()
    clauses = ["deleted_at IS NULL"]
    params = []

    if appointment_date:
        clauses.append("appointment_date = ?")
        params.append(appointment_date)
    else:
        if start_date:
            clauses.append("appointment_date >= ?")
            params.append(start_date)

        if end_date:
            clauses.append("appointment_date <= ?")
            params.append(end_date)

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
        raise ValueError("Status inválido.")

    init_db()
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE appointments SET status = ? WHERE id = ? AND deleted_at IS NULL",
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
              AND deleted_at IS NULL
            """,
            (appointment_id,),
        ).fetchone()

    return record_from_row(row) if row else None


def delete_appointment(appointment_id: int) -> bool:
    init_db()
    deleted_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE appointments
            SET deleted_at = ?
            WHERE id = ?
              AND deleted_at IS NULL
            """,
            (deleted_at, appointment_id),
        )

    return cursor.rowcount > 0


def ensure_deleted_at_column(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(appointments)").fetchall()
    }
    if "deleted_at" not in columns:
        connection.execute("ALTER TABLE appointments ADD COLUMN deleted_at TEXT")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


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
