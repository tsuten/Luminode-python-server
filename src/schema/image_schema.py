"""
画像関連のスキーマ定義

画像アップロード、レスポンス、バリデーションに関する
Pydanticスキーマを定義します。
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ImageFormat(str, Enum):
    """サポートされている画像フォーマット"""
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    WEBP = "image/webp"


class ImageUploadRequest(BaseModel):
    """画像アップロードリクエスト"""
    channel_id: str = Field(..., description="アップロード先のチャンネルID")
    alt_text: Optional[str] = Field(default=None, max_length=500, description="代替テキスト")
    description: Optional[str] = Field(default=None, max_length=1000, description="画像の説明")

    @validator('channel_id')
    def validate_channel_id(cls, v):
        """チャンネルIDの形式をバリデーション"""
        if not v.startswith('channel:'):
            raise ValueError('チャンネルIDは "channel:" で始まる必要があります')
        return v


class ImageUploadResponse(BaseModel):
    """画像アップロードレスポンス"""
    id: str = Field(..., description="画像ID")
    original_filename: str = Field(..., description="元のファイル名")
    file_size: int = Field(..., description="ファイルサイズ（バイト）")
    mime_type: str = Field(..., description="MIMEタイプ")
    width: Optional[int] = Field(default=None, description="画像の幅")
    height: Optional[int] = Field(default=None, description="画像の高さ")
    download_url: str = Field(..., description="ダウンロードURL")
    thumbnail_url: Optional[str] = Field(default=None, description="サムネイルURL")
    uploaded_by: str = Field(..., description="アップロードしたユーザー")
    channel_id: str = Field(..., description="関連するチャンネルID")
    alt_text: Optional[str] = Field(default=None, description="代替テキスト")
    description: Optional[str] = Field(default=None, description="画像の説明")
    created_at: str = Field(..., description="作成日時")


class ImageListResponse(BaseModel):
    """画像一覧レスポンス"""
    images: List[ImageUploadResponse] = Field(..., description="画像リスト")
    total_count: int = Field(..., description="総件数")
    has_more: bool = Field(..., description="さらにデータがあるかどうか")
    offset: int = Field(..., description="オフセット")
    limit: int = Field(..., description="リミット")


class ImageUpdateRequest(BaseModel):
    """画像情報更新リクエスト"""
    alt_text: Optional[str] = Field(default=None, max_length=500, description="代替テキスト")
    description: Optional[str] = Field(default=None, max_length=1000, description="画像の説明")


class ImageValidationError(BaseModel):
    """画像バリデーションエラー"""
    code: str = Field(..., description="エラーコード")
    message: str = Field(..., description="エラーメッセージ")
    details: Optional[Dict[str, Any]] = Field(default=None, description="詳細情報")


class ImageValidationResult(BaseModel):
    """画像バリデーション結果"""
    is_valid: bool = Field(..., description="バリデーション結果")
    errors: List[ImageValidationError] = Field(default_factory=list, description="エラーリスト")
    warnings: List[str] = Field(default_factory=list, description="警告リスト")
    file_info: Optional[Dict[str, Any]] = Field(default=None, description="ファイル情報")


class ThumbnailRequest(BaseModel):
    """サムネイル生成リクエスト"""
    width: int = Field(default=150, ge=50, le=500, description="サムネイルの幅")
    height: int = Field(default=150, ge=50, le=500, description="サムネイルの高さ")
    quality: int = Field(default=80, ge=20, le=100, description="JPEG品質（20-100）")


class ImageStatsResponse(BaseModel):
    """画像統計レスポンス"""
    total_images: int = Field(..., description="総画像数")
    total_size_bytes: int = Field(..., description="総サイズ（バイト）")
    total_size_mb: float = Field(..., description="総サイズ（MB）")
    by_format: Dict[str, int] = Field(..., description="フォーマット別件数")
    by_user: Dict[str, int] = Field(..., description="ユーザー別件数")
    uploaded_today: int = Field(..., description="今日アップロードされた件数")
    uploaded_this_week: int = Field(..., description="今週アップロードされた件数")


# レスポンス用の基底スキーマ
class BaseResponse(BaseModel):
    """API レスポンスの基底クラス"""
    success: bool = Field(..., description="処理の成功可否")
    data: Optional[Any] = Field(default=None, description="レスポンスデータ")
    error: Optional[str] = Field(default=None, description="エラーメッセージ")
    errors: Optional[List[Dict[str, Any]]] = Field(default=None, description="詳細エラー情報")


class ImageUploadSuccessResponse(BaseResponse):
    """画像アップロード成功レスポンス"""
    data: ImageUploadResponse


class ImageListSuccessResponse(BaseResponse):
    """画像一覧取得成功レスポンス"""
    data: ImageListResponse


class ImageStatsSuccessResponse(BaseResponse):
    """画像統計取得成功レスポンス"""
    data: ImageStatsResponse
