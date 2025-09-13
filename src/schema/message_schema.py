from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import enum

class MessageType(enum.Enum):
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    FILE = "file"
    OTHER = "other"

class MessageSchema(BaseModel):
    type: MessageType
    content: str
    send_to: str

class MessageResponse(BaseModel):
    id: str
    type: MessageType
    content: str
    sent_by: str
    sent_to: str