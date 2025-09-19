from model.message_model import Message
from utils.error_formatter import format_exception_for_response
from utils.nest_pydantic_errors import nest_pydantic_errors
from datetime import datetime
from pydantic import BaseModel
from typing import Any
from sockets import sio
from schema.message_schema import MessageSchema, MessageResponse
from pyee.asyncio import AsyncIOEventEmitter
from app import ee
from model.channel_model import Channel
from utils.extract_elements_from_id import extract_elements_from_id
class BaseResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: Any | None = None

@sio.event
async def send_message(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        await sio.emit("system", BaseResponse(success=False, error="Authentication required").model_dump(), room=sid)
        return
    user_id = session.get('user_id')
    if not user_id:
        await sio.emit("system", BaseResponse(success=False, error="User ID not found").model_dump(), room=sid)
        return
    # boilerplate ends

    try:
        MessageSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    send_to_type, send_to_id = extract_elements_from_id(data.get("send_to"))
    if not send_to_type or not send_to_id:
        return BaseResponse(success=False, error="Invalid send_to format").model_dump()

    if send_to_type == "channel":
        try:
            channel = await Channel.get(send_to_id)
            if not channel:
                return BaseResponse(success=False, error="Channel not found").model_dump()
        except Exception as e:
            error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
            return BaseResponse(success=False, error=error_payload).model_dump()

    send_to = send_to_type + ":" + str(send_to_id)
    sent_by = "user:" + str(user_id)
    
    message = Message(type=data.get("type"), content=data.get("content"), sent_by=sent_by, sent_to=send_to)

    try:
        await message.insert()
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()
    
    ee.emit("message_creation", MessageResponse(**message.to_dict()))
    # don't forget to convert to dict
    await sio.emit("system", BaseResponse(success=True, data=message.to_dict()).model_dump(), room=sid)
    return BaseResponse(success=True, data=message.to_dict()).model_dump()

@sio.event
async def get_messages(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        await sio.emit("system", BaseResponse(success=False, error="Authentication required").model_dump(), room=sid)
        return
    user_id = session.get('user_id')
    if not user_id:
        await sio.emit("system", BaseResponse(success=False, error="User ID not found").model_dump(), room=sid)
        return
    # boilerplate ends

    try:
        messages = await Message.find(Message.is_deleted == False).sort(-Message.created_at).to_list()

        messages_length = len(messages)
        return BaseResponse(success=True, data={
            "messages": [message.to_dict() for message in messages],
            "messages_length": messages_length
        }).model_dump()
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        await sio.emit("system", BaseResponse(success=False, error=error_payload).model_dump(), room=sid)
        return BaseResponse(success=False, error=error_payload).model_dump()

class UpdateMessageSchema(BaseModel):
    id: str
    content: str

@sio.event
async def update_message(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        await sio.emit("system", BaseResponse(success=False, error="Authentication required").model_dump(), room=sid)
        return
    user_id = session.get('user_id')
    if not user_id:
        await sio.emit("system", BaseResponse(success=False, error="User ID not found").model_dump(), room=sid)
        return
    # boilerplate ends

    try:
        id_type, id_value = extract_elements_from_id(data.get("id"))
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()
    if not id_type or not id_value:
        return BaseResponse(success=False, error="Invalid id format").model_dump()
    if id_type != "message":
        return BaseResponse(success=False, error="Invalid id format").model_dump()



    try:
        UpdateMessageSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()
    
    try:
        message = await Message.get(id_value)
        if not message:
            return BaseResponse(success=False, error="Message not found").model_dump()
        message.content = data.get("content")
        message.updated_at = datetime.now()
        await message.save()
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()
    
    ee.emit("message_update", MessageResponse(**message.to_dict()))
    await sio.emit("system", BaseResponse(success=True, data=message.to_dict()).model_dump(), room=sid)
    return BaseResponse(success=True, data=message.to_dict()).model_dump()

class DeleteMessageSchema(BaseModel):
    id: str

@sio.event
async def delete_message(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        await sio.emit("system", BaseResponse(success=False, error="Authentication required").model_dump(), room=sid)
        return
    user_id = session.get('user_id')
    if not user_id:
        await sio.emit("system", BaseResponse(success=False, error="User ID not found").model_dump(), room=sid)
        return
    # boilerplate ends

    try:
        DeleteMessageSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    id_type, id_value = extract_elements_from_id(data.get("id"))
    if not id_type or not id_value:
        return BaseResponse(success=False, error="Invalid id format").model_dump()
    if id_type != "message":
        return BaseResponse(success=False, error="Invalid id format").model_dump()
    
    try:
        message = await Message.get(id_value)
        if not message:
            return BaseResponse(success=False, error="Message not found").model_dump()
        if message.is_deleted:
            return BaseResponse(success=False, error="Message already deleted").model_dump()
        message.is_deleted = True
        message.deleted_at = datetime.now()
        await message.save()
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()
    
    ee.emit("message_delete", MessageResponse(**message.to_dict()))
    await sio.emit("system", BaseResponse(success=True, data=message.to_dict()).model_dump(), room=sid)
    return BaseResponse(success=True, data=message.to_dict()).model_dump()

class RestoreMessageSchema(BaseModel):
    id: str

@sio.event
async def restore_message(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        await sio.emit("system", BaseResponse(success=False, error="Authentication required").model_dump(), room=sid)
        return
    user_id = session.get('user_id')
    if not user_id:
        await sio.emit("system", BaseResponse(success=False, error="User ID not found").model_dump(), room=sid)
        return
    # boilerplate ends

    try:
        RestoreMessageSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    id_type, id_value = extract_elements_from_id(data.get("id"))
    if not id_type or not id_value:
        return BaseResponse(success=False, error="Invalid id format").model_dump()
    if id_type != "message":
        return BaseResponse(success=False, error="Invalid id format").model_dump()
    
    try:
        message = await Message.get(id_value)
        if not message:
            return BaseResponse(success=False, error="Message not found").model_dump()
        if not message.is_deleted:
            return BaseResponse(success=False, error="Message isn't deleted").model_dump()
        message.is_deleted = False
        message.deleted_at = None
        await message.save()
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()
    
    ee.emit("message_restore", MessageResponse(**message.to_dict()))
    await sio.emit("system", BaseResponse(success=True, data=message.to_dict()).model_dump(), room=sid)
    return BaseResponse(success=True, data=message.to_dict()).model_dump()