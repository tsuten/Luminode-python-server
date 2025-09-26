#!/usr/bin/env python3
"""
画像API のテストスクリプト

開発時の動作確認用のスクリプトです。
実際のHTTPリクエストを送信して画像APIの動作をテストします。
"""

import asyncio
import httpx
import base64
import json
from pathlib import Path

# テスト用の小さなPNG画像データ（1x1ピクセル）
TEST_PNG_DATA = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB\x60\x82'

BASE_URL = "http://localhost:8000"

async def test_image_validation():
    """画像バリデーション機能のテスト"""
    print("=== 画像バリデーションテスト ===")
    
    try:
        from src.utils.image_utils import validate_image
        
        result = await validate_image(TEST_PNG_DATA, "test.png")
        print(f"バリデーション結果: {'成功' if result.is_valid else '失敗'}")
        
        if result.file_info:
            print("ファイル情報:")
            for key, value in result.file_info.items():
                print(f"  {key}: {value}")
        
        if result.errors:
            print("エラー:")
            for error in result.errors:
                print(f"  - {error.message}")
        
        if result.warnings:
            print("警告:")
            for warning in result.warnings:
                print(f"  - {warning}")
                
    except Exception as e:
        print(f"テスト中にエラーが発生しました: {e}")
    
    print()


async def get_auth_token():
    """認証トークンを取得（テスト用）"""
    # 実際の認証APIを使用してトークンを取得
    # この例では、既存のユーザーでログインしてトークンを取得
    try:
        async with httpx.AsyncClient() as client:
            # ここは実際の認証システムに合わせて調整が必要
            response = await client.post(f"{BASE_URL}/auth/login", json={
                "username": "testuser",
                "password": "testpass"
            })
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("access_token")
            else:
                print(f"認証に失敗しました: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"認証中にエラーが発生しました: {e}")
        return None


async def test_image_upload():
    """画像アップロードAPIのテスト"""
    print("=== 画像アップロードAPIテスト ===")
    
    # 認証トークンを取得
    token = await get_auth_token()
    if not token:
        print("認証トークンを取得できませんでした。テストをスキップします。")
        return None
    
    try:
        # テスト用のチャンネルIDを設定（実際のチャンネルIDに変更が必要）
        channel_id = "channel:test_channel_id"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # ファイルアップロード
            files = {
                "file": ("test.png", TEST_PNG_DATA, "image/png")
            }
            data = {
                "channel_id": channel_id,
                "alt_text": "テスト画像",
                "description": "APIテスト用の画像です"
            }
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            response = await client.post(
                f"{BASE_URL}/api/images/upload",
                files=files,
                data=data,
                headers=headers
            )
            
            print(f"ステータスコード: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("アップロード成功:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result.get("data", {}).get("id", "").replace("image:", "")
            else:
                print(f"アップロード失敗: {response.text}")
                return None
                
    except Exception as e:
        print(f"アップロード中にエラーが発生しました: {e}")
        return None


async def test_image_download(image_id: str):
    """画像ダウンロードAPIのテスト"""
    if not image_id:
        return
    
    print("=== 画像ダウンロードAPIテスト ===")
    
    token = await get_auth_token()
    if not token:
        print("認証トークンを取得できませんでした。テストをスキップします。")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            response = await client.get(
                f"{BASE_URL}/api/images/download/{image_id}",
                headers=headers
            )
            
            print(f"ステータスコード: {response.status_code}")
            
            if response.status_code == 200:
                print(f"ダウンロード成功: {len(response.content)} bytes")
                print(f"Content-Type: {response.headers.get('content-type')}")
                
                # ファイルとして保存
                with open(f"downloaded_{image_id}.png", "wb") as f:
                    f.write(response.content)
                print(f"downloaded_{image_id}.png として保存しました")
            else:
                print(f"ダウンロード失敗: {response.text}")
                
    except Exception as e:
        print(f"ダウンロード中にエラーが発生しました: {e}")


async def test_image_list():
    """画像一覧APIのテスト"""
    print("=== 画像一覧APIテスト ===")
    
    token = await get_auth_token()
    if not token:
        print("認証トークンを取得できませんでした。テストをスキップします。")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            response = await client.get(
                f"{BASE_URL}/api/images/list?limit=5",
                headers=headers
            )
            
            print(f"ステータスコード: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("一覧取得成功:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"一覧取得失敗: {response.text}")
                
    except Exception as e:
        print(f"一覧取得中にエラーが発生しました: {e}")


async def main():
    """メインテスト関数"""
    print("画像APIテストを開始します...\n")
    
    # 1. バリデーションテスト
    await test_image_validation()
    
    # 2. アップロードテスト
    image_id = await test_image_upload()
    print()
    
    # 3. ダウンロードテスト
    if image_id:
        await test_image_download(image_id)
        print()
    
    # 4. 一覧テスト
    await test_image_list()
    
    print("\n🎉 テスト完了!")


if __name__ == "__main__":
    asyncio.run(main())
