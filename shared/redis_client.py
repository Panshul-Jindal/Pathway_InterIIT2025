# shared/redis_client.py
import redis.asyncio as redis
import os

# Global Redis client
redis_client = redis.Redis.from_url(
    os.getenv('REDIS_URL', 'redis://localhost:6379'),
    decode_responses=True
)