from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

# Pydanticモデル定義
class BaseResponse(BaseModel):
    success: bool
    data: Any = None
    error: Any = None

class DataSchema(BaseModel):
    type: str
    required: bool
    description: Optional[str] = None
    minimum: Optional[int] = None
    maximum: Optional[int] = None

class StepResponse(BaseResponse):
    step: int
    step_description: str
    data_schema: Dict[str, DataSchema]

class CreateSuperAdminRequest(BaseModel):
    username: str
    password: str
    password2: str
    email: str

class ServerInfoRequest(BaseModel):
    name: str
    description: str
    logo: Optional[str] = None
    language: Optional[str] = None
    max_members: Optional[int] = None
    categories: Optional[List[str]] = None

class ServerSettings(BaseModel):
    is_private: bool = Field(..., description="Whether the server is private or public")
    max_members: int = Field(..., ge=1, le=100000, description="Maximum number of members allowed (1-100000)")

class ServerSettingsRequest(BaseModel):
    settings: ServerSettings
