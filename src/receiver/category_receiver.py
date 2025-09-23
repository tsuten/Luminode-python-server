from typing import Any, Optional, List
from pydantic import BaseModel
from sockets import sio
from datetime import datetime

from model.category_model import Category
from model.channel_model import Channel
from utils.error_formatter import format_exception_for_response
from utils.nest_pydantic_errors import nest_pydantic_errors
from utils.extract_elements_from_id import extract_elements_from_id_safe


class BaseResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: Any | None = None


class CreateCategorySchema(BaseModel):
    name: str
    description: Optional[str] = None
    next_category_id: Optional[str] = None  # 形式: "category:{id}"


@sio.event
async def create_category(sid, data):
    try:
        payload = CreateCategorySchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    category = Category(
        name=payload.name,
        description=payload.description,
        channels_order=[],
        next_category_id=payload.next_category_id,
    )
    await category.insert()
    return BaseResponse(success=True, data=category.to_dict()).model_dump()


class UpdateCategorySchema(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    next_category_id: Optional[str] = None  # 形式: "category:{id}"


@sio.event
async def update_category(sid, data):
    try:
        payload = UpdateCategorySchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    # id は "category:{id}" を想定
    type_part, value_part = extract_elements_from_id_safe(payload.id)
    if type_part != "category" or not value_part:
        return BaseResponse(success=False, error="Invalid category id").model_dump()
    category = await Category.get(value_part)
    if not category or category.is_deleted:
        return BaseResponse(success=False, error="Category not found").model_dump()

    if payload.name is not None:
        category.name = payload.name
    if payload.description is not None:
        category.description = payload.description
    if payload.next_category_id is not None:
        category.next_category_id = payload.next_category_id

    category.updated_at = datetime.now()
    await category.save()
    return BaseResponse(success=True, data=category.to_dict()).model_dump()


class DeleteCategorySchema(BaseModel):
    id: str


@sio.event
async def delete_category(sid, data):
    try:
        payload = DeleteCategorySchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    category = await Category.get(payload.id)
    if not category or category.is_deleted:
        return BaseResponse(success=False, error="Category not found").model_dump()

    category.is_deleted = True
    category.deleted_at = datetime.now()
    await category.save()

    # ぶら下がっているチャンネルは未分類へ
    if category.channels_order:
        for ch_id in category.channels_order:
            channel = await Channel.get(ch_id)
            if channel and not channel.is_deleted:
                channel.category_id = None
                channel.updated_at = datetime.now()
                await channel.save()

    return BaseResponse(success=True, data=category.to_dict()).model_dump()


class ReorderCategoriesSchema(BaseModel):
    # target を prev の直後へ配置（prev が None の場合、先頭へ）
    target_category_id: str
    prev_category_id: Optional[str] = None

@sio.event
async def reorder_categories(sid, data):
    try:
        payload = ReorderCategoriesSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    # target_category_id は "category:{id}"
    t_type, t_value = extract_elements_from_id_safe(payload.target_category_id)
    if t_type != "category" or not t_value:
        return BaseResponse(success=False, error="Invalid target_category_id").model_dump()
    target = await Category.get(t_value)
    if not target or target.is_deleted:
        return BaseResponse(success=False, error="Category not found").model_dump()

    # 全カテゴリ取得して単方向リストを再配線
    categories = await Category.find(Category.is_deleted == False).to_list()

    # 現在の前ノードを探す
    prev_of_target: Optional[Category] = None
    # next_category_id も "category:{id}" 形式で保持
    formatted_target = f"category:{str(target.id)}"
    for c in categories:
        if c.next_category_id == formatted_target:
            prev_of_target = c
            break

    # いったん target をリストから外す
    if prev_of_target:
        prev_of_target.next_category_id = target.next_category_id
        await prev_of_target.save()

    # prev の直後に target を差し込む
    if payload.prev_category_id is None:
        # 先頭へ: target を新ヘッドにするため、他のどれも target.id を指さない状態になっていればOK
        # ヘッドに特別なフラグは持たないため、以降の探索で導出する
        pass
    else:
        p_type, p_value = extract_elements_from_id_safe(payload.prev_category_id)
        if p_type != "category" or not p_value:
            return BaseResponse(success=False, error="Invalid prev_category_id").model_dump()
        new_prev = next((c for c in categories if str(c.id) == p_value), None)
        if not new_prev or new_prev.is_deleted or str(new_prev.id) == str(target.id):
            return BaseResponse(success=False, error="Invalid prev_category_id").model_dump()
        target.next_category_id = new_prev.next_category_id
        new_prev.next_category_id = f"category:{str(target.id)}"
        await new_prev.save()

    await target.save()
    return BaseResponse(success=True, data={"target": str(target.id)}).model_dump()


class ReorderCategoryChannelsSchema(BaseModel):
    category_id: str
    ordered_channel_ids: List[str]

@sio.event
async def reorder_category_channels(sid, data):
    try:
        payload = ReorderCategoryChannelsSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    # ids は "category:{id}", "channel:{id}" 形式
    c_type, c_value = extract_elements_from_id_safe(payload.category_id)
    if c_type != "category" or not c_value:
        return BaseResponse(success=False, error="Invalid category_id").model_dump()
    category = await Category.get(c_value)
    if not category or category.is_deleted:
        return BaseResponse(success=False, error="Category not found").model_dump()

    # 同一カテゴリに属するチャンネルのみを許可
    for ch_id in payload.ordered_channel_ids:
        ct, cv = extract_elements_from_id_safe(ch_id)
        if ct != "channel" or not cv:
            return BaseResponse(success=False, error="Invalid channel in order").model_dump()
        ch = await Channel.get(cv)
        if not ch or ch.is_deleted or ch.category_id != f"category:{str(category.id)}":
            return BaseResponse(success=False, error="Invalid channel in order").model_dump()

    # 重複禁止
    if len(payload.ordered_channel_ids) != len(set(payload.ordered_channel_ids)):
        return BaseResponse(success=False, error="Duplicate channel ids").model_dump()

    # channels_order は "channel:{id}" の配列を保持
    category.channels_order = payload.ordered_channel_ids
    category.updated_at = datetime.now()
    await category.save()
    return BaseResponse(success=True, data=category.to_dict()).model_dump()

class AddChannelToCategorySchema(BaseModel):
    category_id: str
    channel_id: str


@sio.event
async def add_channel_to_category(sid, data):
    try:
        payload = AddChannelToCategorySchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    c_type, c_value = extract_elements_from_id_safe(payload.category_id)
    if c_type != "category" or not c_value:
        return BaseResponse(success=False, error="Invalid category_id").model_dump()
    category = await Category.get(c_value)
    if not category or category.is_deleted:
        return BaseResponse(success=False, error="Category not found").model_dump()

    ch_type, ch_value = extract_elements_from_id_safe(payload.channel_id)
    if ch_type != "channel" or not ch_value:
        return BaseResponse(success=False, error="Invalid channel_id").model_dump()
    channel = await Channel.get(ch_value)
    if not channel or channel.is_deleted:
        return BaseResponse(success=False, error="Channel not found").model_dump()

    # 既に同じカテゴリに属している場合はエラー
    if channel.category_id == f"category:{str(category.id)}":
        return BaseResponse(success=False, error="Channel is already in this category").model_dump()

    # 既存カテゴリから取り外し（別カテゴリにいた場合）
    if channel.category_id:
        # 旧カテゴリIDは "category:{id}" 形式
        old_ct, old_cv = extract_elements_from_id_safe(channel.category_id)
        old_cat = await Category.get(old_cv) if old_ct == "category" and old_cv else None
        if old_cat and not old_cat.is_deleted and old_cat.channels_order:
            formatted_channel = f"channel:{str(channel.id)}"
            if formatted_channel in old_cat.channels_order:
                old_cat.channels_order = [cid for cid in old_cat.channels_order if cid != formatted_channel]
                old_cat.updated_at = datetime.now()
                await old_cat.save()

    # 目的カテゴリの末尾へ（重複除去してから append）
    category.channels_order = category.channels_order or []
    formatted_channel = f"channel:{str(channel.id)}"
    if formatted_channel in category.channels_order:
        category.channels_order = [cid for cid in category.channels_order if cid != formatted_channel]
    category.channels_order.append(formatted_channel)
    category.updated_at = datetime.now()
    await category.save()

    # チャンネル側のカテゴリ参照を更新
    channel.category_id = f"category:{str(category.id)}"
    channel.updated_at = datetime.now()
    await channel.save()

    return BaseResponse(success=True, data={
        "category": category.to_dict(),
        "channel": channel.to_dict(),
    }).model_dump()