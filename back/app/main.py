import os
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.chat_flow import FlowResult, handle_chat, start_response


class ChatOption(BaseModel):
    id: str
    label: str


class ChatMap(BaseModel):
    latitude: float
    longitude: float
    label: str
    address: str


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


app = FastAPI(title="ESF Assistente API", version="0.1.0")

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


@app.get("/api/chat/start", response_model=ChatResponse)
def start_chat() -> ChatResponse:
    return serialize(start_response())


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return serialize(handle_chat(message=request.message, option_id=request.option_id))


def serialize(result: FlowResult) -> ChatResponse:
    return ChatResponse(
        current_node=result.current_node,
        messages=result.messages,
        options=[ChatOption(id=option.id, label=option.label) for option in result.options],
        ended=result.ended,
        map=ChatMap(**result.map.__dict__) if result.map else None,
    )
