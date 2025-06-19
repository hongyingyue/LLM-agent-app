from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    id: UUID
    username: str
    hashed_password: str
    created_at: datetime


class Session(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime


class Message(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime
    tool_calls: List


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id : str
    response: str

class ToolCall(BaseModel):
    id: UUID
    message_id: UUID
    tool_name: str
    parameters: dict
    result: Optional[str]
    status: str
    created_at: datetime


class FileRecord(BaseModel):
    id: UUID
    session_id: UUID
    filename: str
    filepath: str
    uploaded_at: datetime
