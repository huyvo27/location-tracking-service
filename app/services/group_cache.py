import json

from fastapi import WebSocket
from redis.asyncio import ConnectionError as RedisConnectionError
from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.group import Group
from app.models.membership import Membership
from app.schemas.group import GroupUpdateLocationRequest


class GroupCacheService:
    def __init__(self, redis: Redis, db: AsyncSession, group_uuid: str):
        self.redis = redis
        self.db = db
        self.group_uuid = group_uuid

    @property
    def group_member_key(self) -> str:
        return f"member:{self.group_uuid}"

    @property
    def group_location_key(self) -> str:
        return f"location:{self.group_uuid}"

    @property
    def group_location_channel(self) -> str:
        return f"group:{self.group_uuid}:location"

    async def add_member(self, user_uuid: str) -> None:
        lua_script = """
        local key = KEYS[1]
        local member = ARGV[1]
        local ttl = tonumber(ARGV[2])

        redis.call("SADD", key, member)
        redis.call("EXPIRE", key, ttl)
        return 1
        """
        await self.redis.eval(
            lua_script,
            1,
            self.group_member_key,
            user_uuid,
            str(settings.GROUP_LOCATION_TTL),
        )

    async def sync_group(self) -> None:
        group = await Group.find_by(db=self.db, uuid=self.group_uuid)
        memberships = await Membership.filter_by(db=self.db, group_id=group.id)
        members = [m.user_uuid for m in memberships]
        if not members:
            return

        lua_script = """
        local key = KEYS[1]
        local ttl = tonumber(ARGV[1])
        for i = 2, #ARGV do
            redis.call("SADD", key, ARGV[i])
        end
        redis.call("EXPIRE", key, ttl)
        return 1
        """
        args = [str(settings.GROUP_LOCATION_TTL)] + [str(m) for m in set(members)]

        await self.redis.eval(
            lua_script,
            1,
            self.group_member_key,
            *args,
        )

    async def is_member(self, user_uuid: str) -> bool:
        return await self.redis.sismember(self.group_member_key, user_uuid)

    async def is_exists(self) -> bool:
        return await self.redis.exists(self.group_member_key) == 1

    async def remove_member(self, user_uuid: str) -> bool:
        removed = await self.redis.srem(self.group_member_key, user_uuid)
        await self.redis.hdel(self.group_location_key, user_uuid)
        return removed == 1

    async def remove_group(self):
        await self.redis.delete(self.group_member_key)
        await self.redis.delete(self.group_location_key)

    async def update_location(
        self, user_uuid: str, location_data: GroupUpdateLocationRequest
    ):
        lua_script = """
                local location_key = KEYS[1]
                local member_key = KEYS[2]
                local field = ARGV[1]
                local payload = ARGV[2]
                local new_ts = tonumber(ARGV[3])
                local ttl = tonumber(ARGV[4])

                local current = redis.call("HGET", location_key, field)
                if current then
                    local current_data = cjson.decode(current)
                    local current_ts = tonumber(current_data["timestamp"])
                    if current_ts and current_ts >= new_ts then
                        return 0  -- Do not update
                    end
                end

                redis.call("HSET", location_key, field, payload)
                redis.call("EXPIRE", location_key, ttl)
                redis.call("EXPIRE", member_key, ttl)
                return 1
            """
        payload = {"user_uuid": user_uuid, **location_data.serializable_dict()}
        await self.redis.eval(
            lua_script,
            2,
            self.group_location_key,
            self.group_member_key,
            user_uuid,
            json.dumps(payload),
            str(location_data.timestamp),
            str(settings.GROUP_LOCATION_TTL),
        )

    async def update_location_and_publish(
        self, user_uuid: str, location_data: GroupUpdateLocationRequest
    ):
        lua_script = """
            local location_key = KEYS[1]
            local member_key = KEYS[2]
            local channel = KEYS[3]

            local field = ARGV[1]
            local payload = ARGV[2]
            local new_ts = tonumber(ARGV[3])
            local ttl = tonumber(ARGV[4])

            local current = redis.call("HGET", location_key, field)
            if current then
                local current_data = cjson.decode(current)
                local current_ts = tonumber(current_data["timestamp"])
                if current_ts and current_ts >= new_ts then
                    return 0  -- Skip update
                end
            end

            redis.call("HSET", location_key, field, payload)
            redis.call("EXPIRE", location_key, ttl)
            redis.call("EXPIRE", member_key, ttl)
            redis.call("PUBLISH", channel, payload)
            return 1
        """
        payload = {"user_uuid": user_uuid, **location_data.serializable_dict()}

        res = await self.redis.eval(
            lua_script,
            3,
            self.group_location_key,
            self.group_member_key,
            self.group_location_channel,
            user_uuid,
            json.dumps(payload),
            str(location_data.timestamp),
            str(settings.GROUP_LOCATION_TTL),
        )

    async def get_group_locations(self) -> list[dict]:
        locations = await self.redis.hgetall(self.group_location_key)
        return [json.loads(val) for val in locations.values()]

    async def location_listener(self, websocket: WebSocket):
        pubsub: PubSub = self.redis.pubsub()
        await pubsub.subscribe(self.group_location_channel)
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=0.5
                )
                if message and message["type"] == "message":
                    location_data = json.loads(message["data"])
                    # if user_uuid == location_data["user_uuid"]: continue
                    await websocket.send_json(
                        {"action": "group_locations", "data": [location_data]}
                    )
        except Exception as e:
            raise e
        finally:
            await pubsub.unsubscribe(self.group_location_channel)
            await pubsub.close()
