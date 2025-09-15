from model.channel_model import Channel
from utils.error_formatter import format_exception_for_response
from utils.nest_pydantic_errors import nest_pydantic_errors
from pydantic import BaseModel
from typing import Any
from sockets import sio
from schema.room_join_request_schema import RoomJoinRequestSchema

class BaseResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: Any | None = None

@sio.event
async def join_room(sid, data):
    try:
        RoomJoinRequestSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        await sio.emit("system", BaseResponse(success=False, error=error_payload).model_dump(), room=sid)
        return

    room_type = data.get("room_type")
    room_id = data.get("room_id")

    if room_type != "channel":
        await sio.emit("system", BaseResponse(success=False, error="Only channel rooms are allowed").model_dump(), room=sid)
        return

    channel = await Channel.get(room_id)
    if not channel:
        await sio.emit("system", BaseResponse(success=False, error="Channel not found").model_dump(), room=sid)
        return

    room_name = f"{room_type}:{room_id}"
    await sio.enter_room(sid, room_name)
    await sio.emit("system", BaseResponse(success=True, data={"room_joined": room_name}).model_dump(), room=sid)

@sio.event
async def leave_room(sid, data):
    try:
        RoomJoinRequestSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        await sio.emit("system", BaseResponse(success=False, error=error_payload).model_dump(), room=sid)
        return

    room_type = data.get("room_type")
    room_id = data.get("room_id")

    if room_type != "channel":
        await sio.emit("system", BaseResponse(success=False, error="Only channel rooms are allowed").model_dump(), room=sid)
        return

    channel = await Channel.get(room_id)
    if not channel:
        await sio.emit("system", BaseResponse(success=False, error="Channel not found").model_dump(), room=sid)
        return

    room_name = f"{room_type}:{room_id}"
    await sio.leave_room(sid, room_name)
    await sio.emit("system", BaseResponse(success=True, data={"room_left": room_name}).model_dump(), room=sid)