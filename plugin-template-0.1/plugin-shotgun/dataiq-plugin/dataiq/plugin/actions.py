# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
from typing import Iterable, List

from dataiq.plugin.action import Action, JsonActionSerializer
from dataiq.plugin.util import Serializer


class Actions:
    _actions: List[Action]

    def __init__(self, actions: Iterable[Action] = None):
        """The collection of Actions that a Plugin exposes.

        :arg actions: The initial iterable of actions.
        """
        self._actions = []
        if actions is not None:
            for action in actions:
                self.add(action)

    def __iter__(self) -> Iterable[Action]:
        return iter(self._actions)

    def __repr__(self):
        return f'{self.__class__.__name__}({self._actions!r})'

    def add(self, action: Action):
        """Add a new action to the list."""
        if not isinstance(action, Action):
            raise TypeError("action must be an Action")
        self._actions.append(action)
        return self


class JsonActionsSerializer(Serializer):
    """Serializes an Actions into a JSON list of Action elements."""

    def __init__(self):
        super(JsonActionsSerializer, self).__init__(Actions)

    def serialize(self, s: Actions):
        return [JsonActionSerializer().serialize(a) for a in s]
