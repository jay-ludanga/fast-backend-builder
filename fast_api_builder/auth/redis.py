import asyncio
import json
import threading
from typing import Set

import redis
from decouple import config

from fast_api_builder.utils.error_logging import log_exception, log_message, log_warning


class RedisClient:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Prevent instantiation if an instance already exists
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
        return cls._instance

    def __init__(self, host='localhost', port=6379, password=None, db=0, pool_size=10, debug=True):
        if not hasattr(self, 'initialized'):  # Avoid re-initializing
            self.host = host
            self.port = port
            self.db = db
            self.password = password
            self.pool_size = pool_size
            self.debug = debug
            self.client = self._connect()
            self.initialized = True  # Mark as initialized

    def _connect(self):
        """
        Create and return a Redis client instance using a URL and a connection pool.

        :return: Redis client instance.
        """
        try:
            if not self.debug:  # config('DEBUG', cast=bool):
                redis_url = f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
            else:
                redis_url = f"redis://{self.host}:{self.port}/{self.db}"

            pool = redis.ConnectionPool.from_url(redis_url, max_connections=self.pool_size, decode_responses=True)
            client = redis.Redis(connection_pool=pool)
            client.ping()  # Test the connection
            log_message(f"Connected to Redis with connection pool")
            return client
        except redis.ConnectionError as e:
            log_exception(f"Failed to connect to Redis: {e}")
            return None

    def set(self, key, value, ex=None):
        """
        Set a value in Redis.

        :param key: The key under which the value is stored.
        :param value: The value to store.
        :param ex: The expiry time in seconds (optional).
        """
        if self.client:
            self.client.set(key, value, ex=ex)

    def setex(self, key: str, ttl: int, value: str):
        return self.client.setex(key, ttl, value)

    def get(self, key):
        """
        Get a value from Redis.

        :param key: The key under which the value is stored.
        :return: The value stored in Redis.
        """
        if self.client:
            return self.client.get(key)
        return None

    def delete(self, key):
        """
        Delete a key from Redis.

        :param key: The key to delete.
        """
        if self.client:
            self.client.delete(key)

    def exists(self, key):
        """
        Check if a key exists in Redis.

        :param key: The key to check.
        :return: True if the key exists, False otherwise.
        """
        if self.client:
            return self.client.exists(key)
        return False

    def sadd(self, key, *values):
        """
        Add one or more members to a set in Redis.

        :param key: The key of the set.
        :param values: Values to add to the set.
        """
        if self.client:
            self.client.sadd(key, *values)

    def srem(self, key, *values):
        """
        Remove one or more members from a set in Redis.

        :param key: The key of the set.
        :param values: Values to remove from the set.
        """
        if self.client:
            self.client.srem(key, *values)

    def scan(self, match=None, count=100):
        """
        Scan the Redis database for keys matching a pattern.

        :param match: The pattern to match keys against.
        :param count: The number of keys to return per scan.
        :return: A list of matching keys.
        """
        if self.client:
            cursor = 0
            keys = []
            while True:
                cursor, found_keys = self.client.scan(cursor, match=match, count=count)
                keys.extend(found_keys)
                if cursor == 0:
                    break
            return keys
        return []

    def scan_with_query(self, key_pattern, query, count=100):
        """
        Scan the Redis database for keys matching a pattern and filter by a query string within the data.

        :param key_pattern: The pattern to match keys against.
        :param query: The query string to filter data.
        :param count: The number of keys to return per scan iteration.
        :return: A list of matching dictionaries.
        """
        if self.client:
            cursor = 0
            matching_data = []
            while True:
                cursor, found_keys = self.client.scan(cursor, match=key_pattern, count=count)
                for key in found_keys:
                    value = self.get(key)
                    if value:
                        try:
                            data = json.loads(value)
                            if query in json.dumps(data):
                                matching_data.append(data)
                        except json.JSONDecodeError:
                            continue
                if cursor == 0:
                    break

            return matching_data
        return []

    def smembers(self, key: str) -> Set[str]:
        """
        Retrieve all members of a set from Redis.

        :param key: The key of the set.
        :return: A set of members.
        """
        if self.client:
            return self.client.smembers(key)
        return set()

    def close(self):
        """
        Close the Redis client connection.
        """
        if self.client:
            self.client.close()
            print("Redis connection closed")

    def publish(self, channel, message):
        """
        Publish a message to a Redis channel.

        :param channel: The Redis channel to publish to.
        :param message: The message to publish.
        """
        if self.client:
            self.client.publish(channel, message)

    def subscribe(self, channel):
        """
        Subscribe to a Redis channel.

        :param channel: The Redis channel to subscribe to.
        :return: Redis pubsub object.
        """
        if self.client:
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            return pubsub

    async def listen_to_channel(self, pubsub, on_message):
        """
        Listen for messages on the subscribed Redis channel.

        :param pubsub: Redis pubsub object returned by subscribe.
        :param on_message: Callback function to handle incoming messages.
        """
        if pubsub:
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    on_message(message)
                await asyncio.sleep(1)

    def sismember(self, key, value):
        """
        Check if a value is a member of a set in Redis.

        :param key: The key of the set.
        :param value: The value to check.
        :return: True if the value is a member of the set, False otherwise.
        """
        if self.client:
            return self.client.sismember(key, value)
        return False

    def rpush(self, key, *values):
        """
        Push one or more values onto the end of a list in Redis.

        :param key: The key of the list.
        :param values: Values to push onto the list.
        """
        if self.client:
            self.client.rpush(key, *values)

    def lrange(self, key, start=0, end=-1):
        """
        Get a range of values from a list in Redis.

        :param key: The key of the list.
        :param start: The start index.
        :param end: The end index.
        :return: A list of values from the specified range.
        """
        if self.client:
            return self.client.lrange(key, start, end)

    def set_expire(self, key, seconds):
        """
        Set an expiration (TTL) for a key in Redis.

        :param key: The key to set the expiration for.
        :param seconds: The expiration time in seconds.
        :return: True if the timeout was set, False otherwise.
        """
        if self.client:
            return self.client.expire(key, seconds)
        return False
