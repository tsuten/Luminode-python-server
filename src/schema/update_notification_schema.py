from pydantic import BaseModel
from enum import Enum


class UpdateNotificationType(Enum):
    MESSAGE = "message"
    CHANNEL = "channel"
    USER = "user"

class UpdateNotification(BaseModel):
    id: str
    collection: UpdateNotificationType
    additional_data: dict
    timestamp: str