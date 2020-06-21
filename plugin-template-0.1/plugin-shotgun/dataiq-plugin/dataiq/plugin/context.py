# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
from typing import VT, Dict, Any

from flask import Request

from dataiq.plugin.exceptions import UnknownContextKeyException, BadRequest
from dataiq.plugin.util import EnumMap, PluginEnum


class Parameter(PluginEnum):
    """The enumerated items that can be used as parameters to a plugin execution."""
    GROUPS = ('group',)
    PPATHS = ('pfile',)
    PPATH = ('p',)
    USER = ('user',)
    VPATHS = ('vfile',)
    VPATH = ('v',)
    CLIENTLOGIN = ('client_login',)
    CLIENTIP = ('client_ip',)
    VALIDATE = ('validate',)
    SEARCH = ('search',)
    MAXXY = ('max_xy',)
    IMAGE = ('image',) 
    TEXT = ('text',)
    CLIP = ('clip',)
    JSON = ('json',)
    SEQ = ('seq',)
    TAG = ('tag',)


_serialized_to_parameter = {p.serialized_name: p for p in Parameter}


class Context(EnumMap[Parameter, VT]):
    def __init__(self):
        super(Context, self).__init__(Parameter)

    @classmethod
    def from_request(cls, request: Request):
        j = request.get_json(force=True, silent=True)
        if j is None:
            raise BadRequest('Context JSON not present or not formatted properly.')
        if 'context' not in j:
            raise BadRequest('Context JSON must be enveloped in "context" key.')
        ctx = j['context']
        if not isinstance(ctx, dict):
            raise BadRequest('Context JSON must be an object. Got: ' + str(type(ctx)))

        context = Context()
        try:
            for key, value in ctx.items():
                context[_serialized_to_parameter[key]] = value
        except KeyError as e:
            raise UnknownContextKeyException(e) from e
        return context

    def require(self, *keys: Parameter):
        yield from (self[k] for k in keys)

    def json(self):
        return {k.name: v for k, v in self.items()}


class LazyContext(Context):
    def __init__(self, request: Request):
        super(LazyContext, self).__init__()
        self._lazy: Dict[str, Any] = request.get_json()['context']

    def __getitem__(self, item: Parameter):
        if isinstance(item, self.cls):
            try:
                return super(LazyContext, self).__getitem__(item)
            except KeyError as e:
                try:
                    r = self._lazy[item.serialized_name]
                except KeyError as e2:
                    raise e2 from e
                self[item] = r
                return r
        return super(LazyContext, self).__getitem__(item)

    def __str__(self):
        return 'LazyContext(cached={})'.format(tuple(self.items()))
