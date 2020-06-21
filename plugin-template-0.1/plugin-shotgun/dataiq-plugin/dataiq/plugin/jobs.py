# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
from enum import Enum, auto
from functools import wraps
from typing import Dict, Any, Iterable

from dataiq.plugin.util import Serializer


def wrap_job(plugin):
    """Wrap every call to the decorated endpoint with a Job."""
    def decorator(f):
        @wraps(f)
        def make_job(*args, **kwargs):
            handle = plugin.job_manager.register()
            ret = None
            try:
                ret = f(handle, *args, **kwargs)
            except Exception as e:
                plugin.job_manager.error(
                    handle, type(e).__name__ + ': ' + str(e))
            else:
                plugin.job_manager.complete(handle)
            return ret
        return make_job
    return decorator


class Job:
    """A long-running task that can be inspected."""
    def __init__(self, handle):
        self.handle = handle
        self.status = Status.UNKNOWN
        self.message = ''

    def __repr__(self):
        return f'Job({self.handle}, {self.status}, {repr(self.message)})'


class JsonJobSerializer(Serializer[Job]):
    def __init__(self):
        super().__init__(Job)

    def serialize(self, job: Job):
        return {"identifier": job.handle,
                "status": job.status.name,
                "message": job.message}


class JobManager:
    _IDENTIFIER = 0

    def __init__(self):
        # TODO Investigate if this needs to be persisted for multiple processes
        #  with simultaneous connections. Or if persisting stopped jobs for
        #  (example) 24 hrs is desired.
        self._jobs = set()

    def __contains__(self, handle):
        try:
            self._get(handle)
            return True
        except KeyError:
            return False

    def __iter__(self) -> Iterable[Job]:
        return iter(self._jobs)

    def _get(self, handle):
        for job in self._jobs:
            if job.handle == handle:
                return job
        raise KeyError("Job {} not found.".format(handle))

    def get_status(self, handle) -> Dict[str, Any]:
        job = self._get(handle)
        return JsonJobSerializer().serialize(job)

    def complete(self, handle):
        """Mark a job as gracefully completed."""
        # self._get(handle).status = Status.COMPLETE
        self._jobs.remove(self._get(handle))

    def error(self, handle, message):
        """Mark a job as having errored out with a message."""
        job = self._get(handle)
        job.status = Status.ERROR
        job.message = message

    def msg(self, handle, message):
        self._get(handle).message = message

    def register(self):
        """Return a handle to a newly registered Job"""
        ident = JobManager._IDENTIFIER
        JobManager._IDENTIFIER += 1
        job = Job(ident)
        job.status = Status.RUNNING
        self._jobs.add(job)
        return ident

    # noinspection PyUnusedLocal
    def stop(self, job):
        """Interrupt the running job and return JobStatusResponse."""
        return JobStatusResponse(
            Status.ERROR, f'{self} does not support stopping jobs.')


class JsonJobManagerSerializer(Serializer[JobManager]):
    def __init__(self):
        super().__init__(JobManager)

    def serialize(self, job_manager: JobManager):
        job_ser = JsonJobSerializer()
        return {'jobs': [job_ser.serialize(job) for job in job_manager]}


class Status(Enum):
    UNKNOWN = auto()
    RUNNING = auto()
    COMPLETE = auto()
    STOPPED = auto()
    ERROR = auto()


class JobStatusResponse:
    def __init__(self, status, message):
        if not isinstance(status, Status):
            raise TypeError("status must be a jobs.Status.")
        self.status = status
        self.message = message

    def json(self) -> Dict[str, Any]:
        return {"status": self.status.name, "message": str(self.message)}
