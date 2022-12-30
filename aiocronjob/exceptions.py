class JobAlreadyRunningException(Exception):
    def __str__(self):
        return "Job already running"


class JobNotFoundException(Exception):
    def __str__(self):
        return "Job not found"


class JobNotRunningException(Exception):
    def __str__(self):
        return "Job not running"
