"""
ストレージ抽象化レイヤー

このモジュールは、ファイル保存の抽象化を提供し、
開発環境でのローカルストレージと本番環境での外部ストレージ
（AWS S3、Azure Blob Storage、Google Cloud Storage等）
の切り替えを可能にします。
"""

from .storage_interface import StorageInterface, StorageResult, FileMetadata
from .local_storage import LocalStorage
from .storage_factory import StorageFactory, get_storage

__all__ = ["StorageInterface", "StorageResult", "FileMetadata", "LocalStorage", "StorageFactory", "get_storage"]
