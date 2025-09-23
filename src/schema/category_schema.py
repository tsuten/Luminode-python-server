from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    channels_order: Optional[List[str]] = None
    next_category_id: Optional[str] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    channels_order: List[str]
    next_category_id: Optional[str] = None
    created_at: datetime


