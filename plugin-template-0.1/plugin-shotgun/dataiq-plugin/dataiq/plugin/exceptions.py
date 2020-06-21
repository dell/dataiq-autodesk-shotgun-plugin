# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
import html


class PluginException(Exception):
    def __init__(self, code, msg):
        super(PluginException, self).__init__(html.escape(msg))
        self.code = code


class BadRequest(PluginException):
    def __init__(self, msg):
        super(BadRequest, self).__init__(400, msg)


class UnknownContextKeyException(BadRequest):
    def __init__(self, key):
        super(UnknownContextKeyException, self).__init__(
            f'Unknown context parameter {key}.')
