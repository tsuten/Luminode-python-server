import socketio

# Shared Socket.IO server instance used across the app to avoid circular imports
sio = socketio.AsyncServer(async_mode='asgi')
