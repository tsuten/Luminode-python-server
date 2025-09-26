"""
画像アップロード・管理API

画像のアップロード、ダウンロード、削除、一覧取得など、
画像関連の操作を提供するHTTP APIエンドポイントです。
"""

import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Optional, List
import io
from bson import ObjectId

from schema.image_schema import (
    ImageUploadRequest, ImageUploadResponse, ImageListResponse, 
    ImageUpdateRequest, BaseResponse, ImageStatsResponse,
    ThumbnailRequest
)
from model.image_model import Image
from utils.image_utils import validate_image, create_thumbnail, ImageMetadataExtractor
from storage import get_storage
from utils.error_formatter import format_exception_for_response
from utils.nest_pydantic_errors import nest_pydantic_errors
from internal_auth.jwt_service import JWTService
from model.user_model import User
from model.channel_model import Channel


router = APIRouter()


async def get_current_user(request: Request) -> User:
    """認証されたユーザーを取得"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="認証が必要です")
    
    token = auth_header.split(" ")[1]
    payload = JWTService.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="無効なトークンです")
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="無効なトークンです")
    
    # JWTのuser_idは実際にはauth_idなので、auth_idで検索
    from uuid import UUID
    user = await User.find_by_auth_id(UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    return user


@router.post("/upload", response_model=BaseResponse)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    channel_id: str = Form(...),
    alt_text: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    画像をアップロード
    
    - **file**: アップロードする画像ファイル
    - **channel_id**: アップロード先のチャンネルID  
    - **alt_text**: 代替テキスト（任意）
    - **description**: 画像の説明（任意）
    """
    try:
        # チャンネルIDの形式チェック
        if not channel_id.startswith("channel:"):
            channel_id = f"channel:{channel_id}"
        
        # チャンネルの存在確認
        from utils.extract_elements_from_id import extract_elements_from_id_safe
        channel_parts = extract_elements_from_id_safe(channel_id)
        channel_type, channel_object_id = channel_parts[0], channel_parts[1]
        
        if channel_type != "channel" or not channel_object_id:
            raise HTTPException(status_code=400, detail="無効なチャンネルIDです")
        
        # ObjectIdに変換してチャンネルを取得
        try:
            channel_object_id_obj = ObjectId(channel_object_id)
            channel = await Channel.get(channel_object_id_obj)
        except Exception:
            raise HTTPException(status_code=400, detail="無効なチャンネルID形式です")
        
        if not channel:
            raise HTTPException(status_code=404, detail="チャンネルが見つかりません")
        
        # ファイルデータを読み取り
        file_data = await file.read()
        if not file_data:
            raise HTTPException(status_code=400, detail="ファイルが空です")
        
        # ファイル検証
        validation_result = await validate_image(file_data, file.filename or "unknown")
        if not validation_result.is_valid:
            error_messages = [error.message for error in validation_result.errors]
            raise HTTPException(status_code=400, detail=f"画像バリデーションエラー: {', '.join(error_messages)}")
        
        # ストレージにアップロード
        storage = get_storage()
        upload_result = await storage.upload(
            file_data, 
            file.filename or "image", 
            validation_result.file_info.get("detected_mime_type", file.content_type)
        )
        
        if not upload_result.success:
            raise HTTPException(status_code=500, detail=f"ファイルアップロードに失敗しました: {upload_result.error}")
        
        # サムネイル生成
        thumbnail_storage_id = None
        thumbnail_width = None
        thumbnail_height = None
        
        try:
            thumbnail_data = await create_thumbnail(file_data, 150, 150)
            thumbnail_result = await storage.upload(
                thumbnail_data,
                f"thumb_{file.filename or 'image'}",
                "image/jpeg"
            )
            if thumbnail_result.success:
                thumbnail_storage_id = thumbnail_result.file_id
                thumbnail_width = 150
                thumbnail_height = 150
        except Exception as e:
            print(f"サムネイル生成に失敗しました: {e}")
        
        # データベースに保存
        image = Image(
            storage_file_id=upload_result.file_id,
            original_filename=file.filename or "unknown",
            filename=upload_result.metadata.get("filename", file.filename or "unknown"),
            file_size=validation_result.file_info.get("file_size", len(file_data)),
            mime_type=validation_result.file_info.get("detected_mime_type", file.content_type),
            width=validation_result.file_info.get("width"),
            height=validation_result.file_info.get("height"),
            thumbnail_storage_id=thumbnail_storage_id,
            thumbnail_width=thumbnail_width,
            thumbnail_height=thumbnail_height,
            uploaded_by=f"user:{current_user.id}",
            channel_id=channel_id,
            alt_text=alt_text,
            description=description
        )
        
        await image.insert()
        
        # レスポンス用のURLを生成
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        download_url = image.get_download_url(base_url)
        thumbnail_url = image.get_thumbnail_url(base_url) if thumbnail_storage_id else None
        
        response_data = ImageUploadResponse(
            id=f"image:{image.id}",
            original_filename=image.original_filename,
            file_size=image.file_size,
            mime_type=image.mime_type,
            width=image.width,
            height=image.height,
            download_url=download_url,
            thumbnail_url=thumbnail_url,
            uploaded_by=image.uploaded_by,
            channel_id=image.channel_id,
            alt_text=image.alt_text,
            description=image.description,
            created_at=image.created_at.isoformat()
        )
        
        return BaseResponse(success=True, data=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        raise HTTPException(status_code=500, detail=f"画像アップロードに失敗しました: {str(e)}")


@router.get("/download/{image_id}")
async def download_image(image_id: str, current_user: User = Depends(get_current_user)):
    """
    画像をダウンロード
    
    - **image_id**: 画像のID（image:を除いたObjectId）
    """
    try:
        # 画像情報を取得
        try:
            image_object_id = ObjectId(image_id)
            image = await Image.get(image_object_id)
        except Exception:
            raise HTTPException(status_code=400, detail="無効な画像ID形式です")
        
        if not image or image.is_deleted:
            raise HTTPException(status_code=404, detail="画像が見つかりません")
        
        # ストレージから画像データを取得
        storage = get_storage()
        image_data = await storage.download(image.storage_file_id)
        if not image_data:
            raise HTTPException(status_code=404, detail="画像ファイルが見つかりません")
        
        # ストリーミングレスポンスとして返す
        return StreamingResponse(
            io.BytesIO(image_data),
            media_type=image.mime_type,
            headers={
                "Content-Disposition": f"inline; filename={image.original_filename}",
                "Cache-Control": "public, max-age=3600"  # 1時間キャッシュ
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"画像ダウンロードに失敗しました: {str(e)}")


@router.get("/thumbnail/{image_id}")
async def download_thumbnail(image_id: str, current_user: User = Depends(get_current_user)):
    """
    画像のサムネイルをダウンロード
    
    - **image_id**: 画像のID（image:を除いたObjectId）
    """
    try:
        # 画像情報を取得
        try:
            image_object_id = ObjectId(image_id)
            image = await Image.get(image_object_id)
        except Exception:
            raise HTTPException(status_code=400, detail="無効な画像ID形式です")
        
        if not image or image.is_deleted:
            raise HTTPException(status_code=404, detail="画像が見つかりません")
        
        if not image.thumbnail_storage_id:
            raise HTTPException(status_code=404, detail="サムネイルが見つかりません")
        
        # ストレージからサムネイルデータを取得
        storage = get_storage()
        thumbnail_data = await storage.download(image.thumbnail_storage_id)
        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="サムネイルファイルが見つかりません")
        
        # ストリーミングレスポンスとして返す
        return StreamingResponse(
            io.BytesIO(thumbnail_data),
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f"inline; filename=thumb_{image.original_filename}",
                "Cache-Control": "public, max-age=86400"  # 24時間キャッシュ
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"サムネイルダウンロードに失敗しました: {str(e)}")


@router.get("/list", response_model=BaseResponse)
async def list_images(
    channel_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    画像一覧を取得
    
    - **channel_id**: チャンネルID（指定した場合、そのチャンネルの画像のみ）
    - **user_id**: ユーザーID（指定した場合、そのユーザーの画像のみ）
    - **limit**: 取得件数（最大100）
    - **offset**: オフセット
    """
    try:
        limit = min(limit, 100)  # 最大100件に制限
        
        if channel_id and user_id:
            raise HTTPException(status_code=400, detail="channel_idとuser_idは同時に指定できません")
        
        if channel_id:
            if not channel_id.startswith("channel:"):
                channel_id = f"channel:{channel_id}"
            images = await Image.find_by_channel(channel_id, limit, offset)
        elif user_id:
            if not user_id.startswith("user:"):
                user_id = f"user:{user_id}"
            images = await Image.find_by_user(user_id, limit, offset)
        else:
            # 全画像を取得（削除されていないもののみ）
            images = await Image.find(
                Image.is_deleted == False
            ).skip(offset).limit(limit).sort(-Image.created_at).to_list()
        
        # 総件数を取得
        if channel_id:
            total_count = await Image.count(Image.channel_id == channel_id, Image.is_deleted == False)
        elif user_id:
            total_count = await Image.count(Image.uploaded_by == user_id, Image.is_deleted == False)
        else:
            total_count = await Image.count(Image.is_deleted == False)
        
        # レスポンスデータを作成
        image_responses = []
        for image in images:
            image_responses.append(ImageUploadResponse(
                id=f"image:{image.id}",
                original_filename=image.original_filename,
                file_size=image.file_size,
                mime_type=image.mime_type,
                width=image.width,
                height=image.height,
                download_url=f"/api/images/download/{image.id}",
                thumbnail_url=f"/api/images/thumbnail/{image.id}" if image.thumbnail_storage_id else None,
                uploaded_by=image.uploaded_by,
                channel_id=image.channel_id or "",
                alt_text=image.alt_text,
                description=image.description,
                created_at=image.created_at.isoformat()
            ))
        
        list_response = ImageListResponse(
            images=image_responses,
            total_count=total_count,
            has_more=offset + limit < total_count,
            offset=offset,
            limit=limit
        )
        
        return BaseResponse(success=True, data=list_response)
        
    except HTTPException:
        raise
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        raise HTTPException(status_code=500, detail=f"画像一覧取得に失敗しました: {str(e)}")


@router.delete("/{image_id}", response_model=BaseResponse)
async def delete_image(image_id: str, current_user: User = Depends(get_current_user)):
    """
    画像を削除
    
    - **image_id**: 画像のID（image:を除いたObjectId）
    """
    try:
        # 画像情報を取得
        try:
            image_object_id = ObjectId(image_id)
            image = await Image.get(image_object_id)
        except Exception:
            raise HTTPException(status_code=400, detail="無効な画像ID形式です")
        
        if not image or image.is_deleted:
            raise HTTPException(status_code=404, detail="画像が見つかりません")
        
        # 権限チェック（アップロードしたユーザーのみ削除可能）
        if image.uploaded_by != f"user:{current_user.id}":
            raise HTTPException(status_code=403, detail="この画像を削除する権限がありません")
        
        # ソフト削除
        image.soft_delete()
        await image.save()
        
        return BaseResponse(success=True, data={"message": "画像が削除されました"})
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"画像削除に失敗しました: {str(e)}")


@router.put("/{image_id}", response_model=BaseResponse)
async def update_image(
    image_id: str, 
    update_data: ImageUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    画像情報を更新
    
    - **image_id**: 画像のID（image:を除いたObjectId）
    - **update_data**: 更新するデータ
    """
    try:
        # 画像情報を取得
        try:
            image_object_id = ObjectId(image_id)
            image = await Image.get(image_object_id)
        except Exception:
            raise HTTPException(status_code=400, detail="無効な画像ID形式です")
        
        if not image or image.is_deleted:
            raise HTTPException(status_code=404, detail="画像が見つかりません")
        
        # 権限チェック（アップロードしたユーザーのみ更新可能）
        if image.uploaded_by != f"user:{current_user.id}":
            raise HTTPException(status_code=403, detail="この画像を更新する権限がありません")
        
        # 更新
        if update_data.alt_text is not None:
            image.alt_text = update_data.alt_text
        if update_data.description is not None:
            image.description = update_data.description
        
        await image.save()
        
        return BaseResponse(success=True, data=image.to_dict_public())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"画像更新に失敗しました: {str(e)}")


@router.get("/stats", response_model=BaseResponse)
async def get_image_stats(current_user: User = Depends(get_current_user)):
    """
    画像統計情報を取得
    """
    try:
        # 基本統計
        total_images = await Image.count(Image.is_deleted == False)
        
        # 今日と今週の統計は簡略化
        stats_response = ImageStatsResponse(
            total_images=total_images,
            total_size_bytes=0,  # 実装を簡略化
            total_size_mb=0.0,
            by_format={},
            by_user={},
            uploaded_today=0,
            uploaded_this_week=0
        )
        
        return BaseResponse(success=True, data=stats_response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"統計情報取得に失敗しました: {str(e)}")
