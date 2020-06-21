# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
import datetime
import hashlib
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import time
import traceback
from subprocess import Popen
from threading import Thread, Lock
from typing import MutableMapping, Iterable, Optional, Dict

from dataiq.plugin.configuration import Configuration, JsonConfigurationSerializer
from dataiq.plugin.context import Context
from dataiq.plugin.plugin import Plugin
from dataiq.plugin.plugin_data import PluginData
from flask import request, render_template, Response

import config_parser
import cron
import html_redirector
from execution import PluginExecution
from legacy_action import LegacyAction

CONTAINERNAME = socket.gethostname()
HOSTNAME = '-'.join(CONTAINERNAME.split('-')[:-2]) 
print("HOSTNAME = %s" % HOSTNAME, file=sys.stderr)
REDIRECTOR = html_redirector.SubmitRedirector(hostname='/')

RUNNING: MutableMapping[str, Popen] = {}
CRONRUNNING = {}
EXECUTIONS: Dict[int, PluginExecution] = {}
RESPONSES = {}
PLUGNAME = ''
HOSTSTORAGE = '/hoststorage/'
CONFIG_FOLD = '%s.configs/' % HOSTSTORAGE
SHIPPED_CONFIG_FILE = '/plugin/ca.control'
SAVED_CONFIG_FILE = '%sca.control' % CONFIG_FOLD
PREV_CONFIG_FOLD = '%sprevious/' % CONFIG_FOLD
SEEN_CONFIGS_FILE = '%sconfig_history' % PREV_CONFIG_FOLD
STATUS_FOLD = '%sstatus/' % HOSTSTORAGE
STATUS_FILE = '%smode' % STATUS_FOLD
ENABLED = False
CLOSE_WINDOW = '<html><script type="text/javascript">window.close()</script></html>'

TO_USER = 0
TO_PLUGIN = 1
TIME_BUFFER = 20
#TIME_BUFFER = 100
TO_BE_REMOVED = {}
TESTING = False
PRINT_CAPTURER = None
MSG_DIVERTER = None
MOCKERY_ID = 0


class LegacyConfiguration(Configuration):
    def __init__(self, config_file):
        self.parser = config_parser.ConfigParser(config_file=config_file)
        self.name = self.parser.plugin_name
        self.crons = self.parser.crons
        if self.crons == {}:
            self.crons = None
        super(LegacyConfiguration, self).__init__(
            groups=[],
            actions=self.parser.actions(),
            has_visible_settings=True)


def subproc_monitor():
    while True:
        time.sleep(.5)
        deads = []
        try:
            reset_time = time.time()
            ctr = 0
            for job_id, process in RUNNING.items():
                ctr += 1
                duration = time.time() - reset_time
                if duration > 0.25:
                    time.sleep(0.25)
                    reset_time = time.time()
                    ctr = 0
                running = False
                try:
                    running = process.poll()
                except:
                    app.logger.error(f"Could not tell whether job {job_id} is "
                                     "still running" % job_id)
                if running != None:
                    deads.append(job_id)
        except:
            # Size of dict changed during loop
            # Just try again whenever you can
            pass
        for job_id in deads:
            try:
                del RUNNING[job_id]
            except:

                app.logger.error(
                    f"Could not delete Job {job_id} from RUNNING dictionary")
            TO_BE_REMOVED[job_id] = time.time() + TIME_BUFFER
        tbr_deads = []
        for job_id in TO_BE_REMOVED:
            if TO_BE_REMOVED[job_id] <= time.time():
                try:
                    EXECUTIONS[job_id].cleanup()
                    del EXECUTIONS[job_id]
                    del RESPONSES[job_id]
                except KeyError:
                    # This is ok. Means another function deleted it.
                    pass
                except:
                    # Should be ok. Means another function deleted the entry in RESPONSES.
                    app.logger.error(
                        f"Could not delete Job {job_id} from RESPONSES dictionary")
                tbr_deads.append(job_id)
        for job_id in tbr_deads:
            try:
                del TO_BE_REMOVED[job_id]
            except:
                # Probably ok. Will try to remove again if it's still in TO_BE_REMOVED
                pass


class LegacyPlugin(Plugin):
    """The implementation of the custom Plugin."""
    def __init__(self, config_file, *args, **kwargs):
        self.image_name = 'plugin-shotgun:0.1'
        self.url = 'http://' + HOSTNAME + ':5000' 
        self._config_file: str = config_file
        """The configuration file that this plugin is currently using.
        
        Do not modify internally, or must use settings_lock from the handlers below.
        """
        super(LegacyPlugin, self).__init__('LegacyPlugin',
                                           PluginData(self.url, self.short_name,
                                                      self.plugin_name,
                                                      self.image_name),
                                           *args, **kwargs)
        self.cron_thread = None
        self.monitorThread = Thread(target=subproc_monitor, args=[])
        self.monitorThread.start()

    def start_cron_thread(self):
        self.cron_thread = Thread(target=cron.main,
                             args=[self.plugin_name, self._config_file])
        self.cron_thread.start()

    @property
    def actions(self) -> Iterable[LegacyAction]:
        return self.configuration().actions

    @property
    def config_file(self):
        return self._config_file

    @config_file.setter
    def config_file(self, new_file):
        # TODO Clean this up, but make a quick and dirty check that the file will work
        JsonConfigurationSerializer().serialize(LegacyConfiguration(new_file))

        self._config_file = new_file
        self._invalidate()

    def configuration(self) -> LegacyConfiguration:
        return LegacyConfiguration(self._config_file)

    @property
    def has_crons(self):
        return self.configuration().crons is not None

    @property
    def plugin_name(self):
        return self.configuration().name

    @property
    def short_name(self):
        return self.plugin_name.lower().replace(' ', '')

    def settings(self):
        return render_template("settings.html")

    def execute(self, name: str, context: Context):
        # Example for plugin-previewer
        #curl -X POST http://plugin-previewer:5000/execute/ -H "Content-Type: application/json"  --data '{"name": "Preview", "context": {"p": "/mnt/vol1/SoulModes27.jpg", "guitoken": "100", "seq": "None"}}'

        cai = name
        if not cai:
            err_str = "Execution request to %s did not specify the Custom " \
                      "Action to execute" % self.plugin_name
            app.logger.error(err_str)
            return err_str
        act: Optional[LegacyAction] = None
        for a in self.actions:
            if a.name == cai:
                act = a
        if act is None:
            err_str = f"No action with name of '{cai}' is in " \
                      f"{app.plugin_name}'s configuration"
            app.logger.error(err_str)
            return err_str
        else:
            job_id = self.new_job_id(context)
            execution = PluginExecution(act, context, job_id, False)
            cmd = shlex.split(execution.shell_command)

            EXECUTIONS[job_id] = execution
            RESPONSES[job_id] = ['noresult', 'noresult']
            RUNNING[job_id] = subprocess.Popen(cmd)
            retval = 'noresult'
            deads = []
            while True:
                running = False
                try:
                    running = RUNNING[job_id].poll()
                except:
                    return CLOSE_WINDOW
                if running is not None:
                    deads.append(job_id)
                try:
                    if RESPONSES[job_id][TO_USER] != 'noresult':
                        retval = RESPONSES[job_id][TO_USER]
                except:
                    TO_BE_REMOVED[job_id] = time.time() + TIME_BUFFER
                    return CLOSE_WINDOW
                if retval != 'noresult':
                    RESPONSES[job_id][TO_USER] = 'noresult'
                    break
            for d in deads:
                try:
                    RUNNING[job_id].terminate()
                except:
                    app.logger.error("Could not terminate job %s. "
                                     "Probably already dead." % job_id)
                try:
                    del RUNNING[job_id]
                except:
                    app.logger.error("Could not delete job %s from RUNNING "
                                     "dictionary" % job_id)
                if job_id not in TO_BE_REMOVED:
                    TO_BE_REMOVED[job_id] = time.time() + TIME_BUFFER
            
            if isinstance(retval, str) and retval != 'noresult':
                retval = REDIRECTOR.redirect_submits(retval, job_id) 
            return retval

    def new_job_id(self, req) -> str:
        global MOCKERY_ID
        MOCKERY_ID += 1
        return str(MOCKERY_ID)


def get_is_test():
    # Use a Mock patch to have this return True if needed
    return os.getenv('DEBUG', '') == 'true'


def make_dir(name):
    dirpath = '%s%s' % (HOSTSTORAGE, name)
    dir_exists = False
    if not os.path.isdir(dirpath):
        try:
            os.makedirs(dirpath)
        except OSError as e:
            print("Can't create '%s' directory on host: %s" 
                  % (name, dirpath), file=sys.stderr)
            raise
    else:
        dir_exists = True
    return dir_exists


def save_enabled_state(state):
    global ENABLED
    if state == 'enabled':
        ENABLED = True
    elif state == 'disabled':
        ENABLED = False
    try:
        status_file = open(STATUS_FILE, 'w+')
        status_file.write(state)
        status_file.close()
    except OSError as e:
        ENABLED = False
        print("Could not save the enabled/disabled state for plugin '%s'. "
              "Plugin is now disabled" % PLUGNAME, file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
    if ENABLED:
        state = 'enabled'
    else:
        state = 'disabled'
    return state


def get_enabled_state():
    status_line = ''
    enabled_state = False
    try:
        status_file = open(STATUS_FILE, 'r')
        status_line = status_file.readline().strip()
        status_file.close()
    except OSError as e:
        print("Could not read the enabled/disabled state of plugin '%s'. "
              "Plugin is now disabled" % PLUGNAME, file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
    if status_line == 'enabled':
        print("Plugin '%s' is enabled" % PLUGNAME, file=sys.stderr)
        enabled_state = True
    elif status_line == 'disabled':
        print("Plugin '%s' is disabled" % PLUGNAME, file=sys.stderr)
    elif status_line != '': 
        print("Could not understand enabled/disabled state for plugin '%s': %s"
              % (PLUGNAME, status_line), file=sys.stderr)
    return enabled_state


def create_host_structures():
    config_existed = make_dir('.configs')
    prev_existed = make_dir('.configs/previous')
    outputs_existed = make_dir('outputs')
    status_existed = make_dir('status')
    return status_existed


def md5(path):
    # Returns an md5 checksum hash for a specific path
    def get_file_md5(file_path):
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hash_md5.update(chunk)
        hash_val = hash_md5.hexdigest()
        return hash_val
    return get_file_md5(path)


def datetime_now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def config_history(md5_str, isdefault=False):
    # TODO - (Probably not here) - check some file we ship with that maps releases to
    #   default config md5's, put these in the file (per unique md5)
    # If history config file is not present, assume that this is 
    # the first install 
    if not os.path.isfile(SEEN_CONFIGS_FILE):
        print("Apparent first install of plugin '%s'. Adding default "
              "configuration file (ca.control) to configuration history."
              % PLUGNAME, file=sys.stderr)
        if os.path.isfile(SAVED_CONFIG_FILE):
            print("Configuration history file for plugin '%s' does not exist, "
                  "but there seems to already be a plugin configuration file "
                  "for it on the host machine. This should never happen. "
                  "Please do not delete or modify the configuration history "
                  "file outside DataIQ's User Interface (%s)" 
                  % (PLUGNAME, SEEN_CONFIGS_FILE), file=sys.stderr) 
            print("Please stop plugin '%s's pod with:\n\t1. kubectl delete -n "
                  "dataiq service plugin-<specific name>\n\t2. kubectl delete "
                  "-n dataiq deployment plugin-<specific name>\nRename %s to "
                  "%s.bak\nTo finish, restart the pod with:\n\tkubectl create "
                  "-f <path to plugin's YAML file>" 
                  % (PLUGNAME, SAVED_CONFIG_FILE, SAVED_CONFIG_FILE), 
                  file=sys.stderr) 
            save_enabled_state('disabled')
            return False, 'N/A'
        elif isdefault:
            try:
                shutil.copyfile(SHIPPED_CONFIG_FILE, SAVED_CONFIG_FILE)
            except OSError as e:
                print("Could not copy the default configuration file to %s. "
                      "Cannot proceed. Disabling plugin '%s'." 
                      % (SAVED_CONFIG_FILE, PLUGNAME), file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                save_enabled_state('disabled')
                return False, 'N/A'
            return write_new_seen_config(md5_str, True), 'default'
    found = False
    found_type = 'N/A'
    prev_file = '.N/A'
    prev_default = '.N/A'
    seenfile = open(SEEN_CONFIGS_FILE, 'r')
    for line in seenfile:
        line = line.strip()
        splitter = line.split(' ')
        old_md5 = splitter[0]
        datetimed_config_file = splitter[1]
        kind = splitter[2]
        if old_md5 == md5_str:
           if isdefault and kind == 'default':
               print("Plugin '%s' is using the default and unedited "
                     "configuration" % PLUGNAME, file=sys.stderr)
               return True, 'default'
           found = True
           cfg_date = datetimed_config_file.split('.')[-1]
           print("Plugin '%s' is using an edited configuration file which was "
                 "submitted on %s" % (PLUGNAME, cfg_date), file=sys.stderr)
        prev_file = datetimed_config_file
        if kind == 'default':
            prev_default = prev_file
        if found:
            found_type = kind
            break
    seenfile.close()
    prev_date = prev_file.split('.')[-1]
    prev_default_date = prev_default.split('.')[-1]
    print("Plugin '%s's previous configuration was submitted on %s and the "
          "previous default configuration was recorded on %s" 
          % (PLUGNAME, prev_date, prev_default_date), file=sys.stderr)
    return found, found_type


def force_shipped_config(md5_str): 
    try:
        os.remove(SAVED_CONFIG_FILE)
    except:
        # Don't care if it exists - we're forcing the shipped to become the new config
        pass
    try:
        shutil.copyfile(SHIPPED_CONFIG_FILE, SAVED_CONFIG_FILE)
    except OSError as e:
        print("Could not copy the default configuration file to %s. "
              "Cannot proceed. Disabling plugin '%s'." 
              % (SAVED_CONFIG_FILE, PLUGNAME), file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        save_enabled_state('disabled')
        return False
    return write_new_seen_config(md5_str, True)


def write_new_seen_config(md5_str, isdefault=False):
    # Requires that the new config exists at /hoststorage/.configs/ca.control
    datetime_path = "%sca.control.%s" % (PREV_CONFIG_FOLD, datetime_now_str())
    try:
        shutil.copyfile(SAVED_CONFIG_FILE, datetime_path)
    except OSError as e:
        print("Could not back up the configuration file to %s for "
              "plugin '%s'." % (PREV_CONFIG_FOLD, PLUGNAME), 
              file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        save_enabled_state('disabled')
        return False
    kind = 'default'
    if not isdefault:
        kind = 'custom'
    try:
        hist = open(SEEN_CONFIGS_FILE, 'a+') 
        hist.write("%s %s %s\n" % (md5_str, datetime_path, kind))
        hist.close()
    except OSError as e:
        print("Could not write to configuration history file to "
              "record current configuration for plugin '%s': %s"
              % (PLUGNAME, SEEN_CONFIGS_FILE), file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        save_enabled_state('disabled')
        return False
    return True


def setup_config():
    local_path = SHIPPED_CONFIG_FILE
    host_config_path = SAVED_CONFIG_FILE
    exists = False
    isdifferent = False
    existing_md5 = ''
    local_md5 = md5(local_path)
    local_inhistory, local_kind = config_history(local_md5, True)

    if os.path.isfile(host_config_path):
        exists = True      
        existing_md5 = md5(host_config_path)
        # TODO - compare and look up history of local_md5 when this md5 was first seen,
        #  report to user whether it is old, newest, or whether it has never been seen
        #  before
        if existing_md5 != local_md5:
            print("Host's configuration file for plugin '%s' is different "
                  "than the default configuration file" % PLUGNAME, 
                  file=sys.stderr)
            known_in_hist, existing_kind = config_history(existing_md5, False)
            if not known_in_hist:
                print("The existing configuration file for '%s' was edited "
                      "without the plugin's knowledge. Automatically "
                      "disabling plugin." % PLUGNAME, file=sys.stderr)
                save_enabled_state('disabled')
            elif existing_kind == 'default':
                # Overwrite with new, shipped-with config 
                updated = force_shipped_config(local_md5)
                print("Host's configuration file for plugin '%s' has been "
                      "updated with the new default configuration" % PLUGNAME, 
                      file=sys.stderr)
            else:
                print("Host's customized configuration file for plugin '%s' "
                      "will continue to be used" % PLUGNAME, file=sys.stderr)
    return host_config_path


# Instantiating Plugin Flask server
is_test = get_is_test()
project_root = os.getcwd()
current_config = SHIPPED_CONFIG_FILE
if not is_test:
    proceed = True
    if os.path.isfile(current_config):
        PLUGNAME = LegacyConfiguration(current_config).name
    else:
        print("Local configuration file (ca.control) is missing for plugin "
              "pod with hostname/IP: '%s'. Cannot proceed" % HOSTNAME, 
              file=sys.stderr) 
        save_enabled_state('disabled')
        proceed = False
    already_existed = create_host_structures()
    if proceed:
        if already_existed:
            ENABLED = get_enabled_state()
        else: 
            save_enabled_state('disabled')
        current_config = setup_config()

app = LegacyPlugin(current_config, 
                   template_folder=project_root + '/templates',
                   static_folder=project_root + '/static')
if app.has_crons and ENABLED:
    app.start_cron_thread()

# Setting up various routes.


@app.action('/execute/', methods=['GET', 'POST'])
def execute(context: Context):
    if not ENABLED:
        return json.dumps({'ack': 'disabled'})
    name = request.json['name'] if request.json is not None else None
    execute = app.execute(name, context)
    return execute


@app.route('/returnthis/', methods=['POST'])
def return_this():
    if not ENABLED:
        return json.dumps({'ack': 'disabled'})
    request_json = request.json
    job_id = str(request_json['job_id'])
    retval = request_json['retval']
    if job_id:
        # GUITOKEN IS JOB ID - PLACE HTML IN RUNNING DICT 
        try:
            RESPONSES[job_id][TO_USER] = retval
        except KeyError:
            plugname = app.plugin_name
            app.logger.error("No Plugin interaction in '%s' exists with job id '%s'"
                 % (plugname, job_id))
            return CLOSE_WINDOW 
    return json.dumps({'ack': 'ok'})


@app.route('/getuserresponse/', methods=['POST'])
def get_user_response():
    if not ENABLED:
        return json.dumps({'ack': 'disabled'})
    request_json = request.json
    job_id = str(request_json['job_id'])
    resp = 'noresult'
    if job_id in RESPONSES:
        try:
            while job_id in RESPONSES and resp == 'noresult':
                entry = RESPONSES.get(job_id)
                resp = entry[TO_PLUGIN]
        except:
            if job_id not in RUNNING:
                app.logger.error("/getuserresponse returning 'terminated', as "
                     "job '%s' was not in the list of running jobs" % job_id)
                return CLOSE_WINDOW
        if job_id not in RESPONSES or job_id not in RUNNING:

            # It was deleted by a termination request
            return CLOSE_WINDOW
        try:
            RESPONSES[job_id][TO_PLUGIN] = 'noresult'
        except KeyError:
            # This is ok. Means another function deleted it.
            pass
        except:
            plugname = app.plugin_name
            app.logger.error("Call to %s's /getuserresponse could not reset "
                             "'%s' entry in RESPONSES communication dictionary"
                             % (plugname, job_id))
            pass
    else:
        plugname = app.plugin_name
        app.logger.error("No Plugin interaction in '%s' exists with job_id "
                         "'%s'" % (plugname, job_id))
        return CLOSE_WINDOW
    return json.dumps(resp) 


@app.route('/interact/', methods=['POST'])
def interact():
    if not ENABLED:
        return json.dumps({'ack': 'disabled'})
    form = request.form
    job_id = form.get('job_id')
    action = 'submit_action'
    selections = {}
    for s in form.keys():
        if s == 'result':
            selections[s] = [form.get(s)]
        elif s != 'job_id':
            selections[s] = form.get(s)
    reply_to_user = form.get('reply_to_user', True)
    retval = {'action': action, 'selections': selections}
    if job_id in RESPONSES and job_id in RUNNING:
        try:
            RESPONSES[job_id][TO_PLUGIN] = retval 
            RESPONSES[job_id][TO_USER] = 'noresult' 
        except KeyError:
            # This is probably ok. Execution was terminated.
            retval = CLOSE_WINDOW
            return retval 
    else:
        app.logger.error("Custom Action '%s' interact endpoint received "
                         "interaction request with invalid job_id: '%s'" 
                         % (action, job_id))
        return CLOSE_WINDOW
    retval = json.dumps({'ack': 'ok'})
    while reply_to_user and job_id in RUNNING:
        time.sleep(.01)
        contents = 'noresult'
        try:
            contents = RESPONSES[job_id][TO_USER]
        except KeyError:
            retval = CLOSE_WINDOW
            break
        if contents != 'noresult' and isinstance(contents, str):
            retval = REDIRECTOR.redirect_submits(contents, job_id)
            RESPONSES[job_id][TO_USER] = 'noresult'
            break
    if job_id not in RUNNING:
        return CLOSE_WINDOW
    return retval


@app.route('/terminationrequests/', methods=['GET', 'POST'])
def terminationrequests():
    if not ENABLED:
        return json.dumps({'ack': 'disabled'})
    job_ids = []
    for jid in CRONRUNNING:
        if CRONRUNNING[jid] == 'terminate':
            job_ids.append(jid)
    retdict = {'job_ids': job_ids}
    return json.dumps(retdict)


@app.route('/registercronjob/', methods=['POST'])
def register_cron_job():
    if not ENABLED:
        return json.dumps({'ack': 'disabled'})
    job_id = str(request.json['job_id'])
    if job_id not in CRONRUNNING:
        CRONRUNNING[job_id] = 'running'
    else:
        app.logger.error("Job '%s' is already in the list of running "
                         "cron jobs" % job_id)
        return json.dumps({'ack': 'error'})
    return json.dumps({'ack': 'ok'})


@app.route('/registercrontermination/', methods=['POST'])
def register_cron_termination():
    if not ENABLED:
        return json.dumps({'ack': 'disabled'})
    retdump = json.dumps({'ack': 'ok'})
    job_id = str(request.json['job_id'])
    if job_id in CRONRUNNING:
        try:
            del CRONRUNNING[job_id]
        except:
            app.logger.error("Could not delete job with id '%s' from the "
                             "list of running cron jobs" % job_id)
    else:
        app.logger.error("Job id '%s' is not in the list of running "
                         "cron jobs" % job_id)
        retdump = json.dumps({'ack': 'error'})
    return retdump


settings_lock = Lock()
"""Lock for getting and updating the settings file."""


@app.route('/internal/settings/file', methods=['GET'])
def get_file():
    with settings_lock, open(app.config_file, 'r') as fp:
        contents = fp.read()
    etag = hashlib.md5(contents.encode('utf-8')).hexdigest()
    return Response(status=200,
                    headers={'ETag': etag,
                             'Content-Type': 'text/plain; charset=utf-8'},
                    response=contents)


@app.route('/internal/settings/file', methods=['PUT'])
def put_file():
    with settings_lock:
        if_match = request.headers['If-Match']
        with open(app.config_file, 'rb') as old_file:
            contents = old_file.read()
            etag = hashlib.md5(contents).hexdigest()
            if if_match != etag:
                return Response(
                    status=412,
                    response='This document has been updated elsewhere. '
                             'Please save your changes externally and try '
                             'again.')
        new_file = app.config_file
        with open(new_file, 'wb') as fp:
            fp.write(request.data)
            fp.truncate()
        new_md5 = md5(new_file) 
        write_new_seen_config(new_md5)
        app.config_file = new_file
        has_crons = app.configuration().crons is not None
        if has_crons and ENABLED == True:
            if app.cron_thread == None:
                app.start_cron_thread()
        return Response(status=204)


@app.route('/terminate/', methods=['POST'])
def terminate():
    if not ENABLED:
        return json.dumps({'ack': 'disabled'})
    job_id = request.data.decode('utf-8')
    if job_id in RUNNING:
        try:
            running = RUNNING[job_id].poll()
        except:
            running = None
            app.logger.error("Could not get status for job with id "
                             "'%s'" % job_id)
        if running is None:
            try:
                RUNNING[job_id].terminate()
            except:
                # TODO - print something here
                pass
        else:
            app.logger.error("Termination request received but job with id "
                             "'%s' had already terminated " % job_id)
            return CLOSE_WINDOW
    else:
        if job_id in CRONRUNNING:
            app.logger.info("Request received to terminate cron job "
                            "'%s'" % job_id)
            CRONRUNNING[job_id] = 'terminate'
            return json.dumps({'ack': 'termination request sent'})
        else:
            app.logger.error("Termination request received but no running "
                             "execution with job id '%s' could be found" 
                             % job_id)
            return json.dumps({'ack': 'not found'})
    try:
        app.logger.debug("Deleting job '%s' from list of running "
                         "jobs" % job_id)
        del RUNNING[job_id]
    except:
        return CLOSE_WINDOW
    if job_id not in TO_BE_REMOVED:
        TO_BE_REMOVED[job_id] = time.time() + TIME_BUFFER
    return CLOSE_WINDOW

@app.route('/internal/status/', methods=['GET', 'PUT'])
def status():
    if request.method == 'GET':
        return 'enabled' if get_enabled_state() else 'disabled'
    if request.method == 'PUT':
        state = save_enabled_state(request.data.decode("utf-8"))
        if state == 'enabled':
            has_crons = app.configuration().crons is not None
            if has_crons and ENABLED == True:
                if app.cron_thread == None:
                    app.start_cron_thread()
        else:
            for job_id in CRONRUNNING:
                CRONRUNNING[job_id] = 'terminate'
        return Response(status=204)
