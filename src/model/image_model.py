"""
画像データモデル

アップロードされた画像ファイルのメタデータと
ストレージ情報を管理するためのデータモデルです。
"""

from datetime import datetime
from beanie import Document, before_event, Insert, Update
from typing import Dict, Any, Optional
from uuid import UUID
from pydantic import Field


class Image(Document):
    """画像データモデル"""
    
    # ファイル情報
    storage_file_id: str = Field(..., description="ストレージシステムでのファイルID")
    original_filename: str = Field(..., description="元のファイル名")
    filename: str = Field(..., description="保存時のファイル名")
    
    # ファイル属性
    file_size: int = Field(..., description="ファイルサイズ（バイト）")
    mime_type: str = Field(..., description="MIMEタイプ")
    
    # 画像属性
    width: Optional[int] = Field(default=None, description="画像の幅（ピクセル）")
    height: Optional[int] = Field(default=None, description="画像の高さ（ピクセル）")
    
    # サムネイル情報
    thumbnail_storage_id: Optional[str] = Field(default=None, description="サムネイルのストレージID")
    thumbnail_width: Optional[int] = Field(default=None, description="サムネイルの幅")
    thumbnail_height: Optional[int] = Field(default=None, description="サムネイルの高さ")
    
    # アップロード情報
    uploaded_by: str = Field(..., description="アップロードしたユーザー（user:{id}形式）")
    channel_id: Optional[str] = Field(default=None, description="関連するチャンネルID（channel:{id}形式）")
    
    # メタデータ
    alt_text: Optional[str] = Field(default=None, max_length=500, description="代替テキスト")
    description: Optional[str] = Field(default=None, max_length=1000, description="画像の説明")
    
    # システム情報
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None

    @before_event(Insert)
    def before_insert(self):
        """挿入前の処理"""
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.is_deleted = False
        self.deleted_at = None

    @before_event(Update)
    def before_update(self):
        """更新前の処理"""
        self.updated_at = datetime.now()

    def soft_delete(self):
        """ソフト削除"""
        self.is_deleted = True
        self.deleted_at = datetime.now()

    def restore(self):
        """削除を取り消し"""
        self.is_deleted = False
        self.deleted_at = None

    def to_dict(self) -> Dict[str, Any]:
        """JSONシリアライズ用の辞書を返す"""
        return {
            "id": "image:" + str(self.id),
            "storage_file_id": self.storage_file_id,
            "original_filename": self.original_filename,
            "filename": self.filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "thumbnail_storage_id": self.thumbnail_storage_id,
            "thumbnail_width": self.thumbnail_width,
            "thumbnail_height": self.thumbnail_height,
            "uploaded_by": self.uploaded_by,
            "channel_id": self.channel_id,
            "alt_text": self.alt_text,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }

    def to_dict_public(self) -> Dict[str, Any]:
        """公開用の辞書を返す（内部情報を除外）"""
        return {
            "id": "image:" + str(self.id),
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "thumbnail_width": self.thumbnail_width,
            "thumbnail_height": self.thumbnail_height,
            "uploaded_by": self.uploaded_by,
            "alt_text": self.alt_text,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    async def find_by_user(cls, user_id: str, limit: int = 50, offset: int = 0):
        """ユーザーがアップロードした画像を取得"""
        user_prefix = f"user:{user_id}" if not user_id.startswith("user:") else user_id
        return await cls.find(
            cls.uploaded_by == user_prefix,
            cls.is_deleted == False
        ).skip(offset).limit(limit).sort(-cls.created_at).to_list()

    @classmethod
    async def find_by_channel(cls, channel_id: str, limit: int = 50, offset: int = 0):
        """チャンネルの画像を取得"""
        channel_prefix = f"channel:{channel_id}" if not channel_id.startswith("channel:") else channel_id
        return await cls.find(
            cls.channel_id == channel_prefix,
            cls.is_deleted == False
        ).skip(offset).limit(limit).sort(-cls.created_at).to_list()

    def get_download_url(self, base_url: str = "") -> str:
        """ダウンロードURLを生成"""
        image_id = str(self.id)
        return f"{base_url}/api/images/download/{image_id}"

    def get_thumbnail_url(self, base_url: str = "") -> Optional[str]:
        """サムネイルURLを生成"""
        if not self.thumbnail_storage_id:
            return None
        image_id = str(self.id)
        return f"{base_url}/api/images/thumbnail/{image_id}"
