# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
from abc import abstractmethod, ABC
from enum import Enum
from typing import Iterable, Generic, TypeVar, Union, Type, Mapping, VT, \
    Dict

T = TypeVar('T')
EnumType = TypeVar('EnumType', bound=Enum)


class PluginEnum(Enum):
    """Custom Enum wrapper with some convenience methods.

    :param serialized_name: The key used for the parameter over the network between
        ClarityNow and the plugin.

    Assigning enum values to auto() will use the enum name
    instead of an integer.

    OR-ing a PluginEnum with another member of the same PluginEnum will return
    an EnumSet of the two values.
    """

    def __init__(self, serialized_name):
        self.serialized_name: str = serialized_name

    def __or__(self, other: 'PluginEnum'):
        if isinstance(other, self.__class__):
            return EnumSet(self.__class__, (self, other))
        raise NotImplemented


class _ClsValidator(Generic[T]):
    """Base class for anything which needs to validate type in a collection."""

    def __init__(self, cls: Type[T]):
        self._cls = cls

    @property
    def cls(self) -> Type[T]:
        """The class that is validated against."""
        return self._cls

    def _validate(self, *s: T):
        """Return if all items in s are instances of the validated type."""
        return all(isinstance(i, self._cls) for i in s)


# Note, these two Enum classes use `set` and `dict` internally over their ABC
# counterpart to simplify implementation. Validation is only performed on the
# overridden methods. A complete implementation would re-implement all
# requisite methods.
class EnumSet(set, _ClsValidator[EnumType]):
    """A set that only accepts members of a given Enum class."""

    def __init__(self, cls: Type[EnumType], iterable: Iterable[EnumType] = ()):
        if not issubclass(cls, Enum):
            raise TypeError('cls must be an Enum.')
        _ClsValidator.__init__(self, cls)  # Must be called before _validate
        iterable = list(iterable)
        if not self._validate(*iterable):
            raise TypeError(f'iterable must only contain elements of {cls}')
        set.__init__(self, iterable)

    def __repr__(self):
        s = ', '.join(i.name for i in self)
        return f'{self.__class__.__name__}({self.cls.__name__}, {{{s}}})'

    def __or__(self, other: Union[EnumType, 'EnumSet[EnumType]']):
        if isinstance(other, EnumSet):
            if other.cls is not self.cls:
                raise TypeError(f'Cannot combine {other} and {self} because '
                                f'they are for different types: {other.cls} '
                                f'vs. {self.cls}.')
            s = self.copy()
            s.update(other)
        else:
            s = self.copy()
            s.add(other)
        return s

    def add(self, other: EnumType) -> None:
        if not self._validate(other):
            raise TypeError(f'Cannot add {other} to set because it is not '
                            f'a {self.cls}.')
        super(EnumSet, self).add(other)

    def copy(self) -> 'EnumSet[EnumType]':
        return EnumSet(self.cls, self)

    @staticmethod
    def of(*a: EnumType) -> 'EnumSet[EnumType]':
        """Convenience wrapper to EnumSet(type(a[0], a)."""
        cls = type(a[0])
        return EnumSet(cls, a)

    @staticmethod
    def all_of(cls: Type[EnumType]):
        """Create an EnumSet with all members."""
        return EnumSet.of(*cls)
        

    def update(self, *s: 'Iterable[EnumType]') -> None:
        for i in s:
            if (isinstance(i, EnumSet)) and (i.cls is not self.cls):
                raise TypeError(f'Cannot update {self} with {i} because it is'
                                f'an EnumSet for a different Enum.')
            elif not all(isinstance(x, self.cls) for x in i):
                raise TypeError(f'Cannot update {self} with {i} because the '
                                f'items are not all {self.cls}')
        super(EnumSet, self).update(*s)


class EnumMap(dict, _ClsValidator[EnumType], Mapping[EnumType, VT]):
    """A dictionary that only accepts keys of a given Enum class"""

    def __init__(self, cls: Type[EnumType], **kwargs: VT):
        if not issubclass(cls, Enum):
            raise TypeError('cls must be an Enum.')
        dict.__init__(self)
        _ClsValidator.__init__(self, cls)  # Must be called before _validate
        kw: Dict[EnumType, VT] = {cls[key]: val for key, val in kwargs.items()}
        self._validate(*kw.keys())
        self.update(kw)

    def __repr__(self):
        fmt = ', '.join((f'{k.name}: {v!r}' for k, v in self.items()))
        return f'{self.__class__.__name__}({fmt})'

    def __getitem__(self, item):
        if not self._validate(item):
            raise KeyError(f'Key must be a {self.cls.__name__}')
        return super(EnumMap, self).__getitem__(item)

    def __setitem__(self, key: EnumType, value: VT):
        if not self._validate(key):
            raise TypeError(f'Key must be a {self.cls}')
        return super(EnumMap, self).__setitem__(key, value)


class Serializer(_ClsValidator[T], ABC):
    """Interface for declaring something serializable.

    This will be used to send data back to the user. Be aware of any private
    internal details that should not be made available to the user, and remember
    to never trust user input when serialized objects are expected to be
    returned exactly as sent.
    """

    @abstractmethod
    def serialize(self, s: T):
        """Return the serialized form of s."""
        raise NotImplementedError()
