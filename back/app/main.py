import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.appointment_store import (
    AppointmentCreate,
    AppointmentRecord,
    delete_appointment,
    list_appointments,
    save_appointment,
    update_appointment_status,
)
from app.chat_flow import FlowResult, handle_chat, start_response


class ChatOption(BaseModel):
    id: str
    label: str


class ChatMap(BaseModel):
    latitude: float
    longitude: float
    label: str
    address: str


class ChatImage(BaseModel):
    url: str
    alt: str
    caption: Optional[str] = None


class ChatRequest(BaseModel):
    message: Optional[str] = Field(default=None, description="Texto digitado pelo usuario.")
    option_id: Optional[str] = Field(default=None, description="ID da opcao escolhida pelo usuario.")
    current_node: Optional[str] = Field(default=None, description="No atual da conversa no frontend.")


class ChatResponse(BaseModel):
    current_node: str
    messages: List[str]
    options: List[ChatOption]
    ended: bool = False
    map: Optional[ChatMap] = None
    image: Optional[ChatImage] = None


class AppointmentResponse(BaseModel):
    id: int
    patient_name: str
    document_masked: str
    service: str
    professional: str
    appointment_date: str
    appointment_time: str
    status: str
    created_at: str


class AppointmentStatusRequest(BaseModel):
    status: str


app = FastAPI(title="ESF Assistente API", version="0.1.0")
MAP_AREAS_IMAGE_PATH = Path(__file__).resolve().parents[2] / "templates" / "mapaAreas.jpeg"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
cors_origins.extend(
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def root() -> dict:
    return {
        "status": "ok",
        "service": "ESF Assistente API",
        "health": "/health",
    }


@app.get("/templates/mapaAreas.jpeg", include_in_schema=False)
def get_areas_map_image() -> FileResponse:
    return FileResponse(MAP_AREAS_IMAGE_PATH, media_type="image/jpeg")


@app.get("/api/chat/start", response_model=ChatResponse)
def start_chat() -> ChatResponse:
    return serialize(start_response())


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    result = handle_chat(message=request.message, option_id=request.option_id, current_node=request.current_node)
    if result.appointment:
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
        except ValueError:
            retry_result = handle_chat(option_id="agendamento_trocar_horario", current_node=request.current_node)
            result = FlowResult(
                current_node=retry_result.current_node,
                messages=["Esse horário acabou de ser ocupado antes de salvar.", *retry_result.messages],
                options=retry_result.options,
                ended=retry_result.ended,
                map=retry_result.map,
                image=retry_result.image,
            )

    return serialize(result)


@app.get("/api/appointments", response_model=List[AppointmentResponse])
def get_appointments(
    appointment_date: Optional[str] = Query(default=None, alias="date"),
    status: Optional[str] = None,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> List[AppointmentResponse]:
    verify_admin_token(admin_token)
    return [serialize_appointment(appointment) for appointment in list_appointments(appointment_date, status)]


@app.patch("/api/appointments/{appointment_id}/status", response_model=AppointmentResponse)
def update_status(
    appointment_id: int,
    request: AppointmentStatusRequest,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> AppointmentResponse:
    verify_admin_token(admin_token)
    try:
        appointment = update_appointment_status(appointment_id, request.status)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")

    return serialize_appointment(appointment)


@app.delete("/api/appointments/{appointment_id}")
def delete_appointment_route(
    appointment_id: int,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> dict:
    verify_admin_token(admin_token)
    was_deleted = delete_appointment(appointment_id)

    if not was_deleted:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")

    return {"deleted": True}


def serialize(result: FlowResult) -> ChatResponse:
    return ChatResponse(
        current_node=result.current_node,
        messages=result.messages,
        options=[ChatOption(id=option.id, label=option.label) for option in result.options],
        ended=result.ended,
        map=ChatMap(**result.map.__dict__) if result.map else None,
        image=ChatImage(**result.image.__dict__) if result.image else None,
    )


def serialize_appointment(appointment: AppointmentRecord) -> AppointmentResponse:
    return AppointmentResponse(**appointment.__dict__)


def verify_admin_token(admin_token: Optional[str]) -> None:
    if ADMIN_TOKEN and admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Código de acesso inválido.")
