"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.
"""

from StringIO import StringIO
from sqlalchemy.util import OrderedDict as _SqlAlchemyOrderedDict
import re
import traceback

__docformat__ = 'reStructuredText en'
__all__ = ['BidirectionalLookup',
           'OrderedDict',
           'check_email',
           'classproperty',
           ]

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,4}$'

check_email = re.compile(EMAIL_REGEX).match


class classproperty(object):
    """
    Property descriptor for class objects.
    """

    def __init__(self, get):
        self.__get = get

    def __get__(self, instance, cls):
        return self.__get(cls)


def id_generator(start=0):
    """
    Generator for sequential numeric numbers.
    """
    while True:
        yield start
        start += 1


def get_traceback():
    """
    Fetches the last traceback from :var:`sys.exc_info` and returns it as a
    formatted string.

    :returns: formatted traceback (string)
    """
    buf = StringIO()
    traceback.print_exc(file=buf)
    return buf.getvalue()


# We just redefine this here - perhaps we want to have our own implementation
# later.
OrderedDict = _SqlAlchemyOrderedDict
