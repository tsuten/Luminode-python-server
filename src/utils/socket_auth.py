from typing import Optional, Dict, Any
from sockets import sio

async def get_authenticated_user(sid: str) -> Optional[Dict[str, Any]]:
    """
    Socket.IOセッションから認証済みユーザー情報を取得する
    
    Args:
        sid: Socket.IO セッションID
    
    Returns:
        認証済みユーザー情報（認証されていない場合はNone）
    """
    try:
        session = await sio.get_session(sid)
        if session and session.get('authenticated'):
            return session
        return None
    except Exception:
        return None

async def require_authentication(sid: str) -> Optional[Dict[str, Any]]:
    """
    認証が必要なSocket.IOイベント用のデコレータヘルパー
    
    Args:
        sid: Socket.IO セッションID
    
    Returns:
        認証済みユーザー情報（認証されていない場合はエラーを送信してNoneを返す）
    """
    session = await get_authenticated_user(sid)
    if not session:
        from schema.setup_schema import BaseResponse
        await sio.emit("error", BaseResponse(
            success=False,
            error="Authentication required"
        ).model_dump(), room=sid)
        return None
    return session

def socket_auth_required(func):
    """
    Socket.IOイベントハンドラー用の認証デコレータ
    
    使用例:
    @sio.event
    @socket_auth_required
    async def my_event(sid, data, session=None):
        # sessionには認証済みユーザー情報が入る
        username = session['username']
        ...
    """
    async def wrapper(sid, *args, **kwargs):
        session = await require_authentication(sid)
        if session is None:
            return  # 認証エラーはrequire_authentication内で送信済み
        
        # セッション情報を引数に追加
        kwargs['session'] = session
        return await func(sid, *args, **kwargs)
    
    return wrapper
