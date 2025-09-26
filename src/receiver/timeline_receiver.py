from pydantic import BaseModel, field_validator
from typing import Any
from sockets import sio
from utils.error_formatter import format_exception_for_response
from utils.nest_pydantic_errors import nest_pydantic_errors
from model.message_model import Message
from utils.extract_elements_from_id import extract_elements_from_id
from datetime import datetime
class BaseResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: Any | None = None

class TimeLineSchema(BaseModel):
    channel_id: str
    limit: int = 10
    offset: int = 0

class GetTimelineSchema(BaseModel):
    channel_id: str
    until: datetime
    amount: int = 10
    
    @field_validator('until', mode='before')
    @classmethod
    def parse_until(cls, v):
        if isinstance(v, str):
            # "2025-09-26" 形式の文字列を datetime に変換
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                # 他の形式も試す
                try:
                    return datetime.strptime(v, "%Y-%m-%d")
                except ValueError:
                    raise ValueError(f"Invalid date format: {v}")
        return v

@sio.event
async def get_timeline(sid, data):
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
        validated_data = GetTimelineSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    try:
        id_type, id_value = extract_elements_from_id(validated_data.channel_id)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    try:
        messages = (await Message.find(Message.is_deleted == False, Message.sent_to == "channel:" + id_value, Message.created_at < validated_data.until).sort(-Message.created_at).to_list())[:validated_data.amount]

        timeline_length = len(messages)
        return BaseResponse(success=True, data={
            "timeline": [message.to_dict() for message in messages],
            "timeline_length": timeline_length
        }).model_dump()
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        await sio.emit("system", BaseResponse(success=False, error=error_payload).model_dump(), room=sid)
        return BaseResponse(success=False, error=error_payload).model_dump()



    