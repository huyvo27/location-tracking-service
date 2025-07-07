import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from redis.asyncio import ConnectionError as RedisConnectionError

from app.core.logger import logger
from app.dependencies.db import get_db, get_redis
from app.dependencies.group import ensure_user_is_member_of_group
from app.schemas.websocket import WebSocketRequest
from app.websocket.handlers.group import handle_websocket_message
from app.websocket.helpers.auth import get_token_data_ws
from app.websocket.manager import connection_manager

router = APIRouter()


@router.websocket("/{group_uuid}/ws")
async def group_ws(websocket: WebSocket, group_uuid: str):
    token_data = await get_token_data_ws(websocket=websocket)
    group_cache_service = await ensure_user_is_member_of_group(
        group_uuid=group_uuid,
        token_data=token_data,
        redis=await get_redis(group_uuid),
        db=await anext(get_db()),
    )

    await connection_manager.connect(group_uuid, websocket)

    listener_task = asyncio.create_task(
        group_cache_service.location_listener(websocket=websocket)
    )

    try:
        await websocket.send_json(
            {
                "action": "group_locations",
                "data": await group_cache_service.get_group_locations(),
            }
        )

        while True:
            data = await websocket.receive_json()
            try:
                message = WebSocketRequest(**data)
                await handle_websocket_message(
                    websocket=websocket,
                    user_uuid=token_data.sub,
                    group_cache_service=group_cache_service,
                    message=message,
                )
            except (ValueError, ValidationError):
                await websocket.send_json({"error": "Invalid message format"})

    except WebSocketDisconnect:
        pass
    except (RedisConnectionError, TimeoutError) as e:
        await websocket.send_json(
            {"error": "Redis server is temporarily unavailable. Please try again."}
        )
    except Exception as e:
        logger.exception(f"Unhandled error in group_ws WebSocket: {str(e)}")
        await websocket.send_json({"error": "Internal server error"})
    finally:
        listener_task.cancel()
        connection_manager.disconnect(group_uuid, websocket)
