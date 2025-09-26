"""
ストレージファクトリ

設定に基づいて適切なストレージ実装を提供します。
環境設定により、ローカルストレージまたは外部ストレージを選択できます。
"""

from typing import Optional
import os
from enum import Enum

from .storage_interface import StorageInterface
from .local_storage import LocalStorage


class StorageType(Enum):
    """サポートされているストレージタイプ"""
    LOCAL = "local"
    S3 = "s3"
    AZURE = "azure"
    GCS = "gcs"


class StorageFactory:
    """ストレージインスタンスを作成・管理するファクトリクラス"""
    
    _instance: Optional['StorageFactory'] = None
    _storage: Optional[StorageInterface] = None

    def __new__(cls):
        """シングルトンパターンで実装"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_storage(cls) -> StorageInterface:
        """
        設定に基づいてストレージインスタンスを取得
        
        Returns:
            StorageInterface: 設定されたストレージ実装
        """
        instance = cls()
        
        if instance._storage is None:
            instance._storage = instance._create_storage()
        
        return instance._storage

    def _create_storage(self) -> StorageInterface:
        """設定に基づいてストレージインスタンスを作成"""
        # 環境変数から設定を読み取り
        storage_type = os.getenv("STORAGE_TYPE", "local").lower()
        
        if storage_type == StorageType.LOCAL.value:
            return self._create_local_storage()
        elif storage_type == StorageType.S3.value:
            return self._create_s3_storage()
        elif storage_type == StorageType.AZURE.value:
            return self._create_azure_storage()
        elif storage_type == StorageType.GCS.value:
            return self._create_gcs_storage()
        else:
            # デフォルトはローカルストレージ
            return self._create_local_storage()

    def _create_local_storage(self) -> LocalStorage:
        """ローカルストレージを作成"""
        base_path = os.getenv("LOCAL_STORAGE_PATH", "uploads")
        return LocalStorage(base_path=base_path)

    def _create_s3_storage(self) -> StorageInterface:
        """AWS S3ストレージを作成（将来実装）"""
        # TODO: S3Storageクラスの実装が必要
        raise NotImplementedError("S3ストレージは将来実装予定です")

    def _create_azure_storage(self) -> StorageInterface:
        """Azure Blob Storageを作成（将来実装）"""
        # TODO: AzureStorageクラスの実装が必要
        raise NotImplementedError("Azure Blob Storageは将来実装予定です")

    def _create_gcs_storage(self) -> StorageInterface:
        """Google Cloud Storageを作成（将来実装）"""
        # TODO: GCSStorageクラスの実装が必要
        raise NotImplementedError("Google Cloud Storageは将来実装予定です")

    @classmethod
    def reset(cls):
        """テスト用：ファクトリをリセット"""
        instance = cls()
        instance._storage = None


# 便利な関数として提供
def get_storage() -> StorageInterface:
    """
    現在設定されているストレージインスタンスを取得
    
    Returns:
        StorageInterface: ストレージ実装
    """
    return StorageFactory.get_storage()
