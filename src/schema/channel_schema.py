from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import enum
from uuid import UUID

class ChannelType(enum.Enum):
    TEXT = "text"
    VOICE = "voice"

class ChannelSchema(BaseModel):
    name: str
    description: str
    type: ChannelType

class ChannelResponse(BaseModel):
    id: str
    name: str
    description: str
    type: ChannelType