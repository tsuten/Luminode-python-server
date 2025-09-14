from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import Any, Optional
from uuid import UUID, uuid4
from .auth_model import Auth
from .jwt_service import JWTService
from model.user_model import User
from utils.get_settings import get_is_public
class BaseResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: Any | None = None

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=100)

class LoginRequest(BaseModel):
    username: str  # ユーザー名またはメールアドレス
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class VerifyEmailRequest(BaseModel):
    token: str

router = APIRouter()

# 認証ヘルパー関数
async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """現在のユーザーを取得する（認証が必要なエンドポイント用）"""
    if not authorization:
        return None
    
    try:
        # "Bearer "を除去
        token = authorization.replace("Bearer ", "")
        user_id = JWTService.get_user_id_from_token(token)
        if not user_id:
            return None
        
        # ユーザー情報を取得
        user = await User.find_by_auth_id(user_id)
        auth = await Auth.find_by_user_id(user_id)
        
        if user and auth:
            return {
                "user": user,
                "auth": auth
            }
    except Exception:
        pass
    
    return None

# ルート定義
@router.post("/register", response_model=BaseResponse)
async def register(request: RegisterRequest):
    """ユーザー登録"""

    if not get_is_public():
        return BaseResponse(
            success=False,
            error="Registration is not allowed"
        )

    try:
        # 既存ユーザーをチェック
        existing_auth_username = await Auth.find_by_username(request.username)
        if existing_auth_username:
            return BaseResponse(
                success=False,
                error="Username already exists"
            )
        
        existing_auth_email = await Auth.find_by_email(request.email)
        if existing_auth_email:
            return BaseResponse(
                success=False,
                error="Email already exists"
            )
        
        # ユーザーを作成
        user_id = uuid4()
        user = User(
            auth_id=user_id,
            display_name=request.display_name,
            email=request.email
        )
        await user.insert()
        
        # 認証データを作成
        auth = await Auth.create_auth(
            user_id=user_id,
            username=request.username,
            email=request.email,
            password=request.password
        )
        
        return BaseResponse(
            success=True,
            data={
                "message": "User registered successfully",
                "user": user.to_dict_public(),
                "auth": auth.to_dict(),
                "verification_token": auth.verification_token
            }
        )
    except Exception as error:
        print(f"Error registering user: {error}")
        return BaseResponse(
            success=False,
            error=str(error)
        )

@router.post("/login", response_model=BaseResponse)
async def login(request: LoginRequest):
    """ユーザーログイン"""
    try:
        # 認証を実行
        auth = await Auth.authenticate(request.username, request.password)
        if not auth:
            return BaseResponse(
                success=False,
                error="Invalid username or password"
            )
        
        # ユーザー情報を取得
        user = await User.find_by_auth_id(auth.user_id)
        if not user:
            return BaseResponse(
                success=False,
                error="User data not found"
            )
        
        # JWTトークンを生成
        token_data = JWTService.create_token_pair(
            user_id=auth.user_id,
            auth_id=str(auth.id),
            additional_data={
                "username": auth.username,
                "email": auth.email,
                "is_verified": auth.is_verified
            }
        )
        
        return BaseResponse(
            success=True,
            data={
                "message": "Login successful",
                "tokens": token_data,
                "user": user.to_dict(),
                "auth": auth.to_dict()
            }
        )
    except Exception as error:
        print(f"Error during login: {error}")
        return BaseResponse(
            success=False,
            error=str(error)
        )

@router.post("/refresh", response_model=BaseResponse)
async def refresh_token(request: RefreshTokenRequest):
    """トークンリフレッシュ"""
    try:
        # リフレッシュトークンを検証して新しいトークンを生成
        new_tokens = JWTService.refresh_access_token(request.refresh_token)
        if not new_tokens:
            return BaseResponse(
                success=False,
                error="Invalid or expired refresh token"
            )
        
        return BaseResponse(
            success=True,
            data={
                "message": "Token refreshed successfully",
                "tokens": new_tokens
            }
        )
    except Exception as error:
        print(f"Error refreshing token: {error}")
        return BaseResponse(
            success=False,
            error=str(error)
        )

@router.post("/verify-email", response_model=BaseResponse)
async def verify_email(request: VerifyEmailRequest):
    """メール認証"""
    try:
        # 認証トークンでユーザーを検索
        auth = await Auth.find_one(Auth.verification_token == request.token)
        if not auth:
            return BaseResponse(
                success=False,
                error="Invalid verification token"
            )
        
        # メール認証を実行
        if auth.verify_email(request.token):
            await auth.save()
            return BaseResponse(
                success=True,
                data={
                    "message": "Email verified successfully",
                    "user_id": str(auth.user_id)
                }
            )
        else:
            return BaseResponse(
                success=False,
                error="Email verification failed"
            )
    except Exception as error:
        print(f"Error verifying email: {error}")
        return BaseResponse(
            success=False,
            error=str(error)
        )

@router.get("/profile", response_model=BaseResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """ユーザープロフィール取得（認証が必要）"""
    if not current_user:
        raise HTTPException(status_code=401, detail={"success": False, "error": "Authentication required"})
    
    try:
        return BaseResponse(
            success=True,
            data={
                "user": current_user["user"].to_dict(),
                "auth": current_user["auth"].to_dict()
            }
        )
    except Exception as error:
        print(f"Error getting profile: {error}")
        return BaseResponse(
            success=False,
            error=str(error)
        )

@router.post("/logout", response_model=BaseResponse)
async def logout():
    """ユーザーログアウト"""
    # JWTはステートレスなので、クライアント側でトークンを削除
    # 必要に応じてトークンブラックリスト機能を実装
    return BaseResponse(
        success=True,
        data={"message": "Logout successful"}
    )