from typing import Dict, Any
from schema.setup_schema import BaseResponse
from model.admin_model import Admin, AdminRole
from model.server_model import Server, ServerSettings
from model.setup_model import SetupProgress, SetupStep

async def create_super_admin(username: str, password: str, password2: str, email: str) -> BaseResponse:
    """スーパー管理者を作成"""
    try:
        # 既存の管理者をチェック
        existing_admin = await Admin.find_by_username(username)
        if existing_admin:
            return BaseResponse(
                success=False,
                error="Admin with this username already exists"
            )
        
        existing_email = await Admin.find_by_email(email)
        if existing_email:
            return BaseResponse(
                success=False,
                error="Admin with this email already exists"
            )

        # スーパー管理者を作成
        admin = await Admin.create_admin(
            username=username,
            email=email,
            password=password,
            password2=password2,
            role=AdminRole.SUPER_ADMIN
        )

        # セットアップ進捗を更新
        progress = await SetupProgress.get_or_create_setup_progress()
        progress.start_setup()
        progress.complete_step(SetupStep.CREATE_SUPER_ADMIN, {
            "admin_id": str(admin.id),
            "username": admin.username,
            "email": admin.email
        })
        await progress.save()

        return BaseResponse(
            success=True,
            data={
                "message": "Super admin created successfully",
                "admin": admin.to_dict_without_sensitive(),
                "setup_progress": progress.to_dict()
            }
        )
    except Exception as error:
        print(f"Error creating super admin: {error}")
        return BaseResponse(
            success=False,
            error=str(error) if isinstance(error, Exception) else "Unknown error occurred"
        )

async def set_server_info(data: Dict[str, Any]) -> BaseResponse:
    """サーバー情報を設定"""
    try:
        # 既存のサーバーをチェック
        existing_server = await Server.find_active_server()
        if existing_server:
            return BaseResponse(
                success=False,
                error="Server already exists. Only one server instance is allowed."
            )

        # サーバーを作成
        server = await Server.create_server(
            name=data["name"],
            description=data["description"],
            logo_url=data.get("logo"),
            language=data.get("language", "ja"),
            categories=data.get("categories", [])
        )

        # セットアップ進捗を更新
        progress = await SetupProgress.get_or_create_setup_progress()
        progress.complete_step(SetupStep.SET_SERVER_INFO, {
            "server_id": str(server.id),
            "name": server.name,
            "description": server.description
        })
        await progress.save()

        return BaseResponse(
            success=True,
            data={
                "message": "Server information set successfully",
                "server": server.to_dict(),
                "setup_progress": progress.to_dict()
            }
        )
    except Exception as error:
        print(f"Error setting server info: {error}")
        return BaseResponse(
            success=False,
            error=str(error) if isinstance(error, Exception) else "Unknown error occurred"
        )

async def set_server_settings(settings: Dict[str, Any]) -> BaseResponse:
    """サーバー設定を設定"""
    try:
        # 既存のサーバーを取得
        server = await Server.find_active_server()
        if not server:
            return BaseResponse(
                success=False,
                error="No active server found. Please set server info first."
            )

        # 設定データの準備
        settings_data = {
            "is_private": settings.get("is_private", False),
            "max_members": settings.get("max_members", 1000)
        }

        # サーバー設定を更新
        updated_server = await Server.update_settings(settings_data)
        if not updated_server:
            return BaseResponse(
                success=False,
                error="Failed to update server settings"
            )

        # リソース計算
        max_members = settings_data["max_members"]
        expected_resource = calculate_resource_cost_for_each_connection(max_members)

        # セットアップ進捗を更新
        progress = await SetupProgress.get_or_create_setup_progress()
        progress.complete_step(SetupStep.SET_SERVER_SETTINGS, {
            "settings": settings_data,
            "expected_resource": expected_resource
        })
        await progress.save()

        return BaseResponse(
            success=True,
            data={
                "message": "Server settings configured successfully",
                "server": updated_server.to_dict(),
                "expected_resource": expected_resource,
                "setup_progress": progress.to_dict()
            }
        )
    except Exception as error:
        print(f"Error setting server settings: {error}")
        return BaseResponse(
            success=False,
            error=str(error) if isinstance(error, Exception) else "Unknown error occurred"
        )

def calculate_resource_cost_for_each_connection(max_members: int) -> Dict[str, Any]:
    """
    接続数に基づくリソースコストを計算する
    
    最大メンバー数から実際のリソース使用量を推定し、サーバー運用に必要な
    リソースを計算します。オンラインユーザーは25%、アクティブ接続は10%と仮定し、
    接続あたり2MBのメモリと1KB/sのネットワーク使用量を想定しています。
    
    Args:
        max_members: サーバーの最大メンバー数（1-100,000）
    
    Returns:
        リソース使用量とサーバー推奨設定を含む辞書
    """
    # オンラインユーザーとアクティブ接続の推定
    estimated_online_users = max_members // 4  # 25%がオンラインと仮定
    active_connections = max_members // 10     # 10%がアクティブと仮定
    
    # メモリ使用量の計算（接続あたり2MB）
    memory_per_connection = 2  # MB
    total_memory = active_connections * memory_per_connection
    
    # ネットワーク使用量の計算（接続あたり1KB/s）
    network_per_connection = 1  # KB/s
    total_network = active_connections * network_per_connection
    
    # サーバー推奨設定
    if max_members < 1000:
        server_type = "small"
        min_ram = "512MB"
        min_bandwidth = "10Mbps"
    elif max_members < 5000:
        server_type = "medium"
        min_ram = "1GB"
        min_bandwidth = "100Mbps"
    else:
        server_type = "large"
        min_ram = "2GB"
        min_bandwidth = "1Gbps"
    
    return {
        "totalMembers": max_members,
        "estimatedOnlineUsers": estimated_online_users,
        "activeConnections": active_connections,
        "memory": {
            "perConnection": f"{memory_per_connection}MB",
            "total": f"{total_memory}MB",
            "formatted": f"{total_memory}MB"
        },
        "network": {
            "perConnection": f"{network_per_connection}KB/s",
            "total": f"{total_network}KB/s",
            "formatted": f"{total_network}KB/s"
        },
        "recommendation": {
            "serverType": server_type,
            "minRam": min_ram,
            "minBandwidth": min_bandwidth
        }
    }
