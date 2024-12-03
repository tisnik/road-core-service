"""Integration tests for real Redis behaviour."""

import pytest

from ols.app.models.config import RedisConfig
from ols.app.models.models import CacheEntry
from ols.src.cache.redis_cache import RedisCache

USER_ID = "00000000-0000-0000-0000-000000000001"
CONVERSATION_ID = "00000000-0000-0000-0000-000000000002"

redis_cache: RedisCache


@pytest.mark.redis
def setup():
    """Setups the Redis client."""
    global redis_cache

    # please note that the setup expect Redis running locally on default port
    redis_config = RedisConfig(
        {
            "host": "localhost",
            "port": 6379,
            "max_memory": "100mb",
            "max_memory_policy": "allkeys-lru",
            "retry_on_error": "false",
            "retry_on_timeout": "false",
        }
    )

    redis_cache = RedisCache(redis_config)


@pytest.mark.redis
def test_conversation_in_redis():
    """Check the elementary GET operation and insert_or_append operation."""
    # make sure the cache is empty
    redis_cache.redis_client.delete(USER_ID + ":" + CONVERSATION_ID)

    # the initial value should be empty
    retrieved = redis_cache.get(USER_ID, CONVERSATION_ID)
    assert retrieved is None

    # insert some conversation
    cache_entry = CacheEntry(query="First human message", response="First AI response")
    redis_cache.insert_or_append(USER_ID, CONVERSATION_ID, cache_entry)

    # check what is stored in conversation cache
    retrieved = redis_cache.get(USER_ID, CONVERSATION_ID)
    assert retrieved is not None

    # just the initial cache_entry should be stored
    assert retrieved == cache_entry

    # append more conversation
    cache_entry_2 = CacheEntry(
        query="Second human message", response="Second AI response"
    )

    redis_cache.insert_or_append(USER_ID, CONVERSATION_ID, cache_entry_2)

    # check what is stored in conversation cache
    retrieved = redis_cache.get(USER_ID, CONVERSATION_ID)
    assert retrieved is not None

    # now both conversations should be stored
    assert retrieved == [cache_entry, cache_entry_2]
