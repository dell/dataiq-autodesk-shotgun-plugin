# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
from typing import Union, Iterator, Optional

from dataiq.plugin.action import Action
from dataiq.plugin.action_filter import ActionFilter
from dataiq.plugin.context import Parameter
from dataiq.plugin.util import EnumSet

from legacy_parameter import LegacyParameter, COMMAND_TO_PARAMETER


class LegacyAction(Action):
    """Legacy Plugin implementation-specific information for an Action.

    :param endpoint: URL (from Plugin root) that will trigger this Action.
    :param name: Common name of this Action. This will be used for
        display to the user.
    :param parameters: Set of Parameters that must be available in the
        context when this action is triggered.
    :param action_filter: Filter to apply on the ClarityNow-side,
        before passing the request onto the Plugin.
    :param command: Command to execute on the shell.
    :param validate: Endpoint to hit to validate this action.
    """
    def __init__(self,
                 name: str,
                 endpoint: str,
                 command: str,
                 action_filter: ActionFilter,
                 validate: str = None):
        self.command = command
        params: Iterator[LegacyParameter] = \
            filter(lambda token: isinstance(token, LegacyParameter), self.tokens)
        params: Iterator[Optional[Parameter]] = map(lambda lp: lp.parameter, params)
        params: Iterator[Parameter] = filter(lambda x: x is not None, params)
        params: EnumSet[Parameter] = EnumSet(Parameter, params)
        super().__init__(
            name,
            endpoint,
            params,
            action_filter,
            validate
        )

    @property
    def tokens(self) -> Iterator[Union[str, LegacyParameter]]:
        """Yield the composite tokens of the given command. Will be either str or
        LegacyParameter
        """
        in_variable = False
        stack = 0
        buffer = ''

        for c in self.command:
            if c == '%':
                yield buffer
                buffer = ''
                in_variable = True
                continue
            elif in_variable:
                if stack == 0 and c == '{':
                    stack += 1
                    continue
                elif c == '}':
                    stack -= 1
                    if stack == 0:
                        yield COMMAND_TO_PARAMETER[buffer]
                        buffer = ''
                        in_variable = False
                        continue
                elif not c.isalpha():
                    if stack == 0:
                        yield COMMAND_TO_PARAMETER[buffer]
                        buffer = c
                        in_variable = False
                        continue
                    else:
                        raise ValueError('Shell command string has mismatched {}\'s.')
            buffer += c
        if in_variable:
            yield COMMAND_TO_PARAMETER[buffer]
        else:
            yield buffer
