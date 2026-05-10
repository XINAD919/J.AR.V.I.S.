import datetime

from pydantic import BaseModel


class Webhook(BaseModel):
    event: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    files: list[str] | None = None  # paths o base64 para archivos de medicación


class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_calls_used: list[str]
    timestamp: datetime
