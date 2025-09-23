from datetime import datetime
from beanie import Document, before_event, Insert
from typing import Dict, Any
from uuid import UUID    
from schema.channel_schema import ChannelType

class Channel(Document):
    name: str
    description: str
    type: ChannelType
    # 形式: "category:{id}" を格納
    category_id: str | None = None
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
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "category_id": self.category_id,
        }