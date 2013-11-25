"""
RFC3339 time stamp generation support.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 3, 2013.

This is a fork of Henry Prechneur's rfc3339 module, stripped of test code,
doc strings and comments and adapted for Python 3.x compatibility. It will
be removed once the original package is also compatible with Python 3.x.

# Copyright (c) 2009, 2010, Henry Precheur <henry@precheur.org>
"""
import datetime
import time

__docformat__ = 'reStructuredText en'
__all__ = ['rfc3339']


def _timezone(utc_offset):
    hours = abs(utc_offset) // 3600
    minutes = abs(utc_offset) % 3600 // 60
    return '%c%02d:%02d' % ('-' if utc_offset < 0 else '+', hours, minutes)

def _timedelta_to_seconds(timedelta):
    return (timedelta.days * 86400 + timedelta.seconds +
            timedelta.microseconds // 1000)

def _utc_offset(date, use_system_timezone):
    if isinstance(date, datetime.datetime) and date.tzinfo is not None:
        return _timedelta_to_seconds(date.dst() or date.utcoffset())
    elif use_system_timezone:
        if date.year < 1970:
            # We use 1972 because 1970 doesn't have a leap day (feb 29)
            t = time.mktime(date.replace(year=1972).timetuple())
        else:
            t = time.mktime(date.timetuple())
        if time.localtime(t).tm_isdst: # pragma: no cover
            return -time.altzone
        else:
            return -time.timezone
    else:
        return 0

def _string(d, timezone):
    return ('%04d-%02d-%02dT%02d:%02d:%02d%s' %
            (d.year, d.month, d.day, d.hour, d.minute, d.second, timezone))

def rfc3339(date, utc=False, use_system_timezone=True):
    try:
        if use_system_timezone:
            date = datetime.datetime.fromtimestamp(date)
        else:
            date = datetime.datetime.utcfromtimestamp(date)
    except TypeError:
        pass

    if not isinstance(date, datetime.date):
        raise TypeError('Expected timestamp or date object. Got %r.' %
                        type(date))

    if not isinstance(date, datetime.datetime):
        date = datetime.datetime(*date.timetuple()[:3])
    utc_offset = _utc_offset(date, use_system_timezone)
    if utc:
        return _string(date + datetime.timedelta(seconds=utc_offset), 'Z')
    else:
        return _string(date, _timezone(utc_offset))
