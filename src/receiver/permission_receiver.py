from typing import Any, Optional, List
from pydantic import BaseModel
from sockets import sio
from datetime import datetime

from model.permission_model import Role, Permission, PermissionType
from utils.error_formatter import format_exception_for_response
from utils.nest_pydantic_errors import nest_pydantic_errors
from utils.extract_elements_from_id import extract_elements_from_id_safe


class BaseResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: Any | None = None


class CreateRoleSchema(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[List[Permission]] = None


@sio.event
async def create_role(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        return BaseResponse(success=False, error="Authentication required").model_dump()
    user_id = session.get('user_id')
    if not user_id:
        return BaseResponse(success=False, error="User ID not found").model_dump()
    # boilerplate ends

    try:
        payload = CreateRoleSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    role = Role(
        name=payload.name,
        description=payload.description or "",
        permissions=payload.permissions,
    )
    await role.insert()
    return BaseResponse(success=True, data=role.to_dict()).model_dump()


class UpdateRoleSchema(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[Permission]] = None


@sio.event
async def update_role(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        return BaseResponse(success=False, error="Authentication required").model_dump()
    user_id = session.get('user_id')
    if not user_id:
        return BaseResponse(success=False, error="User ID not found").model_dump()
    # boilerplate ends

    try:
        payload = UpdateRoleSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    # id は "role:{id}" を想定
    type_part, value_part = extract_elements_from_id_safe(payload.id)
    if type_part != "role" or not value_part:
        return BaseResponse(success=False, error="Invalid role id").model_dump()
    
    role = await Role.get(value_part)
    if not role or role.is_deleted:
        return BaseResponse(success=False, error="Role not found").model_dump()

    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description
    if payload.permissions is not None:
        role.permissions = payload.permissions

    role.updated_at = datetime.now()
    await role.save()
    return BaseResponse(success=True, data=role.to_dict()).model_dump()


class DeleteRoleSchema(BaseModel):
    id: str


@sio.event
async def delete_role(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        return BaseResponse(success=False, error="Authentication required").model_dump()
    user_id = session.get('user_id')
    if not user_id:
        return BaseResponse(success=False, error="User ID not found").model_dump()
    # boilerplate ends

    try:
        payload = DeleteRoleSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    # id は "role:{id}" を想定
    type_part, value_part = extract_elements_from_id_safe(payload.id)
    if type_part != "role" or not value_part:
        return BaseResponse(success=False, error="Invalid role id").model_dump()

    role = await Role.get(value_part)
    if not role or role.is_deleted:
        return BaseResponse(success=False, error="Role not found").model_dump()

    role.is_deleted = True
    role.deleted_at = datetime.now()
    await role.save()

    return BaseResponse(success=True, data=role.to_dict()).model_dump()


class GetRolesSchema(BaseModel):
    include_deleted: Optional[bool] = False


@sio.event
async def get_roles(sid, data=None):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        return BaseResponse(success=False, error="Authentication required").model_dump()
    user_id = session.get('user_id')
    if not user_id:
        return BaseResponse(success=False, error="User ID not found").model_dump()
    # boilerplate ends

    try:
        payload = GetRolesSchema(**(data or {}))
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    if payload.include_deleted:
        roles = await Role.find().to_list()
    else:
        roles = await Role.find(Role.is_deleted == False).to_list()

    return BaseResponse(success=True, data={
        "roles": [role.to_dict() for role in roles],
        "roles_count": len(roles)
    }).model_dump()


class GetRoleSchema(BaseModel):
    id: str


@sio.event
async def get_role(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        return BaseResponse(success=False, error="Authentication required").model_dump()
    user_id = session.get('user_id')
    if not user_id:
        return BaseResponse(success=False, error="User ID not found").model_dump()
    # boilerplate ends

    try:
        payload = GetRoleSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    # id は "role:{id}" を想定
    type_part, value_part = extract_elements_from_id_safe(payload.id)
    if type_part != "role" or not value_part:
        return BaseResponse(success=False, error="Invalid role id").model_dump()

    role = await Role.get(value_part)
    if not role:
        return BaseResponse(success=False, error="Role not found").model_dump()

    return BaseResponse(success=True, data=role.to_dict()).model_dump()


class RestoreRoleSchema(BaseModel):
    id: str


@sio.event
async def restore_role(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        return BaseResponse(success=False, error="Authentication required").model_dump()
    user_id = session.get('user_id')
    if not user_id:
        return BaseResponse(success=False, error="User ID not found").model_dump()
    # boilerplate ends

    try:
        payload = RestoreRoleSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    # id は "role:{id}" を想定
    type_part, value_part = extract_elements_from_id_safe(payload.id)
    if type_part != "role" or not value_part:
        return BaseResponse(success=False, error="Invalid role id").model_dump()

    role = await Role.get(value_part)
    if not role:
        return BaseResponse(success=False, error="Role not found").model_dump()
    
    if not role.is_deleted:
        return BaseResponse(success=False, error="Role is not deleted").model_dump()

    role.is_deleted = False
    role.deleted_at = None
    role.updated_at = datetime.now()
    await role.save()

    return BaseResponse(success=True, data=role.to_dict()).model_dump()

class AddPermissionToRoleSchema(BaseModel):
    role_id: str
    permission: Permission

@sio.event
async def add_permission_to_role(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        return BaseResponse(success=False, error="Authentication required").model_dump()
    user_id = session.get('user_id')
    if not user_id:
        return BaseResponse(success=False, error="User ID not found").model_dump()
    # boilerplate ends

    try:
        payload = AddPermissionToRoleSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    # role_id は "role:{id}" を想定
    type_part, value_part = extract_elements_from_id_safe(payload.role_id)
    if type_part != "role" or not value_part:
        return BaseResponse(success=False, error="Invalid role id").model_dump()

    role = await Role.get(value_part)
    if not role or role.is_deleted:
        return BaseResponse(success=False, error="Role not found").model_dump()

    # 権限を追加（重複チェック）
    if role.permissions is None:
        role.permissions = []
    
    # 同じタイプの権限が既に存在するかチェック
    for existing_permission in role.permissions:
        if existing_permission.type == payload.permission.type:
            return BaseResponse(success=False, error="Permission already exists for this role").model_dump()
    
    # 権限を追加
    role.permissions.append(payload.permission)
    role.updated_at = datetime.now()
    await role.save()

    return BaseResponse(success=True, data=role.to_dict()).model_dump()

class UpdatePermissionOfRoleSchema(BaseModel):
    id: str
    permissions: Optional[List[Permission]] = None


@sio.event
async def update_permission_of_role(sid, data):
    # get auth info (boilerplate)
    session = await sio.get_session(sid)
    if not session or not session.get('authenticated'):
        return BaseResponse(success=False, error="Authentication required").model_dump()
    user_id = session.get('user_id')
    if not user_id:
        return BaseResponse(success=False, error="User ID not found").model_dump()
    # boilerplate ends

    try:
        payload = UpdatePermissionOfRoleSchema(**data)
    except Exception as e:
        error_payload = format_exception_for_response(e, pydantic_nester=nest_pydantic_errors)
        return BaseResponse(success=False, error=error_payload).model_dump()

    # id は "role:{id}" を想定
    type_part, value_part = extract_elements_from_id_safe(payload.id)
    if type_part != "role" or not value_part:
        return BaseResponse(success=False, error="Invalid role id").model_dump()

    role = await Role.get(value_part)
    if not role or role.is_deleted:
        return BaseResponse(success=False, error="Role not found").model_dump()

    # 権限を更新
    if payload.permissions is not None:
        role.permissions = payload.permissions
        role.updated_at = datetime.now()
        await role.save()

    return BaseResponse(success=True, data=role.to_dict()).model_dump()
