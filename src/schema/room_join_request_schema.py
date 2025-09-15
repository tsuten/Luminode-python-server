from pydantic import BaseModel

class RoomJoinRequestSchema(BaseModel):
    room_type: str
    room_id: str