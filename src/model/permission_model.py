from datetime import datetime
from beanie import Document, before_event, Insert
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from pydantic import BaseModel, field_validator

class PermissionType(Enum):
    MANAGE_MESSAGES = "manage_messages"
    MANAGE_CHANNELS = "manage_channels"
    TIMEOUT_USERS = "timeout_users"

class Permission(BaseModel):
    type: PermissionType
    is_allowed: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """JSONシリアライズ用の辞書を返す"""
        return {
            "type": self.type.value,
            "is_allowed": self.is_allowed
        }

class Role(Document):
    name: str
    description: str
    permissions: Optional[List[Permission]] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    
    @field_validator('permissions', mode='before')
    @classmethod
    def convert_single_permission_to_list(cls, v):
        """単一のPermissionオブジェクトをリストに変換（既存データとの互換性のため）"""
        if v is None:
            return None
        if isinstance(v, dict):
            # 単一のPermissionオブジェクト（辞書）の場合
            return [Permission(**v)]
        if isinstance(v, list):
            # 既にリストの場合
            return [Permission(**item) if isinstance(item, dict) else item for item in v]
        return v
    
    @before_event(Insert)
    def before_insert(self):
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.is_deleted = False
        self.deleted_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """JSONシリアライズ用の辞書を返す"""
        return {
            "id": "role:" + str(self.id),
            "name": self.name,
            "description": self.description,
            "permissions": [p.to_dict() for p in self.permissions] if self.permissions else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }