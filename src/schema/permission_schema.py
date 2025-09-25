from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class Action(Enum):
    MANAGE_MESSAGES = "manage_messages"
    CREATE_CHANNELS = "create_channels"
    MANAGE_CHANNELS = "manage_channels"

class Permission(BaseModel):
    object: str
    action: Action
    is_granted: bool

class UserLevelPermission(BaseModel):

    permission: Permission[]
    created_at: datetime
    updated_at: datetime

class ChannelLevelPermission(BaseModel):
    channel_id: str
    permission: Permission
    created_at: datetime
    updated_at: datetime