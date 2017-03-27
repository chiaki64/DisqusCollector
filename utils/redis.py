#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import aioredis
import asyncio
import pickle
from config import REDIS_NAME


class RedisFilter:
    def __init__(self, redis):
        self._connection = redis

    async def set(self, table, data, id):
        key = f'{self.prefix(table)}.{id}'
        value = pickle.dumps(data)
        await self._connection.set(key, value)
        return id

    async def get(self, table, id):
        key = self.prefix(table) + id
        value = await self._connection.get(key)
        return None if value is None else pickle.loads(value)

    async def list(self, table):
        data = []
        array = await self._connection.keys(self.prefix(table) + '*')
        for item in array:
            _id = str(item, encoding='utf-8')[len(self.prefix(table)) + 1:]
            value = await self.get(table, _id)
            data.append(value)
        return data

    @staticmethod
    def prefix(table):
        return f'{REDIS_NAME}:{table}'

    async def close(self):
        return self._connection.close()


async def redis_server(loop):
    redis = await aioredis.create_redis(('localhost', 6379), loop=loop)
    redis = RedisFilter(redis)
    await redis.set('Comment', {'comment': {'a': 'b'}}, id='adsadasds')
    data = await redis.get('Comment', id='adsadasds')
    print(data)
    await redis.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(redis_server(loop))
