"""
ストレージの抽象インターフェース

ファイル保存・取得・削除の共通インターフェースを定義します。
将来的に異なるストレージバックエンド（Local、S3、Azure等）を
統一的に扱えるようにします。
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class StorageResult:
    """ストレージ操作の結果を表すクラス"""
    
    def __init__(self, success: bool, file_id: Optional[str] = None, 
                 error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.success = success
        self.file_id = file_id
        self.error = error
        self.metadata = metadata or {}


class FileMetadata:
    """ファイルのメタデータを表すクラス"""
    
    def __init__(self, filename: str, size: int, mime_type: str, 
                 uploaded_at: Optional[datetime] = None):
        self.filename = filename
        self.size = size
        self.mime_type = mime_type
        self.uploaded_at = uploaded_at or datetime.now()


class StorageInterface(ABC):
    """ストレージの抽象インターフェース"""

    @abstractmethod
    async def upload(self, file_data: bytes, filename: str, 
                    mime_type: str, metadata: Optional[Dict[str, Any]] = None) -> StorageResult:
        """
        ファイルをアップロードします
        
        Args:
            file_data: ファイルのバイナリデータ
            filename: オリジナルファイル名
            mime_type: ファイルのMIMEタイプ
            metadata: 追加のメタデータ
            
        Returns:
            StorageResult: アップロード結果
        """
        pass

    @abstractmethod
    async def download(self, file_id: str) -> Optional[bytes]:
        """
        ファイルをダウンロードします
        
        Args:
            file_id: ファイルの一意識別子
            
        Returns:
            Optional[bytes]: ファイルのバイナリデータ、存在しない場合はNone
        """
        pass

    @abstractmethod
    async def delete(self, file_id: str) -> bool:
        """
        ファイルを削除します
        
        Args:
            file_id: ファイルの一意識別子
            
        Returns:
            bool: 削除が成功した場合True
        """
        pass

    @abstractmethod
    async def get_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """
        ファイルのメタデータを取得します
        
        Args:
            file_id: ファイルの一意識別子
            
        Returns:
            Optional[FileMetadata]: ファイルのメタデータ、存在しない場合はNone
        """
        pass

    @abstractmethod
    async def exists(self, file_id: str) -> bool:
        """
        ファイルが存在するかチェックします
        
        Args:
            file_id: ファイルの一意識別子
            
        Returns:
            bool: ファイルが存在する場合True
        """
        pass

    def generate_file_id(self) -> str:
        """
        ユニークなファイルIDを生成します
        
        Returns:
            str: ユニークなファイルID
        """
        return str(uuid.uuid4())
