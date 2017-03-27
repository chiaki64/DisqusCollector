#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import aioredis
import logging
import time
from aiohttp import web
from utils.redis import RedisFilter
from utils.disqus import DisqusAPI
from config import (SECRET_KEY,
                    PUBLIC_KEY,
                    SHORT_NAME,
                    PORT, DEV)

logging.basicConfig(
    filename='access.log',
    level=logging.INFO,
    # format='%(asctime)s::%(levelname)s::%(message)s',
    format='%(message)s',
    datefmt='%a, %Y/%m/%d %H:%M:%S',
)
logger = logging.getLogger('aiohttp.access')
logger.setLevel(logging.INFO)

disqus = DisqusAPI(SECRET_KEY, PUBLIC_KEY)


class AbsView(web.View):
    def __init__(self, request):
        super(AbsView, self).__init__(request)
        self.redis = self.request.app.redis
        self._get = self.request.GET.get
        self.match = self.request.match_info


class IndexView(AbsView):
    async def get(self):
        return web.json_response(
            {'message': 'hello, world'}
        )


class CommentView(AbsView):
    async def get(self):
        url = self._get('link', None) or self.request.headers.get('Referer', None)
        if not url:
            return web.json_response(
                {'msg': 'error'},
                status=400
            )

        comment = await self.redis.get('Comment', id=url)
        timestamp = int(time.time())
        if comment is not None:
            logger.warning(f'ts:{timestamp}, type:{type(timestamp)};ct:{comment["time"]}, type:{type(comment["time"])}')
            if timestamp - comment['time'] < 10:
                return web.json_response(comment)

        thread = await disqus.get(
            'threads.details',
            method='GET',
            forum=SHORT_NAME,
            thread=f'link:{url}'
        )
        if thread.get('id') is None:
            return web.json_response(
                {'msg': 'error'},
                status=400
            )
        posts = await disqus.get(
            'posts.list',
            method='GET',
            forum=SHORT_NAME,
            thread=thread['id']
        )
        await self.redis.set('Comment', {
            'data': posts.response,
            'time': int(time.time())
        }, id=url)
        return web.json_response({
            'data': posts.response,
            'time': int(time.time())
        })

    async def post(self):
        data = dict({}, **await self.request.post())
        if 'link' not in data:
            return web.json_response(
                {'msg': 'error'},
                status=400
            )
        thread = await disqus.get(
            'threads.details',
            method='GET',
            forum=SHORT_NAME,
            thread=f'link:{data["link"]}'
        )
        if thread.get('id') is None:
            return web.json_response(
                {'msg': 'error'},
                status=400
            )

        res = await disqus.get(
            'posts.create',
            method='POST',
            thread=thread['id'],
            author_email=data['email'],
            author_name=data['name'],
            message=data['message'],
            parent=data.get('parent'),
            api_key='E8Uh5l5fHZ6gD8U3KycjAIAk46f68Zw7C6eW8WSjZvCLXebZ7p0r1yrYDrLilk2F'
        )
        return web.json_response(res)


class RecentView(AbsView):
    async def get(self):
        posts = await disqus.get(
            'forums.listPosts',
            method='GET',
            forum=SHORT_NAME,
            limit=self._get('limit') or 10
        )
        await self.redis.set('Recent', posts.response, id='comment')
        return web.json_response(posts.response)


class SyncView(AbsView):
    async def get(self):
        data = await self.redis.list('Comment')
        return web.json_response(data)


async def init(loop):
    if DEV:
        redis_ip = 'localhost'
    else:
        redis_ip = os.environ["REDIS_PORT_6379_TCP_ADDR"]

    app = web.Application(loop=loop, middlewares=[])

    redis = await aioredis.create_redis((redis_ip, '6379'), loop=loop)
    app.redis = RedisFilter(redis)

    app.router.add_get('/', IndexView)
    app.router.add_route('*', '/comment', CommentView)
    app.router.add_route('*', '/recent', RecentView)
    app.router.add_get('/sync', SyncView)

    _handler = app.make_handler(access_log=logger,
                                access_log_format='%t::Request(%r)::Status(%s)::Time(%Tf)::IP(%{X-Real-IP}i)::Referer(%{Referer}i)::User-Agent(%{User-Agent}i)') # NOne
    await loop.create_server(_handler, '0.0.0.0', PORT)
    return _handler, app


loop = asyncio.get_event_loop()
handler, app = loop.run_until_complete(init(loop))
try:
    loop.run_forever()
except (KeyboardInterrupt, SystemExit):
    loop.run_until_complete(handler.finish_connections())
