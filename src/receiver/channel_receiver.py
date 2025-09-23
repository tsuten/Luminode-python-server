from model.channel_model import Channel
from utils.error_formatter import format_exception_for_response
from utils.nest_pydantic_errors import nest_pydantic_errors
from datetime import datetime
from pydantic import BaseModel
from typing import Any, Optional
from sockets import sio
from pyee.asyncio import AsyncIOEventEmitter
from app import ee
from schema.channel_schema import ChannelSchema
from model.category_model import Category
from utils.extract_elements_from_id import extract_elements_from_id_safe
from utils.extract_elements_from_id import extract_elements_from_id

class BaseResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: Any | None = None

@sio.event
async def create_channel(sid, data):
    try:
        ChannelSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    # category_id は "category:{id}" を許容
    raw_category_id = data.get("category_id")
    if raw_category_id:
        ct, cv = extract_elements_from_id_safe(raw_category_id)
        if ct != "category" or not cv:
            return BaseResponse(success=False, error="Invalid category_id").model_dump()
        formatted_category_id = raw_category_id
    else:
        formatted_category_id = None

    channel = Channel(name=data.get("name"), description=data.get("description"), type=data.get("type"), category_id=formatted_category_id)
    ee.emit("channel_created")
    await channel.insert()

    # カテゴリに所属する場合は channels_order に末尾追加
    if channel.category_id:
        _, category_value = extract_elements_from_id_safe(channel.category_id)
        category = await Category.get(category_value)
        if category and not category.is_deleted:
            category.channels_order = (category.channels_order or []) + [f"channel:{str(channel.id)}"]
            category.updated_at = datetime.now()
            await category.save()

    # シンプルにto_dict()メソッドを使用
    return BaseResponse(success=True, data=channel.to_dict()).model_dump()


class UpdateChannelSchema(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None

@sio.event
async def update_channel(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        return BaseResponse(success=False, error="Authentication required").model_dump()
    user_id = session.get('user_id')
    if not user_id:
        return BaseResponse(success=False, error="User ID not found").model_dump()
    # boilerplate ends

    try:
        UpdateChannelSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    try:
        id_type, id_value = extract_elements_from_id(data.get("id"))
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()
    
    if not id_type or not id_value:
        return BaseResponse(success=False, error="Invalid id format").model_dump()
    
    if id_type != "channel":
        return BaseResponse(success=False, error="Invalid id format").model_dump()

    try:
        channel = await Channel.get(id_value)
        if not channel:
            return BaseResponse(success=False, error="Channel not found").model_dump()
        
        # Update only provided fields
        if data.get("name") is not None:
            channel.name = data.get("name")
        if data.get("description") is not None:
            channel.description = data.get("description")
        
        channel.updated_at = datetime.now()
        await channel.save()
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    ee.emit("channel_updated", channel.to_dict())
    return BaseResponse(success=True, data=channel.to_dict()).model_dump()

class DeleteChannelSchema(BaseModel):
    id: str

@sio.event
async def delete_channel(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        return BaseResponse(success=False, error="Authentication required").model_dump()
    user_id = session.get('user_id')
    if not user_id:
        return BaseResponse(success=False, error="User ID not found").model_dump()
    # boilerplate ends

    try:
        DeleteChannelSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    try:
        id_type, id_value = extract_elements_from_id(data.get("id"))
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()
    
    if not id_type or not id_value:
        return BaseResponse(success=False, error="Invalid id format").model_dump()
    
    if id_type != "channel":
        return BaseResponse(success=False, error="Invalid id format").model_dump()
    
    try:
        channel = await Channel.get(id_value)
        if not channel:
            return BaseResponse(success=False, error="Channel not found").model_dump()
        
        if channel.is_deleted:
            return BaseResponse(success=False, error="Channel already deleted").model_dump()
        
        # Soft delete
        channel.is_deleted = True
        channel.deleted_at = datetime.now()
        await channel.save()
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    ee.emit("channel_deleted", channel.to_dict())
    return BaseResponse(success=True, data=channel.to_dict()).model_dump()