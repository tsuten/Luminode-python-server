from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID
import os

class JWTService:
    """JWT認証サービス（python-jose使用）"""
    
    # 環境変数から秘密鍵を取得（デフォルト値も設定）
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24時間
    REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7日
    
    @classmethod
    def create_access_token(cls, user_id: UUID, auth_id: str, additional_data: Optional[Dict[str, Any]] = None) -> str:
        """
        アクセストークンを作成する
        
        Args:
            user_id: ユーザーID
            auth_id: 認証ID
            additional_data: 追加のペイロードデータ
        
        Returns:
            JWT アクセストークン
        """
        expire = datetime.utcnow() + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "user_id": str(user_id),
            "auth_id": auth_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        if additional_data:
            payload.update(additional_data)
        
        return jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
    
    @classmethod
    def create_refresh_token(cls, user_id: UUID, auth_id: str) -> str:
        """
        リフレッシュトークンを作成する
        
        Args:
            user_id: ユーザーID
            auth_id: 認証ID
        
        Returns:
            JWT リフレッシュトークン
        """
        expire = datetime.utcnow() + timedelta(days=cls.REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "user_id": str(user_id),
            "auth_id": auth_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        return jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
    
    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        トークンを検証する
        
        Args:
            token: 検証するトークン
        
        Returns:
            デコードされたペイロード（無効な場合はNone）
        """
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            return payload
        except JWTError:
            # 無効なトークンまたは有効期限切れ
            return None
    
    @classmethod
    def verify_access_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        アクセストークンを検証する
        
        Args:
            token: 検証するアクセストークン
        
        Returns:
            デコードされたペイロード（無効な場合はNone）
        """
        payload = cls.verify_token(token)
        if payload and payload.get("type") == "access":
            return payload
        return None
    
    @classmethod
    def verify_refresh_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        リフレッシュトークンを検証する
        
        Args:
            token: 検証するリフレッシュトークン
        
        Returns:
            デコードされたペイロード（無効な場合はNone）
        """
        payload = cls.verify_token(token)
        if payload and payload.get("type") == "refresh":
            return payload
        return None
    
    @classmethod
    def create_token_pair(cls, user_id: UUID, auth_id: str, additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        アクセストークンとリフレッシュトークンのペアを作成する
        
        Args:
            user_id: ユーザーID
            auth_id: 認証ID
            additional_data: 追加のペイロードデータ
        
        Returns:
            アクセストークンとリフレッシュトークンのペア
        """
        access_token = cls.create_access_token(user_id, auth_id, additional_data)
        refresh_token = cls.create_refresh_token(user_id, auth_id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": cls.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
        }
    
    @classmethod
    def refresh_access_token(cls, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        リフレッシュトークンを使用してアクセストークンを更新する
        
        Args:
            refresh_token: リフレッシュトークン
        
        Returns:
            新しいトークンペア（無効な場合はNone）
        """
        payload = cls.verify_refresh_token(refresh_token)
        if not payload:
            return None
        
        user_id = UUID(payload["user_id"])
        auth_id = payload["auth_id"]
        
        return cls.create_token_pair(user_id, auth_id)
    
    @classmethod
    def get_user_id_from_token(cls, token: str) -> Optional[UUID]:
        """
        トークンからユーザーIDを取得する
        
        Args:
            token: アクセストークン
        
        Returns:
            ユーザーID（無効な場合はNone）
        """
        payload = cls.verify_access_token(token)
        if payload:
            try:
                return UUID(payload["user_id"])
            except (ValueError, KeyError):
                return None
        return None
    
    @classmethod
    def get_auth_id_from_token(cls, token: str) -> Optional[str]:
        """
        トークンから認証IDを取得する
        
        Args:
            token: アクセストークン
        
        Returns:
            認証ID（無効な場合はNone）
        """
        payload = cls.verify_access_token(token)
        if payload:
            return payload.get("auth_id")
        return None
