# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
import logging
from collections import Mapping

logger = logging.getLogger('legacy.util')


def apply_nested_map(original, default, prefix=''):
    """Recurse through nested Mapping and apply missing keys from default."""
    for key, value in default.items():
        if key not in original:
            logger.debug(f'util::apply_nested_map applying default {prefix}/{key}')
            original[key] = value
        elif isinstance(original[key], Mapping)\
                and isinstance(default[key], Mapping):
            apply_nested_map(original[key], default[key], prefix+'/'+key)
