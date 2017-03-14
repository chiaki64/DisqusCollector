#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import aiohttp
import os
import warnings
from urllib.parse import urlencode

import simplejson

INTERFACES = simplejson.loads(open(os.path.join(os.path.dirname(__file__), 'interfaces.json'), 'r').read())

HOST = 'https://disqus.com/'


class InterfaceNotDefined(NotImplementedError):
    pass


class APIError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return '%s: %s' % (self.code, self.message)


class Result(object):
    def __init__(self, response, cursor=None):
        self.response = response
        self.cursor = cursor or {}

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, repr(self.response))

    def __iter__(self):
        for r in self.response:
            yield r

    def __len__(self):
        return len(self.response)

    def __getitem__(self, key):
        return list.__getitem__(self.response, key)

    def __contains__(self, key):
        return list.__contains__(self.response, key)


class Resource:
    def __init__(self, api, interface=INTERFACES, node=None, tree=()):
        self.api = api
        self.node = node
        self.interface = interface
        if node:
            tree = tree + (node,)
        self.tree = tree

    def __getattr__(self, attr):
        if attr in getattr(self, '__dict__'):
            return getattr(self, attr)
        interface = self.interface
        if attr not in interface:
            interface[attr] = {}
            # raise InterfaceNotDefined(attr)
        return Resource(self.api, interface[attr], attr, self.tree)

    async def __call__(self, endpoint=None, **kwargs):
        return await self._request(endpoint, **kwargs)

    # async def __call__(self, *args, **kwargs):

    async def _request(self, endpoint=None, **kwargs):
        if endpoint is not None:
            resource = self.interface.get(endpoint, {})
            endpoint = endpoint.replace('.', '/')
        else:
            resource = self.interface
            endpoint = '/'.join(self.tree)

        # Check required
        for k in resource.get('required', []):
            if k not in [x.split(':')[0] for x in kwargs.keys()]:
                raise ValueError('Missing required argument: %s' % k)
        # 有method就给,没有就从json里面拿
        method = kwargs.pop('method', resource.get('method'))
        if not method:
            raise InterfaceNotDefined('Interface is not defined, you must pass ``method`` (HTTP Method).')

        api = self.api
        version = kwargs.pop('version', api.version)
        # _format = kwargs.pop('format', api.format)

        path = HOST + f'api/{version}/{endpoint}.json'
        print('kw1->', kwargs)
        if 'api_secret' not in kwargs and api.secret_key:
            kwargs['api_secret'] = api.secret_key
        if 'api_public' not in kwargs and api.public_key and 'api_key' not in kwargs:
            kwargs['api_key'] = api.public_key
            print('kw2->', kwargs)

        params = []
        for k, v in kwargs.items():
            if isinstance(v, (list, tuple)):
                for val in v:
                    params.append((k, val))
            else:
                params.append((k, v))

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
        }

        if method == 'GET':
            path = f'{path}?{urlencode(params)}'
            data = ''
        else:
            data = urlencode(params)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        async with aiohttp.ClientSession() as client:
            async with client.request(
                    method=method,
                    url=path,
                    params=data,
                    headers=headers
            ) as resp:
                data = simplejson.loads(await resp.text())
                if resp.status != 200:
                    raise APIError(data['code'], data['response'])
                if isinstance(data['response'], list):
                    return Result(data['response'], data.get('cursor'))
                return data['response']


class DisqusAPI(Resource):
    def __init__(self, secret_key=None, public_key=None, version='3.0', **kwargs):
        self.secret_key = secret_key
        self.public_key = public_key
        if not public_key:
            warnings.warn('You should pass ``public_key`` in addition to your secret key.')
        self.version = version
        super(DisqusAPI, self).__init__(self)

    def _request(self, **kwargs):
        raise SyntaxError('You cannot call the API without a resource.')

        # def _get_key(self):
        #     return self.secret_key
        #
        # key = property(_get_key)
        #
        # def setSecretKey(self, key):
        #     self.secret_key = key
        #
        # setKey = setSecretKey
        #
        # def setPublicKey(self, key):
        #     self.public_key = key
        #
        # def setFormat(self, format):
        #     self.format = format
        #
        # def setVersion(self, version):
        #     self.version = version

