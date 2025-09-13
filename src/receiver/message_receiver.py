from model.message_model import Message
from utils.error_formatter import format_exception_for_response
from utils.nest_pydantic_errors import nest_pydantic_errors
from datetime import datetime
from pydantic import BaseModel
from typing import Any
from sockets import sio
from schema.message_schema import MessageSchema
from pyee.asyncio import AsyncIOEventEmitter
from app import ee

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
        await sio.emit("system", BaseResponse(success=False, error=error_payload).model_dump(), room=sid)
        return

    send_to = "channel:" + data.get("send_to")
    sent_by = "user:" + str(user_id)
    
    message = Message(type=data.get("type"), content=data.get("content"), sent_by=sent_by, sent_to=send_to)
    ee.emit("test")
    await message.insert()
    
    # don't forget to convert to dict
    await sio.emit("system", BaseResponse(success=True, data=message.to_dict()).model_dump(), room=sid)