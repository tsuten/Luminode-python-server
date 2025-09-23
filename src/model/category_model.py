from datetime import datetime
from beanie import Document, before_event, Insert
from typing import List, Dict, Any


class Category(Document):
    name: str
    description: str | None = None
    channels_order: List[str] = []
    next_category_id: str | None = None
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
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "channels_order": self.channels_order,
            "next_category_id": self.next_category_id,
        }


