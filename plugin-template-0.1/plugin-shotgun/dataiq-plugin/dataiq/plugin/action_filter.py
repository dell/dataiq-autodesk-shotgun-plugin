# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
from typing import Iterable, Union

from dataiq.plugin.util import Serializer, EnumSet, PluginEnum


class AppliesTo(PluginEnum):
    """Where the Plugin can pre-filter based on user selections."""
    FILES = ('files',)
    FOLDERS = ('folders',)
    SEQUENCES = ('sequences',)
    SINGLE_VOLUME = ('single_volume',)


class ListedWithin(PluginEnum):
    """Where the Action appears."""
    MAIN = ('main',)
    BROWSE = ('browse',)  # Standard Plugin location, middle-right
    DETAILS = ('details',)  # Details Pane, lower-right
    SEARCH = ('search',)
    TAGS = ('tags',)


class VolumeTypes(PluginEnum):
    """A volume type filter."""
    TYPE_NFS = ('nfs',)
    TYPE_S3 = ('s3',)
    TYPE_VFS = ('vfs',)


class TagFilter:
    def __init__(self, tags: Iterable[str], categories: Iterable[str]):
        self.tags: Iterable[str] = tags
        self.categories: Iterable[str] = categories

    def __repr__(self):
        return f'{self.__class__.__name__}({self.tags!r}, {self.categories!r})'


class ActionFilter:
    """Set of filters that Actions can set for themselves to restrict or refine
    access.

    :param groups: Groups that the Action grants access to. If this is a string it is
        interpreted as a space-delineated list of groups.
    :param tags: Tags that the selection must belong to.
    :param listed_within: Where on the GUI the Action should be displayed.
    :param applies_to: Selection types the Action pre-filters for.
    :param volume_types: Volume Types to pre-filter Action on.
    :param path_regex: Regex that the selection path must match as a
        prerequisite.
    """
    def __init__(
            self,
            groups: Iterable[str],
            tags: TagFilter,
            listed_within: Union[ListedWithin, EnumSet[ListedWithin]],
            applies_to: Union[AppliesTo, EnumSet[AppliesTo]],
            volume_types: Union[VolumeTypes, EnumSet[VolumeTypes]],
            max_selections: int,
            path_regex: str):
        # Groups
        if isinstance(groups, str):
            groups = groups.split(' ')
        if not all(isinstance(g, str) for g in groups):
            raise TypeError('groups must only contain strings.')
        # Listed Within
        if isinstance(listed_within, ListedWithin):
            listed_within = EnumSet.of(listed_within)
        if not isinstance(listed_within, EnumSet) \
                or listed_within.cls is not ListedWithin:
            raise TypeError('listed_within must be an EnumSet of ListedWithin')
        # Applies To
        if isinstance(applies_to, AppliesTo):
            applies_to = EnumSet.of(applies_to)
        if not isinstance(applies_to, EnumSet) \
                or applies_to.cls is not AppliesTo:
            raise TypeError('applies_to must be an EnumSet of AppliesTo')
        # Volume Types
        if isinstance(volume_types, VolumeTypes):
            volume_types = EnumSet.of(volume_types)
        if not isinstance(volume_types, EnumSet) \
                or volume_types.cls is not VolumeTypes:
            raise TypeError('volume_type must be an EnumSet of VolumeType')

        self.groups: Iterable[str] = groups
        self.tags: TagFilter = tags
        self.listed_within: EnumSet[ListedWithin] = listed_within
        self.applies_to: EnumSet[AppliesTo] = applies_to
        self.volume_types: EnumSet[VolumeTypes] = volume_types
        self.max_selections: int = max_selections
        self.path_regex: str = path_regex

    def __repr__(self):
        return f'{self.__class__.__name__}({self.groups!r}, {self.tags!r}, ' \
               f'{self.listed_within!r}, {self.applies_to!r}, {self.volume_types!r}, ' \
               f'{self.max_selections!r}, {self.path_regex!r})'


class JsonActionFilterSerializer(Serializer):
    def __init__(self):
        super(JsonActionFilterSerializer, self).__init__(ActionFilter)

    def serialize(self, s: ActionFilter):
        return {
            "groups": list(s.groups),
            "tags": s.tags.tags,
            "tag_categories": s.tags.categories,
            "listed_within": [l.serialized_name for l in s.listed_within],
            "applies_to": [a.serialized_name for a in s.applies_to],
            "volume_types": [v.serialized_name for v in s.volume_types],
            "max_selections": s.max_selections,
            "path_regex": s.path_regex
        }
