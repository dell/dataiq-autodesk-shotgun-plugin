# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.

import os
import tempfile
from collections import deque
from typing import Callable

from dataiq.plugin.context import Context

from legacy_action import LegacyAction
from legacy_parameter import LegacyParameter


class PluginExecution:
    """An instance of a plugin execution."""

    def __init__(self, action: LegacyAction, context: Context, job_id: str,
                 enable_validation: bool):
        self._action = action
        self._context = context
        self._job_id = job_id
        self._cleanup_tasks: deque[Callable] = deque()
        self._enable_validation = enable_validation

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """Run all cleanup tasks."""
        while True:
            try:
                clean = self._cleanup_tasks.pop()
            except IndexError as _:
                break
            try:
                clean()
            except Exception as e:
                print('Exception raised in execution cleanup: ' + str(e))  # TODO log

    @property
    def shell_command(self) -> str:
        cmd = ''
        for token in self._action.tokens:
            if isinstance(token, str):
                cmd += token
            else:
                cmd += self._populate_parameter(token)
        return cmd

    def _populate_parameter(self, legacy: LegacyParameter) -> str:
        """Return the substitution that should be performed for the given parameter."""
        if legacy == LegacyParameter.JOB_ID:
            return self._job_id
        elif legacy == LegacyParameter.GROUPS:
            return ','.join(self._context[legacy.parameter])
        elif legacy in [LegacyParameter.PPATHS, LegacyParameter.VPATHS]:
            # Make a temp file of these and pass it to the script.
            contents = bytes('\n'.join(self._context[legacy.parameter]), 'utf-8')
            return self._make_temp_file(contents)
        elif legacy == LegacyParameter.VALIDATE:
            return '0' if not self._enable_validation else '1'
        else:
            return self._context[legacy.parameter]

    def _make_temp_file(self, contents: bytes) -> str:
        """Create a temporary file that will be cleaned up upon job completion.

        :return: the absolute path to the temporary file.
        """
        tmp_name = None
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_name = tmp.name
            self._cleanup_tasks.append(lambda: os.remove(tmp_name))
            tmp.write(contents)
        return tmp_name
