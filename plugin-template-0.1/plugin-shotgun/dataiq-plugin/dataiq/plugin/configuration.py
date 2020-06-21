# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
from typing import List

from dataiq.plugin.actions import Actions, JsonActionsSerializer
from dataiq.plugin.util import Serializer


class Configuration:
    groups: List[str]
    actions: Actions
    has_visible_settings: bool

    def __init__(self,
                 groups: List[str],
                 actions: Actions,
                 has_visible_settings: bool):
        """Create a configuration for a plugin.

        Every DataIQ plugin must have a configuration, containing the pertinent public
        data that ClarityNow and IXUI need to interface properly with the plugin.

        :arg groups: A list of groups that are allowed to access the plugin. An empty
            list implies no filtering at the plugin level.
        :arg actions: The actions that the plugin exposes to the user.
        :arg has_visible_settings: Boolean that indicates whether IXUI should give the
            user the ability to change this configuration.
        """
        if not isinstance(groups, list):
            raise TypeError('groups must be a list.')
        if not isinstance(actions, Actions):
            raise TypeError('actions must be an Actions.')
        if not isinstance(has_visible_settings, bool):
            raise TypeError('has_visible_settings must be a boolean.')

        self.groups = groups
        self.actions = actions
        self.has_visible_settings = has_visible_settings


class JsonConfigurationSerializer(Serializer):
    def __init__(self):
        super().__init__(Configuration)

    def serialize(self, s: Configuration):
        return {
            'groups': s.groups,
            'actions': JsonActionsSerializer().serialize(s.actions),
            'has_visible_settings': s.has_visible_settings
        }
