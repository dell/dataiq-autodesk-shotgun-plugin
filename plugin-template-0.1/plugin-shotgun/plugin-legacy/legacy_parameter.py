# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
from typing import Dict, Optional

from dataiq.plugin.context import Parameter
from dataiq.plugin.util import PluginEnum


class LegacyParameter(PluginEnum):
    GROUPS = (Parameter.GROUPS, 'group')
    PPATHS = (Parameter.PPATHS, 'pfile')
    PPATH = (Parameter.PPATH, 'p')
    USER = (Parameter.USER, 'u')
    VPATHS = (Parameter.VPATHS, 'vfile')
    VPATH = (Parameter.VPATH, 'v')
    JOB_ID = (None, 'guitoken')
    CLIENTLOGIN = (Parameter.CLIENTLOGIN, 'clientLogin')
    CLIENTIP = (Parameter.CLIENTIP, 'clientIP')
    VALIDATE = (Parameter.VALIDATE, 'validate')
    SEARCH = (Parameter.SEARCH, 'search')
    MAXXY = (Parameter.MAXXY, 'maxXY')
    IMAGE = (Parameter.IMAGE, 'image')
    TEXT = (Parameter.TEXT, 'text')
    CLIP = (Parameter.CLIP, 'clip')
    JSON = (Parameter.JSON, 'json')
    SEQ = (Parameter.SEQ, 'seq')
    TAG = (Parameter.TAG, 'tag')

    def __init__(self, parameter: Optional[Parameter], command_name: str):
        self.parameter = parameter
        PluginEnum.__init__(self,
                            None if parameter is None else parameter.serialized_name)
        self.command_name = command_name


COMMAND_TO_PARAMETER: Dict[str, LegacyParameter] = \
    {p.command_name: p for p in LegacyParameter}
"""Map of LegacyParameter command names to LegacyParameter."""
