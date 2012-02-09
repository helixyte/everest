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
    count = start
    while True:
        send_value = (yield count)
        if not send_value is None:
            if send_value < count:
                raise ValueError('Values from ID generator must increase '
                                 'monotonically (current value: %d; value '
                                 'sent to generator: %d).'
                                 % (count, send_value))
            count = send_value
        else:
            count += 1


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


class BidirectionalLookup(object):
    """
    Bidirectional mapping between a left and a right collection of items.
    
    Each element of the left collection is mapped to exactly one element of
    the right collection; both collections contain unique elements.
    """

    def __init__(self, init_map=None, map_type=dict):
        """
        :param init_map: map-like object to initialize this instance with
        :param map_type: type to use for the left and right item maps
          (dictionary like)
        """
        self.__left = map_type()
        self.__right = map_type()
        if not init_map is None:
            for left, right in init_map.iteritems():
                self.__setitem__(left, right)

    def __setitem__(self, left_item, right_item):
        is_in_left = right_item in self.__left
        is_in_right = left_item in self.__right
        in_both = is_in_left and is_in_right
        if is_in_left or is_in_right and not in_both:
            raise ValueError('Cannot use the existing item "%s" from the %s '
                             'set as item in the %s set!' % is_in_right and
                             (left_item, 'right', 'left') or
                             (right_item, 'left', 'right'))
        self.__left[left_item] = right_item
        self.__right[right_item] = left_item

    def __delitem__(self, left_or_right_item):
        if left_or_right_item in self.__left:
            del self.__left[left_or_right_item]
        elif left_or_right_item in self.__right:
            del self.__right[left_or_right_item]
        else:
            raise KeyError("'%s'" % (left_or_right_item,))

    def __getitem__(self, left_or_right_item):
        if left_or_right_item in self.__left:
            return self.__left[left_or_right_item]
        elif left_or_right_item in self.__right:
            return self.__right[left_or_right_item]
        else:
            raise KeyError("'%s'" % (left_or_right_item,))

    def __contains__(self, left_or_right_item):
        return (left_or_right_item in self.__left) \
               or (left_or_right_item in self.__right)

    def has_left(self, item):
        return item in self.__left

    def has_right(self, item):
        return item in self.__right

    def get(self, left_or_right_item):
        try:
            item = self.__getitem__(left_or_right_item)
        except KeyError:
            item = None
        return item

    def get_left(self, left_item):
        return self.__left.get(left_item)

    def get_right(self, right_item):
        return self.__right.get(right_item)

    def pop_left(self, left_item, default=None):
        right_item = self.__left.pop(left_item, default)
        self.__right.pop(right_item, default)
        return right_item

    def pop_right(self, right_item, default=None):
        left_item = self.__left.pop(right_item, default)
        self.__left.pop(left_item, default)
        return left_item

    def left_keys(self):
        return self.__left.keys()

    def right_keys(self):
        return self.__right.keys()

    def left_values(self):
        return self.__left.values()

    def right_values(self):
        return self.__right.values()

    def left_items(self):
        return self.__left.items()

    def right_items(self):
        return self.__right.items()

    def clear(self):
        self.__left.clear()
        self.__right.clear()
