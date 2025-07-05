from fastapi import WebSocket
from pydantic import ValidationError

from app.schemas.group import GroupUpdateLocationRequest
from app.schemas.websocket import WebSocketRequest
from app.services.group_cache import GroupCacheService


async def handle_websocket_message(
    websocket: WebSocket,
    user_uuid: str,
    group_cache_service: GroupCacheService,
    message: WebSocketRequest,
):
    if (
        not await group_cache_service.is_exists()
        or not await group_cache_service.is_member(user_uuid=user_uuid)
    ):
        await websocket.send_json({"error": "You are no longer a member of this group"})
        await websocket.close()
        return

    if message.action == "get_locations":
        locations = await group_cache_service.get_group_locations()
        await websocket.send_json(
            {
                "action": "group_locations",
                "data": locations,
            }
        )
    elif message.action == "ping":
        await websocket.send_json({"action": "pong", "data": "ok"})
    elif message.action == "update_location":
        if not message.data:
            await websocket.send_json({"error": "Missing data"})
            return

        try:
            location = GroupUpdateLocationRequest(**message.data)
            await group_cache_service.update_location_and_publish(
                user_uuid=user_uuid, location_data=location
            )
        except ValidationError:
            await websocket.send_json({"error": "Invalid data format"})
            return
