#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import aioredis
import logging
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
    format='%(asctime)s::%(levelname)s::%(message)s',
    datefmt='%a, %Y/%m/%d %H:%M:%S',
)
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
        await self.redis.set('Comment', posts.response, id=str(thread['id']))
        return web.json_response(posts.response)

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
        pass


async def logger_middleware(app, handler):
    async def middleware_handler(request):
        # if '.ico' not in request.path:
        # logging.info(
        #         f'Path:({request.path})::Method:({request.method})::User-Agent:({request.headers["User-Agent"]})::Referer:({request.headers.get("Referer")})')
        response = await handler(request)
        return response
    return middleware_handler

async def init(loop):
    if DEV:
        redis_ip = 'localhost'
    else:
        redis_ip = os.environ["REDIS_PORT_6379_TCP_ADDR"]

    app = web.Application(loop=loop, middlewares=[logger_middleware])

    redis = await aioredis.create_redis((redis_ip, '6379'), loop=loop)
    app.redis = RedisFilter(redis)

    app.router.add_get('/', IndexView)
    app.router.add_route('*', '/comment', CommentView)
    app.router.add_route('*', '/recent', RecentView)
    # app.router.add_get('/sync', SyncView)

    _handler = app.make_handler()
    await loop.create_server(_handler, '0.0.0.0', PORT)
    return _handler, app


loop = asyncio.get_event_loop()
handler, app = loop.run_until_complete(init(loop))
try:
    loop.run_forever()
except (KeyboardInterrupt, SystemExit):
    loop.run_until_complete(handler.finish_connections())
