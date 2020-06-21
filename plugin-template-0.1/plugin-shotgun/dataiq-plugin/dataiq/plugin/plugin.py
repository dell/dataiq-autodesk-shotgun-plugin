# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
"""
plugin.py - A wrapper for a Flask application specifically for DataIQ plugins.
"""

import os
import warnings
from abc import ABC, abstractmethod
from functools import wraps
from inspect import signature
from threading import Thread
from time import sleep
from typing import Optional, Union

import flask
import requests
from flask import Flask, Response
from requests import ConnectionError
from werkzeug.exceptions import NotFound

from dataiq.plugin.configuration import Configuration, \
    JsonConfigurationSerializer
from dataiq.plugin.context import Context
from dataiq.plugin.exceptions import PluginException
from dataiq.plugin.jobs import JobManager, JobStatusResponse, \
    JsonJobManagerSerializer
from dataiq.plugin.plugin_data import PluginData
from dataiq.plugin.util import Serializer

try:
    CLARITY_HOSTNAME = os.environ['CN_HOSTNAME']
except KeyError:
    warnings.warn('Environment variable CN_HOSTNAME was not set. Using default value.')
    CLARITY_HOSTNAME = 'claritynow'

STATIC_FOLDER = 'static_folder'
TEMPLATE_FOLDER = 'template_folder'


def _invalidate_task(plugin_data: PluginData) -> None:
    """Invalidate or register this plugin within ClarityNow."""
    url = 'http://' + CLARITY_HOSTNAME + '/plugins/' + plugin_data.short_name
    body = {
        'url': plugin_data.url,
        'longName': plugin_data.long_name,
        'image': plugin_data.image
    }
    response = None
    while response is None:
        print('Attempting to invalidate ClarityNow cache at: ' + url)
        try:
            r = requests.put(url, json=body)
        except ConnectionError:
            sleep(5)
            continue
        response = r
    if 204 != response.status_code:
        warnings.warn(
            f"PUT to invalidate cache did not return 204. ClarityNow may be "
            f"using an outdated configuration. Got a {response.status_code}: "
            f"{response.text}")
    print('Successfully Invalidated ClarityNow')


class Plugin(Flask, ABC):
    """Additional functionality that can be integrated into ClarityNow.

    :param import_name: See Flask.
    :param static_folder: Absolute path to look for Flask static resources.
    :param template_folder: Absolute path to look for Flask template resources.
    """

    def __init__(self, import_name: str, plugin_data: PluginData, *args, **kwargs):
        # Set default kwargs
        cwd = os.getcwd()
        if TEMPLATE_FOLDER not in kwargs:
            kwargs[TEMPLATE_FOLDER] = cwd + '/templates'
        if STATIC_FOLDER not in kwargs:
            kwargs[STATIC_FOLDER] = cwd + '/static'

        # Validate kwargs
        if not os.path.isabs(kwargs.get(TEMPLATE_FOLDER)):
            raise ValueError('template_folder must be an absolute path.')
        if not os.path.isabs(kwargs.get(STATIC_FOLDER)):
            raise ValueError('static_folder must be an absolute path.')
        super().__init__(import_name, *args, **kwargs)

        self.job_manager = JobManager()

        # Add default endpoints
        self.add_url_rule('/internal/configuration/', 'configuration',
                          self._handle_configuration)
        self.add_url_rule('/internal/settings/', 'settings', self._handle_settings)
        self.add_url_rule('/internal/jobs/', 'jobs', self._handle_jobs)
        self.add_url_rule('/internal/jobs/<job>', 'job',
                          self._handle_job, methods=["GET", "DELETE"])

        # Invalidate the ClarityNow view of this plugin.
        self._invalidate_thread: Optional[Thread] = None
        self._plugin_data: PluginData = plugin_data
        self._invalidate()

    def action(self,
               rule: str,
               serializer: Optional[Serializer] = None,
               **options):
        """Decorate a function to parse Context from HTTP request.

        Simply acts as a wrapper for the standard Flask App.route(...) that
        additionally parses the user's context out of the HTTP request body.

        Actions must support the POST method because they require information
        that is not available in the URL parameters. Additional methods such as
        GET and DELETE may be added if given in the 'methods' argument. If a
        'methods' argument is provided without POST included, the argument is
        ignored.

        :param rule: See Flask App.route
        :param serializer: If provided, passes the return value of the decorated
            method through the serializer. Otherwise does not modify the return
            value.
        :param options: See Flask App.route
        :return: The decorated function that passes a Context argument.
        """

        def decorator(f):
            if len(signature(f).parameters) != 1:
                raise TypeError(f"Function being decorated ({f.__name__}) must "
                                f"have 1 parameter, which will be passed a "
                                f"Context at runtime.")

            @wraps(f)
            def parse_context():
                try:
                    context = Context.from_request(flask.request) \
                        if flask.request.method == 'POST' else None
                    result = f(context)
                    if serializer is not None:
                        if isinstance(result, serializer.cls):
                            result = serializer.serialize(result)
                        else:
                            raise TypeError(f'Cannot serialize a {type(result)}, '
                                            f'was expecting a {serializer.cls}.')
                    return result
                except PluginException as e:
                    return Response(str(e), e.code)

            if 'methods' not in options or 'POST' not in options['methods']:
                options['methods'] = ['POST']
            endpoint_name = options.pop("endpoint", f.__name__)
            self.add_url_rule(rule, endpoint_name, parse_context, **options)
            return parse_context

        return decorator

    @abstractmethod
    def configuration(self) -> Configuration:
        """Return the Configuration object for the plugin."""
        pass

    def _handle_configuration(self) -> dict:
        """Handler for the /internal/configuration endpoint.

        Calls self.configuration() and validates the return type before returning
        control to Flask.
        """
        configuration = self.configuration()
        if not isinstance(configuration, Configuration):
            raise TypeError("configuration() must return a Configuration"
                            " instance. Got a " + type(configuration).__name__)
        return JsonConfigurationSerializer().serialize(configuration)

    def _handle_jobs(self) -> dict:
        """Handler for the /internal/jobs/ endpoint.

        Return all of the jobs that this plugin knows about.
        """
        return JsonJobManagerSerializer().serialize(self.job_manager)

    def _handle_job(self, job) -> Response:
        """Handler for the /internal/jobs/<id> endpoint.

        Methods:
            GET: Return status of job id.
            DELETE: Interrupt job id and return status.
        """
        try:
            job = int(job)
        except ValueError:
            return Response('Job argument must be an integer.', status=400)
        try:
            if flask.request.method == "GET":
                return self.job_manager.get_status(job)
            elif flask.request.method == "DELETE":
                status = self.job_manager.stop(job)
                if not isinstance(status, JobStatusResponse):
                    raise TypeError("job_stop must return a JobStatusResponse.")
                return status.json()
            else:
                return Response('/jobs/<job> endpoint only supports GET and '
                                'DELETE.', status=405)
        except KeyError:
            return Response(f'Job {job} not found.', status=404)

    def _invalidate(self):
        if self._invalidate_thread is None or not self._invalidate_thread.is_alive():
            self._invalidate_thread = Thread(
                target=_invalidate_task,
                name='invalidate-task',
                args=(self._plugin_data,)
            )
            self._invalidate_thread.start()

    def settings(self) -> Union[str, Response]:
        """Return the HTML used to modify this plugin's configuration.

        Is expecting HTML (str) to be returned if the plugin exposes a settings page,
        but will also accept a Flask Response object for fine-grained control.

        The default implementation returns a 404 indicating the plugin does not have a
        settings page, though if a user sees this page then the plugin configuration
        did not correctly indicate that it does not expose a settings page. See
        """
        raise NotFound(f"{self.name} does not have a settings page.")

    def _handle_settings(self):
        """Handler for the /internal/settings endpoint.

        Calls self.settings() and validates the return type before returning control to
        Flask.
        """
        html_response = self.settings()
        if not isinstance(html_response, (str, Response)):
            raise TypeError("settings must return html (str) or a Flask Response "
                            "object.")
        return html_response
