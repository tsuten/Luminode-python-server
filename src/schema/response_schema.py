from pydantic import BaseModel
from typing import Any, Optional

class ErrorResponse(BaseModel):
    success: bool = False
    error: str