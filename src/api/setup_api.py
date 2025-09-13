from fastapi import APIRouter, HTTPException, Request
from schema.setup_schema import (
    BaseResponse, DataSchema, StepResponse,
    CreateSuperAdminRequest, ServerInfoRequest, ServerSettingsRequest
)
from utils.setup_helpers import create_super_admin, set_server_info, set_server_settings
from model.server_model import Server
from model.setup_model import SetupProgress

router = APIRouter()

# ルート定義
@router.get("/", response_model=BaseResponse)
async def get_server_info():
    """サーバー情報を取得"""
    try:
        server = await Server.find_active_server()
        if not server:
            return BaseResponse(
                success=True, 
                data={"message": "No server configured yet", "server": None}
            )
        
        return BaseResponse(success=True, data=server.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail={"success": False, "error": str(e)})

@router.get("/progress", response_model=BaseResponse)
async def get_setup_progress():
    """セットアップの進捗状況を取得"""
    try:
        progress = await SetupProgress.get_or_create_setup_progress()
        return BaseResponse(success=True, data=progress.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail={"success": False, "error": str(e)})

@router.post("/reset", response_model=BaseResponse)
async def reset_setup():
    """セットアップをリセットする"""
    try:
        progress = await SetupProgress.reset_setup_progress()
        return BaseResponse(
            success=True, 
            data={
                "message": "Setup progress has been reset",
                "setup_progress": progress.to_dict()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"success": False, "error": str(e)})

@router.get("/{step}", response_model=StepResponse)
async def get_setup_step(step: str):
    """セットアップステップ情報を取得"""
    if step == "1":
        return StepResponse(
            success=True,
            step=1,
            step_description="Create super admin",
            data_schema={
                "username": DataSchema(
                    type="string",
                    required=True,
                    description="Administrator username"
                ),
                "password": DataSchema(
                    type="string",
                    required=True,
                    description="Primary admin password (minimum 8 characters)"
                ),
                "password2": DataSchema(
                    type="string",
                    required=True,
                    description="Secondary admin password for enhanced security"
                ),
                "email": DataSchema(
                    type="string",
                    required=True,
                    description="Administrator email address"
                )
            }
        )
    elif step == "2":
        return StepResponse(
            success=True,
            step=2,
            step_description="Set server info",
            data_schema={
                "name": DataSchema(type="string", required=True),
                "description": DataSchema(type="string", required=True),
                "logo": DataSchema(type="string", required=True),
                "language": DataSchema(type="string", required=True),
                "max_members": DataSchema(type="number", required=True),
                "categories": DataSchema(
                    type="array",
                    required=True,
                    description="Array of category names"
                )
            }
        )
    elif step == "3":
        return StepResponse(
            success=True,
            step=3,
            step_description="Set server settings",
            data_schema={
                "settings": DataSchema(
                    type="object",
                    required=True,
                    description="Server settings object with is_private and max_members"
                )
            }
        )
    else:
        raise HTTPException(status_code=400, detail={"success": False, "error": "Invalid step"})

@router.post("/{step}", response_model=BaseResponse)
async def execute_setup_step(step: str, request: Request):
    """セットアップステップを実行"""
    body = await request.json()
    
    if step == "1":
        if not all(key in body for key in ["username", "password", "password2", "email"]):
            raise HTTPException(
                status_code=400, 
                detail={"success": False, "error": "Username, password, password2, and email are required"}
            )
        return await create_super_admin(body["username"], body["password"], body["password2"], body["email"])
    
    elif step == "2":
        if not all(key in body for key in ["name", "description"]):
            raise HTTPException(
                status_code=400, 
                detail={"success": False, "error": "Name and description are required"}
            )
        return await set_server_info(body)
    
    elif step == "3":
        if "settings" not in body or not isinstance(body["settings"], dict):
            raise HTTPException(
                status_code=400, 
                detail={"success": False, "error": "Settings object is required"}
            )
        if "is_private" not in body["settings"] or "max_members" not in body["settings"]:
            raise HTTPException(
                status_code=400, 
                detail={"success": False, "error": "is_private and max_members are required in settings"}
            )
        return await set_server_settings(body["settings"])
    
    else:
        raise HTTPException(status_code=400, detail={"success": False, "error": "Invalid step"})
