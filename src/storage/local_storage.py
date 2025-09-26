"""
ローカルファイルシステムストレージ実装

開発環境用のローカルファイルシステムを使用したストレージ実装です。
ファイルは指定されたディレクトリに保存され、メタデータはJSONファイルで管理されます。
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# aiofilesがない場合の代替実装
try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False

from .storage_interface import StorageInterface, StorageResult, FileMetadata


class LocalStorage(StorageInterface):
    """ローカルファイルシステム用のストレージ実装"""
    
    def __init__(self, base_path: str = "uploads"):
        """
        LocalStorageを初期化します
        
        Args:
            base_path: ファイル保存のベースディレクトリ
        """
        self.base_path = Path(base_path)
        self.files_dir = self.base_path / "files"
        self.metadata_dir = self.base_path / "metadata"
        
        # ディレクトリを作成
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, file_id: str) -> Path:
        """ファイルIDからファイルパスを取得"""
        return self.files_dir / file_id

    def _get_metadata_path(self, file_id: str) -> Path:
        """ファイルIDからメタデータファイルパスを取得"""
        return self.metadata_dir / f"{file_id}.json"

    async def upload(self, file_data: bytes, filename: str, 
                    mime_type: str, metadata: Optional[Dict[str, Any]] = None) -> StorageResult:
        """ファイルをローカルファイルシステムにアップロード"""
        try:
            # ユニークなファイルIDを生成
            file_id = self.generate_file_id()
            file_path = self._get_file_path(file_id)
            metadata_path = self._get_metadata_path(file_id)
            
            # ファイルデータを保存
            if HAS_AIOFILES:
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(file_data)
            else:
                # 同期的なファイル書き込み（開発時用）
                with open(file_path, 'wb') as f:
                    f.write(file_data)
            
            # メタデータを保存
            file_metadata = {
                "file_id": file_id,
                "filename": filename,
                "size": len(file_data),
                "mime_type": mime_type,
                "uploaded_at": datetime.now().isoformat(),
                "storage_path": str(file_path),
                "metadata": metadata or {}
            }
            
            if HAS_AIOFILES:
                async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(file_metadata, ensure_ascii=False, indent=2))
            else:
                # 同期的なファイル書き込み（開発時用）
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    f.write(json.dumps(file_metadata, ensure_ascii=False, indent=2))
            
            return StorageResult(
                success=True,
                file_id=file_id,
                metadata=file_metadata
            )
            
        except Exception as e:
            return StorageResult(
                success=False,
                error=f"ファイルアップロードに失敗しました: {str(e)}"
            )

    async def download(self, file_id: str) -> Optional[bytes]:
        """ファイルをローカルファイルシステムからダウンロード"""
        try:
            file_path = self._get_file_path(file_id)
            
            if not file_path.exists():
                return None
            
            if HAS_AIOFILES:
                async with aiofiles.open(file_path, 'rb') as f:
                    return await f.read()
            else:
                # 同期的なファイル読み込み（開発時用）
                with open(file_path, 'rb') as f:
                    return f.read()
                
        except Exception:
            return None

    async def delete(self, file_id: str) -> bool:
        """ファイルをローカルファイルシステムから削除"""
        try:
            file_path = self._get_file_path(file_id)
            metadata_path = self._get_metadata_path(file_id)
            
            success = True
            
            # ファイルが存在する場合削除
            if file_path.exists():
                file_path.unlink()
            
            # メタデータファイルが存在する場合削除
            if metadata_path.exists():
                metadata_path.unlink()
            
            return success
            
        except Exception:
            return False

    async def get_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """ファイルのメタデータを取得"""
        try:
            metadata_path = self._get_metadata_path(file_id)
            
            if not metadata_path.exists():
                return None
            
            if HAS_AIOFILES:
                async with aiofiles.open(metadata_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
            else:
                # 同期的なファイル読み込み（開発時用）
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    data = json.loads(content)
                
            return FileMetadata(
                filename=data["filename"],
                size=data["size"],
                mime_type=data["mime_type"],
                uploaded_at=datetime.fromisoformat(data["uploaded_at"])
            )
                
        except Exception:
            return None

    async def exists(self, file_id: str) -> bool:
        """ファイルが存在するかチェック"""
        file_path = self._get_file_path(file_id)
        return file_path.exists()

    async def cleanup_orphaned_files(self) -> int:
        """
        孤立したファイル（メタデータのないファイル）をクリーンアップ
        
        Returns:
            int: 削除されたファイル数
        """
        cleaned_count = 0
        
        try:
            for file_path in self.files_dir.iterdir():
                if file_path.is_file():
                    file_id = file_path.name
                    metadata_path = self._get_metadata_path(file_id)
                    
                    # メタデータファイルが存在しない場合、孤立ファイルとして削除
                    if not metadata_path.exists():
                        file_path.unlink()
                        cleaned_count += 1
                        
        except Exception:
            pass
            
        return cleaned_count

    def get_storage_info(self) -> Dict[str, Any]:
        """ストレージの使用状況情報を取得"""
        try:
            total_files = len(list(self.files_dir.glob("*")))
            total_size = sum(f.stat().st_size for f in self.files_dir.glob("*") if f.is_file())
            
            return {
                "storage_type": "local",
                "base_path": str(self.base_path),
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2)
            }
        except Exception:
            return {
                "storage_type": "local",
                "base_path": str(self.base_path),
                "error": "ストレージ情報の取得に失敗しました"
            }
