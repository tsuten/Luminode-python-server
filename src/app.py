from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
from typing import Any
from utils.nest_pydantic_errors import nest_pydantic_errors
from utils.error_formatter import format_exception_for_response
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from contextlib import asynccontextmanager
from beanie import init_beanie
from model.message_model import Message
from model.channel_model import Channel
from model.user_model import User
from model.admin_model import Admin
from model.server_model import Server, ServerSettings
from model.setup_model import SetupProgress
from internal_auth.auth_model import Auth
from sockets import sio
import socketio
from events import ee

@asynccontextmanager
async def lifespan(app):
    # Create Async PyMongo client
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=2000)
    print("lifespan: mongo client creation success")
    db = client.get_database("test")
    await init_beanie(database=db, document_models=[Message, Channel, User, Admin, Server, ServerSettings, SetupProgress, Auth])
    print("lifespan: beanie initialization success")
    yield
    client.close()

app_fastapi = FastAPI(lifespan=lifespan)

# setup socketio
app_socketio = socketio.ASGIApp(sio, other_asgi_app=app_fastapi)

class BaseResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: Any | None = None

class Item(BaseModel):
    name: str
    chinpo: int

class ItemResponse(BaseResponse):
    data: Item

@app_fastapi.post("/" , response_model=ItemResponse)
async def read_root(item: Item):
    return ItemResponse(success=True, data=item)

@sio.event
async def connect(sid, environ, auth=None):
    """Socket.IO接続時の認証"""
    print(f"connect attempt {sid}")
    
    try:
        # パラメータからトークンを取得
        token = None
        if auth and isinstance(auth, dict):
            token = auth.get('token')
        
        # 環境変数からクエリパラメータも確認
        if not token and environ.get('QUERY_STRING'):
            from urllib.parse import parse_qs
            query_params = parse_qs(environ['QUERY_STRING'])
            if 'token' in query_params:
                token = query_params['token'][0]
        
        if not token:
            print(f"connect rejected {sid}: No token provided")
            return False  # 接続拒否
        
        # JWT認証サービスを使用してトークンを検証
        from internal_auth.jwt_service import JWTService
        from internal_auth.auth_model import Auth
        from model.user_model import User
        
        payload = JWTService.verify_access_token(token)
        if not payload:
            print(f"connect rejected {sid}: Invalid token")
            return False  # 接続拒否
        
        # ユーザー情報を取得
        user_id = payload.get('user_id')
        auth_id = payload.get('auth_id')
        
        if not user_id or not auth_id:
            print(f"connect rejected {sid}: Invalid token payload")
            return False  # 接続拒否
        
        # データベースからユーザー情報を取得
        from uuid import UUID
        try:
            # JWTトークンから取得したuser_idは実際にはUser.auth_id
            user_uuid = UUID(user_id)
            user = await User.find_by_auth_id(user_uuid)
            
            # auth_idはAuthモデルのID（ObjectIdとして検索）
            from bson import ObjectId
            auth = None
            try:
                auth_object_id = ObjectId(auth_id)
                auth = await Auth.find_one(Auth.id == auth_object_id)
            except Exception as e:
                if os.getenv("DEBUG_SOCKET_AUTH", "false").lower() == "true":
                    print(f"connect debug {sid}: Invalid auth_id format: {e}")
            
            # ObjectId検索で見つからない場合は、user_idで検索
            if not auth:
                try:
                    auth = await Auth.find_one(Auth.user_id == user_uuid)
                except Exception as e:
                    if os.getenv("DEBUG_SOCKET_AUTH", "false").lower() == "true":
                        print(f"connect debug {sid}: Error searching by user_id: {e}")
            
            if not user:
                print(f"connect rejected {sid}: User not found (user_id: {user_id})")
                return False  # 接続拒否
            
            if not auth:
                print(f"connect rejected {sid}: Auth not found (auth_id: {auth_id})")
                return False  # 接続拒否
            
            # ユーザーIDと認証IDの整合性をチェック
            if str(auth.user_id) != str(user_uuid):
                print(f"connect rejected {sid}: User-Auth ID mismatch")
                return False  # 接続拒否
            
            if not auth.is_active:
                print(f"connect rejected {sid}: User account is inactive")
                return False  # 接続拒否
        
        except Exception as e:
            print(f"connect rejected {sid}: Database error - {e}")
            return False  # 接続拒否
        
        # セッション情報を保存
        await sio.save_session(sid, {
            'user_id': str(user.id),
            'auth_id': auth_id,
            'username': auth.username,
            'display_name': user.display_name,
            'email': auth.email,
            'is_verified': auth.is_verified,
            'authenticated': True
        })
        
        # ユーザーをオンライン状態に設定
        user.set_online_status(True)
        await user.save()
        
        print(f"connect accepted {sid}: {auth.username} ({user.display_name})")
        
        # 接続成功をクライアントに通知
        await sio.emit('auth_success', {
            'message': 'Authentication successful',
            'user': user.to_dict_public(),
            'session_id': sid
        }, room=sid)
        
        return True  # 接続許可
        
    except Exception as error:
        print(f"connect rejected {sid}: Authentication error - {error}")
        return False  # 接続拒否

@sio.event
async def disconnect(sid):
    """Socket.IO切断時の処理"""
    try:
        # セッション情報を取得
        session = await sio.get_session(sid)
        if session and session.get('authenticated'):
            user_id = session.get('user_id')
            username = session.get('username')
            
            if user_id:
                # ユーザーをオフライン状態に設定
                from model.user_model import User
                user = await User.get(user_id)
                if user:
                    user.set_online_status(False)
                    await user.save()
            
            print(f"disconnect {sid}: {username}")
        else:
            print(f"disconnect {sid}: unauthenticated session")
            
    except Exception as error:
        print(f"disconnect error {sid}: {error}")

@sio.event
async def message(sid, data):
    """メッセージイベントの処理（認証必須）"""
    try:
        # セッション情報を確認
        session = await sio.get_session(sid)
        if not session or not session.get('authenticated'):
            await sio.emit("error", BaseResponse(
                success=False, 
                error="Authentication required"
            ).model_dump(), room=sid)
            return
        
        # データの検証
        Item(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        await sio.emit("system", BaseResponse(success=False, error=error_payload).model_dump(), room=sid)
        return

    # 認証済みユーザーからのメッセージ
    username = session.get('username', 'Unknown')
    await sio.emit("system", f"Hello from server, {username}!", room=sid)

# Receiver registration moved to import side-effects in receiver module
# Import after sio is defined to avoid circular imports
import receiver.message_receiver  # noqa: E402,F401
import sender.message_sender  # noqa: E402,F401
import receiver.channel_receiver  # noqa: E402,F401

# Setup API router registration
from api.setup_api import router as setup_router
app_fastapi.include_router(setup_router, prefix="/setup", tags=["setup"])

# Auth API router registration
from internal_auth.auth_api import router as auth_router
app_fastapi.include_router(auth_router, prefix="/auth", tags=["auth"])

if __name__ == "__main__":
    uvicorn.run("app:app_socketio", host="0.0.0.0", port=8000, reload=True)