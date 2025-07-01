import json

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
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
        memberships = await Membership.filter_by(db=self.db, group_uuid=self.group_uuid)
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
        await self.redis.eval(
            lua_script,
            2,
            self.group_location_key,
            self.group_member_key,
            user_uuid,
            json.dumps(location_data.serializable_dict()),
            str(location_data.timestamp),
            str(settings.GROUP_LOCATION_TTL),
        )

    async def get_group_locations(self) -> list[dict]:
        locations = await self.redis.hgetall(self.group_location_key)
        return [
            {"user_uuid": user_uuid, **json.loads(val)}
            for user_uuid, val in locations.items()
        ]
