from pydantic import BaseModel


class WebSocketRequest(BaseModel):
    action: str
    data: dict | None = None
