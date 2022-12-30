import datetime

import pytz


def now():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
