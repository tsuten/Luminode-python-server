import asyncio
from typing import Optional

from pymongo import AsyncMongoClient
from pydantic import BaseModel

from beanie import Document, Indexed, init_beanie


class Category(BaseModel):
    name: str
    description: str


class Product(Document):
    name: str                          # You can use normal types just like in pydantic
    description: Optional[str] = None
    price: Indexed(float)              # You can also specify that a field should correspond to an index
    category: Category                 # You can include pydantic models as well

_client = None

async def init():
    db_name = "test"
    global _client
    if _client is None:
        print("init: loading mongo client")
        _client = AsyncMongoClient("mongodb://127.0.0.1:27017")
        print("init: loading beanie")
        await init_beanie(database=_client.db_name, document_models=[Product])

def get_client() -> AsyncMongoClient:
    if _client is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    return _client