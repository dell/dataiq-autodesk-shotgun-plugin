#!/usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import print_function # Use Python 3 printing
# Data mover Plugin for ClarityNow!
# Copyright (C) 2020 by DataFrameworks, Inc. - all rights reserved
# A plugin license is required.
# Summary: The shotgun plugin connects to the shotgun API and applies tag to the shots found on the filesystem
# Notes:
# - Place script in /usr/local/claritynow/scripts/plugins.d/cn_shotgun (with matching ccmtools.py and ccm.control)
# - Set executable: chmod +x cn_petagene.py ccmtools.py
# - Install the python requirements: pip install -r requirements.txt
# - Add the autotagging rule from autotag.cfg.cn_shotgun.sample in /usr/local/claritynow/etc/autotag.cfg
# - Place the cn_shotgun file in /etc/cron.d/
# - Designed for Python version 2.7
# Changelog:
# v1.0-1 2020-03-31 Initial release
# v1.0-2 2020-04-23 Cron task update
# v1.0-3 2020-04-24 DataIQ compatility

import os

IDENT = u'cn_shotgun'
NAME = u'cn_shotgun.py'
VERSION = '1.0'
LOGGING_NAME = 'legacy.%s' % IDENT
# Get the current platform from the environment variable SHOTGUN_PLUGIN_MODE. Available options: "cn", "dataiq"
# Default is cn
PLATFORM_MODE = os.environ.get('SHOTGUN_PLUGIN_MODE', 'cn')

import sys
sys.path.append('/usr/local/claritynow/scripts/python')
import claritynowapi
import ccmtools
import traceback
import socket
import datetime
import time
import shotgun_api3

class ShotgunPlugin:
    def __init__(self, scriptFilePath):
        # CN tag categories
        self.SHOT_TAG_CAT = 'shot'
        self.SHOT_STATUS_CAT = 'shotgun_status'
        self.SHOT_VERSION_CAT = 'shotgun_version'
        # CN Server settings
        self.CNSERVER = 'localhost'
        # CN config
        self.cncfg = ccmtools.CcmConfig(scriptFilePath, IDENT)
        self.dataiqcfg = self._get_dataiq_cfg()
        # Prepare connection to ClarityNow server
        username, password = self.cncfg.getCredentials()
        self.api = claritynowapi.ClarityNowConnection(username, password, self.CNSERVER)
        self.server_map = ccmtools.ServerMap(self.api)
        # Prepare logging
        self.debug = (self._get_from_config('debug') == "True")
        self.facility = self._get_from_config('facility')
        if PLATFORM_MODE == 'dataiq':
            import logging
            logging.basicConfig()
            logging.getLogger().setLevel(self.debug)
            self.log = logging.getLogger(LOGGING_NAME)
        else:
            self.log = ccmtools.CcmLog(IDENT, ('v%s' % VERSION,), debug=self.debug, facility=self.facility)
        # Prepare shotgun API
        self.shotgun_api_url = self._get_from_config('shotgunAPIUrl')
        self.shotgun_api_script_name = self._get_from_config('shotgunAPIScriptName')
        self.shotgun_api_key = self._get_from_config('shotgunAPIKey')
        self.sg = shotgun_api3.Shotgun('https://'+self.shotgun_api_url, script_name=self.shotgun_api_script_name, api_key=self.shotgun_api_key)
        # Plugin utils
        self.unique_tags_to_create = set()
        self.implied_tag_updates = []
        self.implied_tags_to_delete = []
        self.tag_updates = []
        self.expiration_delay = self._get_from_config('expirationDelay')
        self.shotgun_status_finalized = 'fin'

    def _format_log(self, log_tuple):
        if PLATFORM_MODE == 'dataiq':
            return ', '.join(str(i) for i in log_tuple)
        return log_tuple

    def _get_dataiq_cfg(self):
        if PLATFORM_MODE == 'dataiq':
            from plugin_configs import CfgReader
            reader = CfgReader(LOGGING_NAME)
            return reader.get_globals()
        return None

    def _get_from_config(self, name):
        if PLATFORM_MODE == 'dataiq':
            return self.dataiqcfg.get(name)
        return self.cncfg.getFromIdent(name)

    def _retrieve_shot_tags(self):
        return self.api.getTags(self.SHOT_TAG_CAT)

    def _retrieve_shotgun_shots(self):
        fields = ['code', 'project', 'sg_sequence', 'sg_versions', 'sg_status', 'sg_status_list']
        #fields = ['code', 'project', 'sg_sequence', 'sg_versions', 'sg_status', 'sg_status_list', 'assets', 'addressings_cc', 'sg_cut_duration', 'sg_cut_in', 'sg_cut_order', 'sg_cut_out' ,'description', 'id', 'open_notes_count', 'sg_shot_type', 'task_template', 'created_by', 'created_at', 'updated_at', 'updated_by', 'tags']
        filters = []
        return self.sg.find('Shot', filters, fields)

    def _find_shotgun_shot_by_unique_name(self, name, shots):
        # Find a shotgun shot using the tag unique id name from CN
        # Returns None if no version is found
        splitted_name = name.split('_')
        if len(splitted_name) != 3:
            return None
        for shot in shots:
            if shot['code'] == splitted_name[2] and shot['sg_sequence']['name'] == splitted_name[1] and shot['project']['name'] == splitted_name[0]:
                return shot
        return None

    def _find_shotgun_version_by_name(self, name, versions):
        # Find a shotgun version by name
        # Returns None if no version is found
        for version in versions:
            if version['name'] == name:
                return version
        return None

    def _get_or_create_category(self, name):
        try:
            category_id = self.api.getTagCategory(name).id
        except:
            category_id = self.api.addTagCategory(claritynowapi.TagCategoryData(name=name))
            pass
        return dict(id=category_id, category_name=name)

    def _get_or_create_tag(self, category_name, name):
        try:
            tag = self.api.getTag(category_name, name).id
        except:
            tag = self.api.addTag(category_name, claritynowapi.TagData(name=name))
            pass
        return dict(id=tag, category_name=category_name, tag_name=name)

    def _update_tag(self, tag_data):
        try:
            self.api.changeTag(tag_data)
        except:
            self.log.error(self._format_log(('Failed to update tag data', tag_data.name)))

    def _get_implied_tags_for_tag(self, category_name, name):
        # Get the list of implied tag strings for a given parent tab
        try:
            return self.api.bulkGetImpliedTags(['{0}/{1}'.format(category_name, name)])[0]
        except:
            return []

    def _get_shot_path_info_by_tag(self, shot_tag):
        # Find path associated with a shot tag
        # We can assume the tag is only applied on one path
        try:
            request = claritynowapi.FastStatRequest()
            request.resultType = claritynowapi.FastStatRequest.ALL_PATHS
            subRequest = claritynowapi.SubRequest()
            subRequest.filters.append(claritynowapi.TagFilter([shot_tag.id]))
            request.requests.append(subRequest)
            result = self.api.report(request)
            return result.requests[0].results[0].paths[0]
        except:
            return None

    def _get_folder_content(self, vpath):
        # List the content of a virtualPath
        try:
            return self.api.enumerateFolderFromDb(vpath)
        except:
            return []

    def _handle_shot_status(self, shot_tag, shot):
        # Determine if a shot status implied tag needs to be updated
        current_implied_tags = self._get_implied_tags_for_tag(self.SHOT_TAG_CAT, shot_tag.name)
        new_implied_tag = '{0}/{1}'.format(self.SHOT_STATUS_CAT, shot['sg_status_list'])
        if new_implied_tag not in current_implied_tags:
            self.unique_tags_to_create.add(new_implied_tag)
            self.implied_tag_updates.append(('{0}/{1}'.format(self.SHOT_TAG_CAT, shot_tag.name), [new_implied_tag]))
            self.implied_tags_to_delete.append(('{0}/{1}'.format(self.SHOT_TAG_CAT, shot_tag.name), current_implied_tags))
            # Update the expiration if needed
            if shot['sg_status_list'] == self.shotgun_status_finalized and self.expiration_delay:
                expiration = datetime.datetime.now() + datetime.timedelta(days=int(self.expiration_delay))
                shot_tag.expiration = time.mktime(expiration.timetuple())
                self._update_tag(shot_tag)
            elif shot['sg_status_list'] != self.shotgun_status_finalized:
                shot_tag.expiration = None
                self._update_tag(shot_tag)

    def _handle_shot_versions(self, shot_tag, shot):
        # Enumerate all shots subfolders
        # If a matching shotgun version is found, the version folder is tagged
        # If no matching shotgun version is found, all tags are cleared
        path = self._get_shot_path_info_by_tag(shot_tag)
        if path:
            for elem in self._get_folder_content(path.path):
                if elem.fileType == 'FOLDER':
                    version = self._find_shotgun_version_by_name(elem.name, shot['sg_versions'])
                    if version:
                        self.unique_tags_to_create.add('{0}/{1}'.format(self.SHOT_VERSION_CAT, elem.name))
                        self.tag_updates.append((os.path.join(path.path, elem.name), ['{0}/{1}'.format(self.SHOT_VERSION_CAT, elem.name)]))
                    else:
                        self.tag_updates.append((os.path.join(path.path, elem.name), []))

    def _create_new_tags(self):
        # Create all tags in CN
        for implied_tag in self.unique_tags_to_create:
            splitted_tag = implied_tag.split('/')
            self._get_or_create_category(splitted_tag[0])
            self._get_or_create_tag(splitted_tag[0], splitted_tag[1])

    def _commit_tags(self):
        # Commit all tags
        try:
            self.api.bulkSetTagsForFolder(updates=self.tag_updates)
        except:
            self.log.error(self._format_log(('Failed to bulk set tags', 'Attempting to set one by one')))
            for tag in self.tag_updates:
                try:
                    self.api.bulkSetTagsForFolder(updates=[tag])
                except:
                    self.log.error(self._format_log(('Failed to set tag', tag[0], tag[1])))

    def _commit_implied_tags(self):
        # Commit all implied tags
        try:
            self.api.bulkImpliedTagUpdate(tagsToAdd=self.implied_tag_updates, tagsToDelete=self.implied_tags_to_delete)
        except:
            self.log.error(self._format_log(('Failed to bulk update implied tags', 'Attempting to update one by one')))
            for implied_tag in self.implied_tag_updates:
                try:
                    self.api.bulkImpliedTagUpdate(tagsToAdd=[implied_tag])
                except:
                    self.log.error(self._format_log(('Failed to add implied tags', '-'.join(implied_tag[1]), 'parent {0}'.format(implied_tag[0]))))
            for implied_tag in self.implied_tags_to_delete:
                try:
                    self.api.bulkImpliedTagUpdate(tagsToAdd=[implied_tag])
                except:
                    self.log.error(self._format_log(('Failed to delete implied tags', '-'.join(implied_tag[1]), 'parent {0}'.format(implied_tag[0]))))

    def start(self):
        self.log.info(self._format_log(('Shotgun plugin', 'Starting execution')))
        shot_tags = self._retrieve_shot_tags()
        shots = self._retrieve_shotgun_shots()
        for shot_tag in shot_tags:
            match = self._find_shotgun_shot_by_unique_name(shot_tag.name, shots)
            if match is None:
                self.log.warning(('Unable to find matching shotgun shot for %s' % shot_tag.name, 'Skipping shot.'))
                continue
            self._handle_shot_status(shot_tag, match)
            self._handle_shot_versions(shot_tag, match)
        self._create_new_tags()
        self._commit_tags()
        self._commit_implied_tags()
        self.sg.close()
        self.log.info(self._format_log(('Shotgun plugin', 'Execution terminated')))

def main():
    #Get current path
    if len(sys.argv) == 1:
        scriptFilePath = os.path.dirname(sys.argv[0])
    else:
        #Error out - print to stderr - let cron know something went wrong too
        error_msg = "CnShotgun (cn_shotgun.py) takes no arguments. %s arguments were passed in.\nAborting script." % (len(sys.argv) - 1)
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    try:
        shotgun = ShotgunPlugin(scriptFilePath)
        shotgun.start()
    except Exception as e:
        machine_name = socket.gethostname()
        print("\n--------ERROR---------\n%s failed to complete while being executed on machine: %s\nScript aborted.\nResponse received: %s" % (NAME, machine_name, e.message) , file=sys.stderr)
        print("\n----FULL TRACEBACK----\n", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("\n", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
