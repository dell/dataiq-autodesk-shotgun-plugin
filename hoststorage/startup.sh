# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.

set -x -e

# This script is mounted into its respective legacy plugin container and is
# executed as the default CMD. It sets up the plugin executor environment and
# installs runtime dependencies.


# These variables explicitly set the container to expect and use UTF-8
# encodings in all file systems. Undefined Behavior may occur if the
# executor is expected to handle text that is not UTF-8.
export LANG=en_US.utf-8
export LC_ALL=en_US.utf-8
export PYTHONUNBUFFERED=1

# Hostname and port to access ClarityNow from within DataIQ.
export CN_HOSTNAME=claritynow:30080


# The dataiq-plugin library will operate relative to the PLUGIN_WORKING_DIR,
# placing app files under this directory. To persist across reboots, it is
# recommended that this point to a mounted volume.
export PLUGIN_WORKING_DIR=/hoststorage/


# In situations similar to a first-load scenario, the executor will detect that
# there are no user-saved config files. By default, the executor will refer to
# this file. This file will not be modified by the executor, and can be used as
# a template for the specific of each plugin.
export PLUGIN_DEFAULT_YAML=/hoststorage/ca.control


# Uncomment the following line to override all authentication and authorization
# checks in the Flask application. All requests will be authorized as if they
# were a root user with the given username. USE WITH CAUTION.
#export AUTH_OVERRIDE=root_override

# Set plugin to DataIQ
export SHOTGUN_PLUGIN_MODE=dataiq

# Install the Python 3 dependencies for the plugin code, located in /plugin/deps
python3.8 -m pip install /plugin/deps/* --no-index
python3.8 -m pip install /plugin/dataiq-plugin /plugin/plugin-legacy --no-index

pip install /hoststorage/deps2/* --no-index

# Begin executing the flask server.
cd /hoststorage/
export FLASK_APP=/hoststorage/app.py
flask run --host=0.0.0.0 --port=5000
