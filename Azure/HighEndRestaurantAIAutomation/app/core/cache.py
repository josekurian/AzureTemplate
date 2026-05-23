try:
    import redis.asyncio as aioredis
except Exception:
    aioredis = None

class Cache:
    def __init__(self, url=None):
        self.url = url
        self.client = None

    async def connect(self):
        if aioredis is None:
            return
        self.client = aioredis.from_url(self.url)

    async def get(self, key):
        if not self.client:
            return None
        return await self.client.get(key)

    async def set(self, key, value, ex=None):
        if not self.client:
            return False
        await self.client.set(key, value, ex=ex)
        return True
