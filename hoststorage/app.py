"""
The DataIQ Shell Executor Example

Wraps desktop ClarityNow plugin scripts in a Flask-based environment.

Environment Variables:
    AUTH_OVERRIDE: If set, will override all authentication and use a root user whose
        username is the value of the variable. Use carefully.
    HOSTNAME: The hostname of the current machine. Used to tell ClarityNow how to route
        to this plugin. Defaults to localhost.
    PLUGIN_DEFAULT_YAML: The default plugin config YAML file to load if there is not an
        existing app.sqlite database present in the PLUGIN_WORKING_DIR. Defaults
        to '/hoststorage/ca.control'.
    PLUGIN_WORKING_DIR: The directory relative to which to the executor will operate.
        It will place the app.sqlite database as well as any additional config files
        here. Script executions can be performed relative to this directory. Defaults
        to the dirname of PLUGIN_DEFAULT_YAML.
    STATIC_FOLDER: The absolute path to the Flask static resources.
    TEMPLATE_FOLDER: The absolute path to the Flask template resources.

Notes:
    Do not attempt to use with any multi-process based WSGI container. The
    AsyncExecutor implementation makes assumptions about being able to access the same
    in-memory data structures across different requests.
"""
import logging
import os

from dataiq.plugin.user import HardcodedAdminUser
from dataiq.plugin.util import get_env_or_warn

from legacy.async_executor import AsyncExecutor

logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger('app')

AUTH_OVERRIDE = os.getenv('AUTH_OVERRIDE')
FULL_HOSTNAME = get_env_or_warn(
    'HOSTNAME', log, 'localhost')
PLUGIN_DEFAULT_YAML = get_env_or_warn(
    'PLUGIN_DEFAULT_YAML', log, '/hoststorage/ca.control')
PLUGIN_WORKING_DIR = get_env_or_warn(
    'PLUGIN_WORKING_DIR', log, os.path.dirname(PLUGIN_DEFAULT_YAML))
STATIC_FOLDER = get_env_or_warn(
    'STATIC_FOLDER', log, '/plugin/plugin-legacy/static/')
TEMPLATE_FOLDER = get_env_or_warn(
    'TEMPLATE_FOLDER', log, '/plugin/plugin-legacy/templates/')

try:
    # Hostname is assumed to be in the form of: "plugin-<name>-<pod_id>", though the DNS
    #  route to the plugin is only "plugin-<name>"
    HOSTNAME = '-'.join(FULL_HOSTNAME.split('-')[:-1])
except KeyError:
    HOSTNAME = FULL_HOSTNAME

override = None if AUTH_OVERRIDE is None else HardcodedAdminUser(AUTH_OVERRIDE)

app = AsyncExecutor(
    import_name='shotgun',
    hostname=HOSTNAME,
    default_config_file=PLUGIN_DEFAULT_YAML,
    working_dir=PLUGIN_WORKING_DIR,
    auth_override=override,
    static_folder=STATIC_FOLDER,
    template_folder=TEMPLATE_FOLDER
)


if __name__ == '__main__':
    app.run()
