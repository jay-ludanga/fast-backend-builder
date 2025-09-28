import json
from typing import Set, Optional

import json
from typing import Set, Optional

import redis.asyncio as redis

from fast_backend_builder.utils.error_logging import log_message


class RedisClient:
    _instance: Optional["RedisClient"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
        return cls._instance

    def __init__(self, host="localhost", port=6379, password=None, db=0, pool_size=10, debug=True):
        if not hasattr(self, "initialized"):  # Prevent re-init on singleton
            if not debug:
                redis_url = f"redis://:{password}@{host}:{port}/{db}"
            else:
                redis_url = f"redis://{host}:{port}/{db}"

            self.client = redis.from_url(
                redis_url,
                decode_responses=True,
                max_connections=pool_size,
            )
            self.initialized = True
            log_message("Connected to Redis (async)")

    # --------------------
    # Basic key operations
    # --------------------
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        return await self.client.set(key, value, ex=ex)

    async def setex(self, key: str, ttl: int, value: str):
        return await self.client.setex(key, ttl, value)

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def delete(self, key: str):
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.client.exists(key))

    async def set_expire(self, key: str, seconds: int):
        return await self.client.expire(key, seconds)

    # --------------------
    # Set operations
    # --------------------
    async def sadd(self, key: str, *values: str):
        return await self.client.sadd(key, *values)

    async def srem(self, key: str, *values: str):
        return await self.client.srem(key, *values)

    async def smembers(self, key: str) -> Set[str]:
        return await self.client.smembers(key)

    async def sismember(self, key: str, value: str) -> bool:
        return await self.client.sismember(key, value)

    # --------------------
    # List operations
    # --------------------
    async def rpush(self, key: str, *values: str):
        return await self.client.rpush(key, *values)

    async def lrange(self, key: str, start=0, end=-1):
        return await self.client.lrange(key, start, end)

    # --------------------
    # Scan utilities
    # --------------------
    async def scan(self, match=None, count=100):
        cursor = b"0"
        keys = []
        while cursor:
            cursor, found_keys = await self.client.scan(cursor=cursor, match=match, count=count)
            keys.extend(found_keys)
        return keys

    async def scan_with_query(self, key_pattern: str, query: str, count=100):
        cursor = b"0"
        matching_data = []
        while cursor:
            cursor, found_keys = await self.client.scan(cursor=cursor, match=key_pattern, count=count)
            for key in found_keys:
                value = await self.get(key)
                if value:
                    try:
                        data = json.loads(value)
                        if query in json.dumps(data):
                            matching_data.append(data)
                    except json.JSONDecodeError:
                        continue
        return matching_data

    # --------------------
    # Pub/Sub
    # --------------------
    async def publish(self, channel: str, message: str):
        return await self.client.publish(channel, message)

    async def subscribe(self, channel: str):
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def listen_to_channel(self, pubsub, on_message):
        async for message in pubsub.listen():
            if message and message["type"] == "message":
                on_message(message)

    # --------------------
    # Connection management
    # --------------------
    async def close(self):
        await self.client.close()
        log_message("Redis connection closed")
