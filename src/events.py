from pyee.asyncio import AsyncIOEventEmitter

# Shared event emitter instance used across the app to avoid circular imports
ee = AsyncIOEventEmitter()
