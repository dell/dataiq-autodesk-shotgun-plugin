# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
import codecs
import logging
import re
import sys
from logging import DEBUG
from typing import List, Optional

import yaml

from dataiq.plugin.action_filter import ActionFilter, VolumeTypes, \
    ListedWithin, TagFilter, AppliesTo
from dataiq.plugin.actions import Actions
from dataiq.plugin.context import Parameter
from dataiq.plugin.util import EnumSet
from legacy_action import LegacyAction
from legacy_parameter import COMMAND_TO_PARAMETER
from util import apply_nested_map

ACTIONS = 'Actions'
PLUGIN_NAME = "Plugin Name"
GLOBAL_CONFIGURATIONS = "Global Configurations"
CRON_JOBS = "Cron Jobs"
EXTINCT_FILTERS = ['track_user_navigation',
                   'asynchronous_execution']
HTML_TYPES = ['radio', 'checkbox', 'select', 'textbox', 'textarea', 'n/a']
VALID_SECTION_NAMES = ['value', 'default', 'description',
                       'long_description', 'note', 'options']
FILTER_DEFAULTS = {
    "groups": [],
    "tags": [],
    "tag_categories": [],
    "listed_within": ['browse'],
    "volume_types": ['TYPE_VFS'],
    "applies": {
        "files": False,
        "folders": False,
        "sequences": False,
        "single_volume": False,
    },
    "max_selections": 1,
    "path_regex": "",
}

logging.basicConfig()
logging.getLogger().setLevel(DEBUG)
logger = logging.getLogger('legacy.config_parser')

print(logger.getEffectiveLevel())


def open_path(config_path):
    config = None
    with open(config_path) as f:
        try:
            config = yaml.safe_load(f)
        except Exception as e:  # pragma: not covered
            print(str(e), file=sys.stderr)  # pragma: not covered
    return config


class ConfigParser:
    def __init__(self, config_file=None, quiet=False, testing=False,
                 print_capturer=None):
        self.testing = testing
        self.quiet = quiet
        self.print_capturer = print_capturer
        self.msgDiverter = None
        if self.print_capturer:
            self.msgDiverter = codecs.open(self.print_capturer, 'w', 'utf-8')

        self.config_filename = config_file or '/plugin/ca.control'
        self.yaml = open_path(self.config_filename)
        self.plugin_name = self.yaml.get(PLUGIN_NAME, "Unnamed Plugin")

        self.param_matchers = []
        prefix = r'\%[\{]?'
        tail = r'[\}]?'
        for cmd, parameter in sorted(COMMAND_TO_PARAMETER.items(),
                                     key=lambda x: len(x[0]), reverse=True):
            regx = re.compile(f'{prefix}{cmd}{tail}')
            self.param_matchers.append((regx, parameter))
        self.globalCfg = self.flatten_global_config()
        self.crons = self.yaml.get(CRON_JOBS, {})

    def translate_none(self, d, k):
        if 'example' in d[k]:
            if isinstance(d[k]['example'], list):
                return []
            elif isinstance(d[k]['example'], dict):
                return {}
            elif isinstance(d[k]['example'], str):
                return ''
            elif isinstance(d[k]['example'], int):
                return 0
            elif isinstance(d[k]['example'], float):
                return 0.0

        if 'default' in d[k]:
            if isinstance(d[k]['default'], list):
                return []
            elif isinstance(d[k]['default'], dict):
                return {}
            elif isinstance(d[k]['default'], str):
                return ''
            elif isinstance(d[k]['default'], int):
                return 0
            elif isinstance(d[k]['default'], float):
                return 0.0
        return None

    def flatten_global_config(self, subconf=None):
        out_cfg = {}
        gconf = subconf
        if not gconf:
            gconf = self.yaml.get(GLOBAL_CONFIGURATIONS, {})
        for k in gconf:
            if k.lower().startswith("label "):
                subconf = gconf.get(k)
                flattened_cfg = self.flatten_global_config(subconf=subconf)
                for k in flattened_cfg:
                    out_cfg[k] = flattened_cfg[k]
            else:
                if isinstance(gconf[k], dict):
                    if 'value' in gconf[k]:
                        out_cfg[k] = gconf[k].get('value')
                        if out_cfg[k] is None:
                            out_cfg[k] = self.translate_none(gconf, k)
                    else:
                        out_cfg[k] = gconf[k]
                else:
                    out_cfg[k] = gconf[k]
        return out_cfg

    def guess_html_type(self, key, value):
        self.pr_i("%s's configuration parser is guessing correct "
                  "html_input_type for '%s'" % (self.plugin_name, key))
        thisType = type(value)
        retval = 'invalid'
        if value == None:
            retval = 'textbox'
        elif thisType == bool:
            retval = 'checkbox'
        elif thisType == list:
            retval = 'textarea'
        elif thisType in [str, int, float]:
            retval = 'textbox'
        elif thisType == dict:
            self.pr_w("%s's configuration parser warning: Uncommon to use a "
                      "dictionary as a configuration value\nAre you sure "
                      "the value for '%s' is correct? "
                      "Value: %s" % (self.plugin_name, key, value))
            retval = 'textarea'
        if retval == 'invalid':
            self.pr_e(
                "%s's configuration parser error: Invalid configuration "
                "type for '%s': type = %s, value = %s"
                % (self.plugin_name, key, thisType, value))
        return retval

    def correct_section(self, topkey, section):
        retdict = {}
        if type(section) == dict:
            for k in section:
                lowk = k.lower()

                if lowk in VALID_SECTION_NAMES:
                    retdict[lowk] = section[k]
                elif lowk == 'html_input_type':
                    if section[k].lower() not in HTML_TYPES:
                        self.pr_e(
                            "%s's configuration parsing error: Invalid "
                            "html_input_type in %s: '%s'"
                            % (self.plugin_name, topkey, section[k]))
                    else:
                        retdict['html_input_type'] = section[k]
                else:
                    self.pr_e("%s's configuration parsing error: Invalid "
                              "attribute within %s: '%s'"
                              % (self.plugin_name, topkey, section))
            if 'value' not in retdict:
                self.pr_e("%s's configuration parsing error: No value in "
                          "config for '%s'" % (self.plugin_name, topkey))
                raise KeyError("No value in config for '%s'" % topkey)
            if 'html_input_type' not in retdict:
                html_type = self.guess_html_type(topkey,
                                                 retdict.get('value', None))
                if html_type != 'invalid':
                    retdict['html_input_type'] = html_type
                else:
                    self.pr_e(
                        "%s's configuration parsing error: Invalid value "
                        "in config for '%s': '%s'"
                        % (self.plugin_name, topkey,
                           repr(retdict.get('value'))))
                    raise ValueError("Invalid value in config for '%s': '%s'"
                                     % (topkey, repr(retdict.get('value'))))
        else:
            retdict = {'value': section, 'default': section}
            html_type = self.guess_html_type(topkey, section)
            if html_type != 'invalid':
                retdict['html_input_type'] = html_type
            else:
                raise ValueError("Invalid value in config for '%s': '%s'"
                                 % (topkey, repr(retdict.get('value'))))
        return retdict

    def correct_globals(self, d):
        current_label = 'nolabel'
        builder = {}
        contained_keys = []
        labels_to_options = {current_label: []}
        for k in d:
            if k.lower().startswith('label '):
                new_label = k[6:]
                labels_to_options[new_label] = []
                for elem in contained_keys:
                    builder[elem]['label'] = current_label
                    labels_to_options[current_label].append(elem)
                contained_keys = []
                current_label = new_label
                options = d[k]
                for option in options:
                    contained_keys.append(option)
                    builder[option] = self.correct_section(option,
                                                           options[option])
                    # TODO - put all parse info in another python file
            else:
                contained_keys.append(k)
                builder[k] = self.correct_section(k, d[k])
        for elem in contained_keys:
            builder[elem]['label'] = current_label
            labels_to_options[current_label].append(elem)
        return builder, labels_to_options

    def _parse_filter(self, action_filter):
        # Insert default keys
        apply_nested_map(action_filter, FILTER_DEFAULTS)

        # TODO expand for better handling of HTML formatting options.

        return ActionFilter(
            action_filter['groups'],
            TagFilter(action_filter['tags'], action_filter['tag_categories']),
            EnumSet.of(*(ListedWithin[a.upper()] for a in
                         action_filter['listed_within'])),
            EnumSet.of(
                *(AppliesTo[a.upper()] for a in action_filter['applies'])),
            EnumSet.of(*(VolumeTypes[a.upper()] for a in
                         action_filter['volume_types'])),
            action_filter['max_selections'],
            action_filter['path_regex'])

    def actions(self):
        actions = Actions()
        for name, action in self.yaml[ACTIONS].items():
            self.pr_i(f'ConfigParser::actions {name}')
            endpoint = action.get('endpoint', '/execute')

            cmdline = action.get('command')
            if not cmdline:
                raise ValueError(f'Action {name} must include command.')

            legacy_action = LegacyAction(
                name,
                endpoint,
                cmdline,
                self._parse_filter(action['filter']),
                action.get('validate', '') or '/validate/')
            actions.add(legacy_action)
        return actions

    def pr_e(self, msg): # pragma: not covered
        if not self.quiet:
            if not self.print_capturer:
                logger.error(msg) # pragma: not covered
            else:
                self.msgDiverter.write('%s\n' % msg)

    def pr_i(self, msg): # pragma: not covered
        if not self.quiet:
            if not self.print_capturer:
                logger.info(msg) # pragma: not covered
            else:
                self.msgDiverter.write('%s\n' % msg)

    def pr_w(self, msg): # pragma: not covered
        if not self.quiet:
            if not self.print_capturer:
                logger.warning(msg) # pragma: not covered
            else:
                self.msgDiverter.write('%s\n' % msg)
