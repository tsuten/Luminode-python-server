from datetime import datetime
from beanie import Document, before_event, Insert
from typing import Dict, Any
from schema.message_schema import MessageType

class Message(Document):
    type: MessageType
    content: str
    sent_by: str
    sent_to: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    
    @before_event(Insert)
    def before_insert(self):
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.is_deleted = False
        self.deleted_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """JSONシリアライズ用の辞書を返す"""
        return {
            "id": str(self.id),
            "type": self.type.value,
            "content": self.content,
            "sent_by": self.sent_by,
            "sent_to": self.sent_to,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }