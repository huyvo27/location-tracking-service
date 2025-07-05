from fastapi import WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.schemas.token import TokenData


async def get_token_data_ws(websocket: WebSocket) -> TokenData:
    auth_header = websocket.headers.get("authorization")
    if not auth_header:
        await websocket.close(code=1008)
        raise WebSocketDisconnect(code=1008, reason="Invalid Token")

    try:
        return decode_access_token(auth_header)
    except Exception:
        await websocket.close(code=1008)
        raise WebSocketDisconnect(code=1008, reason="Invalid Token")
