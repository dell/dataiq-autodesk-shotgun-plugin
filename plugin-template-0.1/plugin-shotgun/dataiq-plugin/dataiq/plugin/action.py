# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
import re
from typing import Union

from dataiq.plugin.action_filter import ActionFilter, JsonActionFilterSerializer
from dataiq.plugin.context import Parameter
from dataiq.plugin.util import EnumSet, Serializer


class Action:
    """Represents an action that a Plugin exposes.

    :param endpoint: URL (from Plugin root) that will trigger this Action.
    :param name: Common name of this Action. This will be used for
        display to the user.
    :param parameters: Set of Parameters that must be available in the
        context when this action is triggered.
    :param action_filter: Filter to apply on the ClarityNow-side,
        before passing the request onto the Plugin.
    """
    def __init__(self,
                 name: str,
                 endpoint: str,
                 parameters: Union[Parameter, EnumSet[Parameter]],
                 action_filter: ActionFilter,
                 validate: str = None):
        # Name
        if not isinstance(name, str):
            raise TypeError("name must be a str.")
        elif not re.fullmatch(r'\w[\w\d ]*\w', name):
            raise ValueError(f'name must be at least 3 characters, start and '
                             f'end with a word character, and only contain '
                             f'[a-zA-Z0-9]. Got "{name}"')
        # Endpoint
        if not isinstance(endpoint, str):
            raise TypeError("endpoint must be a str.")
        elif not re.fullmatch(r'/[\w-]+/', endpoint):
            raise ValueError(f'endpoint must start and end with a slash (/) and only '
                             f'contain word-characters ([\\w-]). Got "{endpoint}"')
        # Validate
        if validate is None:
            pass
        elif not isinstance(validate, str):
            raise TypeError("validate must be a str or None.")
        elif not re.fullmatch(r'/[\w-]+/', validate):
            raise ValueError(f'validate must start with a slash (/) and only '
                             f'contain word-characters. Got "{validate}"')
        # Parameters
        if isinstance(parameters, Parameter):
            parameters = EnumSet(Parameter, (parameters,))
        elif isinstance(parameters, EnumSet):
            if parameters.cls is not Parameter:
                raise TypeError("parameters must only contain Parameter.")
        else:
            raise TypeError("parameters must be a member of or "
                            "EnumSet of Parameter.")
        # Filter
        if not isinstance(action_filter, ActionFilter):
            raise TypeError("filter must be of type Filter.")

        self.endpoint: str = endpoint
        self.name: str = name
        self.parameters: EnumSet[Parameter] = parameters
        self.filter: ActionFilter = action_filter
        self.validate: str = validate

    def __repr__(self):
        return f'{self.__class__.__name__}({self.name!r}, {self.endpoint!r}, ' \
               f'{self.parameters!r}, {self.filter!r}, {self.validate!r})'


class JsonActionSerializer(Serializer):
    """Serializes an Action into a JSON array of key-value pairs."""
    def __init__(self):
        super(JsonActionSerializer, self).__init__(Action)

    def serialize(self, s: Action):
        return {
            "endpoint": s.endpoint,
            "name": s.name,
            "parameters": [p.serialized_name for p in s.parameters],
            "filter": JsonActionFilterSerializer().serialize(s.filter)
        }
