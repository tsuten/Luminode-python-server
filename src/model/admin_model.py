from datetime import datetime
from beanie import Document, before_event, Insert, Update
from typing import Dict, Any, Optional
from pydantic import Field, EmailStr
import bcrypt
from enum import Enum

class AdminRole(str, Enum):
    """管理者の役割"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"

class Admin(Document):
    """管理者モデル（管理パネル専用）"""
    username: str = Field(..., min_length=3, max_length=50, description="管理者のユーザー名")
    email: EmailStr = Field(..., description="管理者のメールアドレス")
    password_hash: str = Field(..., description="ハッシュ化されたパスワード")
    password2_hash: str = Field(..., description="ハッシュ化されたセカンダリパスワード")
    role: AdminRole = Field(default=AdminRole.ADMIN, description="管理者の役割")
    is_active: bool = Field(default=True, description="アカウントがアクティブかどうか")
    last_login: Optional[datetime] = Field(default=None, description="最終ログイン日時")
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
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """パスワードをハッシュ化する"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        """パスワードを検証する"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    @classmethod
    async def create_admin(
        cls, 
        username: str, 
        email: str, 
        password: str, 
        password2: str,
        role: AdminRole = AdminRole.ADMIN
    ) -> "Admin":
        """新しい管理者を作成する"""
        # パスワードのハッシュ化
        password_hash = cls.hash_password(password)
        password2_hash = cls.hash_password(password2)
        
        # 管理者インスタンスを作成
        admin = cls(
            username=username,
            email=email,
            password_hash=password_hash,
            password2_hash=password2_hash,
            role=role
        )
        
        # データベースに保存
        await admin.insert()
        return admin
    
    def verify_passwords(self, password: str, password2: str) -> bool:
        """両方のパスワードを検証する"""
        return (
            self.verify_password(password, self.password_hash) and
            self.verify_password(password2, self.password2_hash)
        )
    
    def update_last_login(self):
        """最終ログイン日時を更新する"""
        self.last_login = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """JSONシリアライズ用の辞書を返す（パスワードハッシュは除外）"""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
    
    def to_dict_without_sensitive(self) -> Dict[str, Any]:
        """機密情報を除外した辞書を返す"""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    async def find_by_username(cls, username: str) -> Optional["Admin"]:
        """ユーザー名で管理者を検索する"""
        return await cls.find_one(cls.username == username, cls.is_deleted == False)
    
    @classmethod
    async def find_by_email(cls, email: str) -> Optional["Admin"]:
        """メールアドレスで管理者を検索する"""
        return await cls.find_one(cls.email == email, cls.is_deleted == False)
    
    @classmethod
    async def authenticate(cls, username: str, password: str) -> Optional["Admin"]:
        """管理者の認証を行う"""
        admin = await cls.find_by_username(username)
        if admin and admin.is_active and admin.verify_password(password, admin.password_hash):
            admin.update_last_login()
            await admin.save()
            return admin
        return None
