from events import ee
from sockets import sio
from schema.message_schema import MessageResponse
from pydantic import BaseModel
from typing import Any
from utils.nest_pydantic_errors import nest_pydantic_errors
from utils.error_formatter import format_exception_for_response

class BaseResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: Any | None = None

@ee.on("message_creation")
async def message_creation_event(message: MessageResponse):
    print("message creation event")

    print(message.sent_to)

    await sio.emit("message", BaseResponse(success=True, data=message.model_dump(mode="json")).model_dump(), room=message.sent_to)