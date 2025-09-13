from datetime import datetime
from beanie import Document, before_event, Insert, Update
from typing import Dict, Any, Optional
from pydantic import Field, EmailStr
import bcrypt
from uuid import UUID, uuid4

class Auth(Document):
    """内部認証データモデル（ユーザーデータと分離）"""
    user_id: UUID = Field(..., description="関連するユーザーのID")
    username: str = Field(..., min_length=3, max_length=50, description="ログイン用ユーザー名")
    email: EmailStr = Field(..., description="メールアドレス")
    password_hash: str = Field(..., description="ハッシュ化されたパスワード")
    is_active: bool = Field(default=True, description="アカウントがアクティブかどうか")
    is_verified: bool = Field(default=False, description="メール認証済みかどうか")
    verification_token: Optional[str] = Field(default=None, description="メール認証トークン")
    reset_token: Optional[str] = Field(default=None, description="パスワードリセットトークン")
    reset_token_expires: Optional[datetime] = Field(default=None, description="リセットトークンの有効期限")
    last_login: Optional[datetime] = Field(default=None, description="最終ログイン日時")
    failed_login_attempts: int = Field(default=0, description="ログイン失敗回数")
    locked_until: Optional[datetime] = Field(default=None, description="アカウントロック解除日時")
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
        # 認証トークンを生成
        if not self.verification_token:
            self.verification_token = str(uuid4())
    
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
    
    def is_account_locked(self) -> bool:
        """アカウントがロックされているかチェック"""
        if self.locked_until is None:
            return False
        return datetime.now() < self.locked_until
    
    def increment_failed_attempts(self):
        """ログイン失敗回数を増やす"""
        self.failed_login_attempts += 1
        # 5回失敗したら30分ロック
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.now().replace(minute=datetime.now().minute + 30)
    
    def reset_failed_attempts(self):
        """ログイン失敗回数をリセット"""
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def update_last_login(self):
        """最終ログイン日時を更新"""
        self.last_login = datetime.now()
        self.reset_failed_attempts()
    
    def generate_reset_token(self) -> str:
        """パスワードリセットトークンを生成"""
        self.reset_token = str(uuid4())
        # 1時間の有効期限
        self.reset_token_expires = datetime.now().replace(hour=datetime.now().hour + 1)
        return self.reset_token
    
    def is_reset_token_valid(self, token: str) -> bool:
        """リセットトークンが有効かチェック"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        return (
            self.reset_token == token and
            datetime.now() < self.reset_token_expires
        )
    
    def verify_email(self, token: str) -> bool:
        """メール認証を行う"""
        if self.verification_token == token:
            self.is_verified = True
            self.verification_token = None
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """JSONシリアライズ用の辞書を返す（パスワードハッシュは除外）"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "failed_login_attempts": self.failed_login_attempts,
            "is_locked": self.is_account_locked(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    async def create_auth(
        cls,
        user_id: UUID,
        username: str,
        email: str,
        password: str
    ) -> "Auth":
        """新しい認証データを作成する"""
        password_hash = cls.hash_password(password)
        
        auth = cls(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash
        )
        
        await auth.insert()
        return auth
    
    @classmethod
    async def find_by_username(cls, username: str) -> Optional["Auth"]:
        """ユーザー名で認証データを検索する"""
        return await cls.find_one(cls.username == username, cls.is_deleted == False)
    
    @classmethod
    async def find_by_email(cls, email: str) -> Optional["Auth"]:
        """メールアドレスで認証データを検索する"""
        return await cls.find_one(cls.email == email, cls.is_deleted == False)
    
    @classmethod
    async def find_by_user_id(cls, user_id: UUID) -> Optional["Auth"]:
        """ユーザーIDで認証データを検索する"""
        return await cls.find_one(cls.user_id == user_id, cls.is_deleted == False)
    
    @classmethod
    async def authenticate(cls, username: str, password: str) -> Optional["Auth"]:
        """認証を行う"""
        auth = await cls.find_by_username(username)
        if not auth:
            # ユーザー名で見つからない場合はメールアドレスで試す
            auth = await cls.find_by_email(username)
        
        if not auth:
            return None
        
        # アカウントがロックされているかチェック
        if auth.is_account_locked():
            return None
        
        # アカウントがアクティブかチェック
        if not auth.is_active:
            return None
        
        # パスワード検証
        if auth.verify_password(password, auth.password_hash):
            auth.update_last_login()
            await auth.save()
            return auth
        else:
            auth.increment_failed_attempts()
            await auth.save()
            return None