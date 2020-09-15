#!/usr/bin/python
# Copyright (c) 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.

from __future__ import print_function # Use Python 3 printing
import yaml
import logging
import traceback
from logging import DEBUG
logging.basicConfig()
logging.getLogger().setLevel(DEBUG)

class CfgReader:
    def __init__(self, logging_name, 
                 config_path='/hoststorage/.configs/ca.control'):
        self.plugin_name = logging_name.split('.')[-1]
        self.config_path = config_path
        self.logger = logging.getLogger(logging_name) 

    def get_full_config(self):
        self.logger.info("Attempting to read %s's configuration "
                         "file: %s" % (self.plugin_name, self.config_path))
        config = None
        try:
            with open(self.config_path) as f:
                try:
                    config = yaml.safe_load(f)
                except Exception as e:  # pragma: not covered
                    self.logger.error("Could not parse YAML in configuration "
                                      "file\nTraceback: %s" 
                                      % traceback.format_exc())
        except IOError:
            self.logger.error("Could not open configuration file\n"
                              "Traceback: %s" % traceback.format_exc())
        return config
    
    def get_globals(self):
        full = self.get_full_config()
        gconf = None
        if full != None:
            try:
                gconf = full["Global Configurations"]
            except KeyError:
                self.logger.error("Could not find 'Global Configurations' in "
                                  "%s's configuration file: %s"
                                  % (self.plugin_name, self.config_path))
        return gconf

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

    def global_configs(self, subconf=None):
        out_cfg = {}
        gconf = subconf
        if not gconf:
            gconf = self.get_globals() 
        for k in gconf:
            if k.lower().startswith("label "):
                subconf = gconf.get(k)
                flattened_cfg = self.global_configs(subconf=subconf)
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
