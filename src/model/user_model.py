from datetime import datetime
from beanie import Document, before_event, Insert, Update
from typing import Dict, Any, Optional
from uuid import UUID
from pydantic import Field, EmailStr

class User(Document):
    """ユーザーモデル"""
    auth_id: UUID = Field(..., description="認証システムでのユニークID")
    display_name: str = Field(..., min_length=1, max_length=100, description="表示名")
    email: Optional[EmailStr] = Field(default=None, description="メールアドレス")
    avatar_url: Optional[str] = Field(default=None, description="アバター画像のURL")
    is_online: bool = Field(default=False, description="オンライン状態")
    last_seen: Optional[datetime] = Field(default=None, description="最終アクセス日時")
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
    
    @before_event(Update)
    def before_update(self):
        self.updated_at = datetime.now()
    
    def update_last_seen(self):
        """最終アクセス日時を更新する"""
        self.last_seen = datetime.now()
    
    def set_online_status(self, is_online: bool):
        """オンライン状態を設定する"""
        self.is_online = is_online
        if is_online:
            self.update_last_seen()
    
    def to_dict(self) -> Dict[str, Any]:
        """JSONシリアライズ用の辞書を返す"""
        return {
            "id": str(self.id),
            "auth_id": str(self.auth_id),
            "display_name": self.display_name,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "is_online": self.is_online,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
    
    def to_dict_public(self) -> Dict[str, Any]:
        """公開用の辞書を返す（機密情報を除外）"""
        return {
            "id": str(self.id),
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "is_online": self.is_online,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
    
    @classmethod
    async def find_by_auth_id(cls, auth_id: UUID) -> Optional["User"]:
        """認証IDでユーザーを検索する"""
        return await cls.find_one(cls.auth_id == auth_id, cls.is_deleted == False)
    
    @classmethod
    async def find_by_email(cls, email: str) -> Optional["User"]:
        """メールアドレスでユーザーを検索する"""
        return await cls.find_one(cls.email == email, cls.is_deleted == False)