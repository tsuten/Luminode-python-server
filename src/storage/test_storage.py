"""
ストレージ抽象化レイヤーのテスト

開発時の動作確認用の簡単なテストスクリプトです。
"""

import asyncio
import os
import tempfile
import shutil
from pathlib import Path

from .local_storage import LocalStorage
from .storage_factory import get_storage


async def test_local_storage():
    """ローカルストレージの基本機能をテスト"""
    print("=== ローカルストレージテスト開始 ===")
    
    # テスト用の一時ディレクトリを作成
    test_dir = tempfile.mkdtemp(prefix="storage_test_")
    print(f"テストディレクトリ: {test_dir}")
    
    try:
        # LocalStorageインスタンスを作成
        storage = LocalStorage(base_path=test_dir)
        
        # テスト用のファイルデータ
        test_data = "Hello, World! これはテスト用の画像データです。".encode('utf-8')
        test_filename = "test_image.jpg"
        test_mime_type = "image/jpeg"
        
        print("\n1. ファイルアップロードテスト")
        result = await storage.upload(test_data, test_filename, test_mime_type)
        
        if result.success:
            print(f"✓ アップロード成功: file_id = {result.file_id}")
            file_id = result.file_id
        else:
            print(f"✗ アップロード失敗: {result.error}")
            return
        
        print("\n2. ファイル存在確認テスト")
        exists = await storage.exists(file_id)
        print(f"✓ ファイル存在確認: {exists}")
        
        print("\n3. メタデータ取得テスト")
        metadata = await storage.get_metadata(file_id)
        if metadata:
            print(f"✓ メタデータ取得成功:")
            print(f"  - ファイル名: {metadata.filename}")
            print(f"  - サイズ: {metadata.size} bytes")
            print(f"  - MIMEタイプ: {metadata.mime_type}")
            print(f"  - アップロード日時: {metadata.uploaded_at}")
        else:
            print("✗ メタデータ取得失敗")
        
        print("\n4. ファイルダウンロードテスト")
        downloaded_data = await storage.download(file_id)
        if downloaded_data:
            print(f"✓ ダウンロード成功: {len(downloaded_data)} bytes")
            if downloaded_data == test_data:
                print("✓ データ整合性確認: データが一致しています")
            else:
                print("✗ データ整合性確認: データが不一致です")
        else:
            print("✗ ダウンロード失敗")
        
        print("\n5. ストレージ情報取得テスト")
        storage_info = storage.get_storage_info()
        print(f"✓ ストレージ情報:")
        for key, value in storage_info.items():
            print(f"  - {key}: {value}")
        
        print("\n6. ファイル削除テスト")
        deleted = await storage.delete(file_id)
        if deleted:
            print("✓ ファイル削除成功")
            
            # 削除後の存在確認
            exists_after = await storage.exists(file_id)
            print(f"✓ 削除後の存在確認: {exists_after}")
        else:
            print("✗ ファイル削除失敗")
        
    finally:
        # テストディレクトリをクリーンアップ
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"\nテストディレクトリを削除しました: {test_dir}")
    
    print("\n=== ローカルストレージテスト完了 ===")


async def test_storage_factory():
    """ストレージファクトリのテスト"""
    print("\n=== ストレージファクトリテスト開始 ===")
    
    # 環境変数を設定してローカルストレージを使用
    os.environ["STORAGE_TYPE"] = "local"
    os.environ["LOCAL_STORAGE_PATH"] = "test_uploads"
    
    try:
        # ファクトリからストレージを取得
        storage = get_storage()
        print(f"✓ ストレージ取得成功: {type(storage).__name__}")
        
        # 簡単な動作確認
        test_data = b"Factory test data"
        result = await storage.upload(test_data, "factory_test.txt", "text/plain")
        
        if result.success:
            print(f"✓ ファクトリ経由でのアップロード成功: {result.file_id}")
            
            # クリーンアップ
            await storage.delete(result.file_id)
            print("✓ テストファイル削除完了")
        else:
            print(f"✗ ファクトリ経由でのアップロード失敗: {result.error}")
    
    finally:
        # テストディレクトリをクリーンアップ
        test_path = Path("test_uploads")
        if test_path.exists():
            shutil.rmtree(test_path, ignore_errors=True)
            print("✓ テスト用アップロードディレクトリを削除しました")
    
    print("=== ストレージファクトリテスト完了 ===")


async def main():
    """メインテスト関数"""
    print("ストレージ抽象化レイヤーのテストを開始します...\n")
    
    await test_local_storage()
    await test_storage_factory()
    
    print("\n🎉 全てのテストが完了しました！")


if __name__ == "__main__":
    asyncio.run(main())
