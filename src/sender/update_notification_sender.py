from events import ee
from sockets import sio
from schema.update_notification_schema import UpdateNotification
from pydantic import BaseModel
from typing import Any
from utils.nest_pydantic_errors import nest_pydantic_errors
from utils.error_formatter import format_exception_for_response
from utils.extract_elements_from_id import validate_id

class BaseResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: Any | None = None

@ee.on("update_notification")
async def update_notification_event(update_notification: UpdateNotification):
    print("update notification event")

    if not validate_id(update_notification.id):
        print(BaseResponse(success=False, error="Invalid id format").model_dump())
        return

    await sio.emit("update_notification", BaseResponse(success=True, data=update_notification.model_dump(mode="json")).model_dump())