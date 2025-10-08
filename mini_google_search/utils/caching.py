from collections import OrderedDict
from typing import Any, Optional

from . import config


class LRUCache:
    def __init__(self, maxsize: int = 256):
        self.maxsize = maxsize
        self._store: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            self._store.move_to_end(key)
            return self._store[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self.maxsize:
            self._store.popitem(last=False)


def get_cache_backend():
    # Optional Redis support if environment and package are available
    if config.REDIS_URL:
        try:
            import redis  # type: ignore

            client = redis.from_url(config.REDIS_URL)
            client.ping()

            class RedisCache:
                def __init__(self, client):
                    self.client = client

                def get(self, key: str):
                    val = self.client.get(key)
                    if val is None:
                        return None
                    import pickle

                    return pickle.loads(val)

                def set(self, key: str, value: Any):
                    import pickle

                    self.client.set(key, pickle.dumps(value))

            return RedisCache(client)
        except Exception:
            pass
    return LRUCache(maxsize=config.CACHE_SIZE)

