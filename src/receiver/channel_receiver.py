from model.channel_model import Channel
from utils.error_formatter import format_exception_for_response
from utils.nest_pydantic_errors import nest_pydantic_errors
from datetime import datetime
from pydantic import BaseModel
from typing import Any
from sockets import sio
from pyee.asyncio import AsyncIOEventEmitter
from app import ee
from schema.channel_schema import ChannelSchema

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
        await sio.emit("system", BaseResponse(success=False, error=error_payload).model_dump(), room=sid)
        return

    channel = Channel(name=data.get("name"), description=data.get("description"), type=data.get("type"))
    ee.emit("channel_created")
    await channel.insert()

    # シンプルにto_dict()メソッドを使用
    await sio.emit("system", BaseResponse(success=True, data=channel.to_dict()).model_dump(), room=sid)