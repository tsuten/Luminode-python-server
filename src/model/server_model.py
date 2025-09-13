from datetime import datetime
from beanie import Document, before_event, Insert, Update
from typing import Dict, Any, Optional, List
from pydantic import Field
from enum import Enum

class AuthMethod(str, Enum):
    """認証方式"""
    INTERNAL = "internal"  # 内部認証
    EXTERNAL = "external"  # 外部認証（OAuth等）
    DISABLED = "disabled"  # 認証無効

class ServerStatus(str, Enum):
    """サーバーの状態"""
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"

class ServerSettings(Document):
    """サーバー設定モデル"""
    is_private: bool = Field(default=False, description="プライベートサーバーかどうか")
    max_members: int = Field(default=1000, ge=1, le=100000, description="最大メンバー数")
    allow_registration: bool = Field(default=True, description="新規登録を許可するか")
    require_email_verification: bool = Field(default=True, description="メール認証を必須にするか")
    auth_method: AuthMethod = Field(default=AuthMethod.INTERNAL, description="認証方式")
    external_auth_config: Optional[Dict[str, Any]] = Field(default=None, description="外部認証設定")
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    @before_event(Insert)
    def before_insert(self):
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    @before_event(Update)
    def before_update(self):
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """JSONシリアライズ用の辞書を返す"""
        return {
            "is_private": self.is_private,
            "max_members": self.max_members,
            "allow_registration": self.allow_registration,
            "require_email_verification": self.require_email_verification,
            "auth_method": self.auth_method.value,
            "external_auth_config": self.external_auth_config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Server(Document):
    """サーバーモデル"""
    name: str = Field(..., min_length=1, max_length=100, description="サーバー名")
    description: str = Field(..., min_length=1, max_length=500, description="サーバーの説明")
    logo_url: Optional[str] = Field(default=None, description="ロゴ画像のURL")
    language: str = Field(default="ja", description="サーバーの言語設定")
    status: ServerStatus = Field(default=ServerStatus.ACTIVE, description="サーバーの状態")
    categories: List[str] = Field(default_factory=list, description="カテゴリ一覧")
    settings: Optional[ServerSettings] = Field(default=None, description="サーバー設定")
    member_count: int = Field(default=0, ge=0, description="現在のメンバー数")
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
        # デフォルト設定を作成
        if self.settings is None:
            self.settings = ServerSettings()
    
    @before_event(Update)
    def before_update(self):
        self.updated_at = datetime.now()
    
    def update_member_count(self, count: int):
        """メンバー数を更新する"""
        self.member_count = max(0, count)
    
    def increment_member_count(self):
        """メンバー数を1増やす"""
        self.member_count += 1
    
    def decrement_member_count(self):
        """メンバー数を1減らす"""
        self.member_count = max(0, self.member_count - 1)
    
    def can_accept_new_members(self) -> bool:
        """新しいメンバーを受け入れられるかチェック"""
        if not self.settings:
            return True
        return self.member_count < self.settings.max_members
    
    def set_status(self, status: ServerStatus):
        """サーバーの状態を設定する"""
        self.status = status
    
    def add_category(self, category: str):
        """カテゴリを追加する"""
        if category not in self.categories:
            self.categories.append(category)
    
    def remove_category(self, category: str):
        """カテゴリを削除する"""
        if category in self.categories:
            self.categories.remove(category)
    
    def to_dict(self) -> Dict[str, Any]:
        """JSONシリアライズ用の辞書を返す"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "logo_url": self.logo_url,
            "language": self.language,
            "status": self.status.value,
            "categories": self.categories,
            "settings": self.settings.to_dict() if self.settings else None,
            "member_count": self.member_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
    
    def to_dict_public(self) -> Dict[str, Any]:
        """公開用の辞書を返す（機密情報を除外）"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "logo_url": self.logo_url,
            "language": self.language,
            "status": self.status.value,
            "categories": self.categories,
            "member_count": self.member_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    async def create_server(
        cls,
        name: str,
        description: str,
        logo_url: Optional[str] = None,
        language: str = "ja",
        categories: Optional[List[str]] = None,
        settings: Optional[ServerSettings] = None
    ) -> "Server":
        """新しいサーバーを作成する"""
        server = cls(
            name=name,
            description=description,
            logo_url=logo_url,
            language=language,
            categories=categories or [],
            settings=settings or ServerSettings()
        )
        await server.insert()
        return server
    
    @classmethod
    async def find_active_server(cls) -> Optional["Server"]:
        """アクティブなサーバーを検索する（通常は1つだけ）"""
        return await cls.find_one(cls.is_deleted == False)
    
    @classmethod
    async def update_settings(cls, settings_data: Dict[str, Any]) -> Optional["Server"]:
        """サーバー設定を更新する"""
        server = await cls.find_active_server()
        if server:
            if server.settings:
                # 既存の設定を更新
                for key, value in settings_data.items():
                    if hasattr(server.settings, key):
                        setattr(server.settings, key, value)
            else:
                # 新しい設定を作成
                server.settings = ServerSettings(**settings_data)
            await server.save()
        return server
