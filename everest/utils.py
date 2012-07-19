"""
General purpose utilities.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.
"""
from StringIO import StringIO
from everest.interfaces import IRepositoryManager
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from pyramid.threadlocal import get_current_registry
from weakref import ref
import re
import traceback

__docformat__ = 'reStructuredText en'
__all__ = ['BidirectionalLookup',
           'check_email',
           'classproperty',
           'get_filter_specification_visitor',
           'get_order_specification_visitor',
           'get_repository_manager',
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


def get_filter_specification_visitor(name):
    """
    Returns a the class registered as the filter specification 
    visitor utility under the given name (one of the 
    :const:`everest.querying.base.EXPRESSION_KINDS` constants).
    
    :returns: class implementing 
        :class:`everest.interfaces.IFilterSpecificationVisitor`
    """
    reg = get_current_registry()
    return reg.getUtility(IFilterSpecificationVisitor, name=name)


def get_order_specification_visitor(name):
    """
    Returns the class registered as the order specification 
    visitor utility under the given name (one of the 
    :const:`everest.querying.base.EXPRESSION_KINDS` constants).
    
    :returns: class implementing 
        :class:`everest.interfaces.IOrderSpecificationVisitor`
    """
    reg = get_current_registry()
    return reg.getUtility(IOrderSpecificationVisitor, name=name)


def get_repository_manager():
    """
    Registers the object registered as the repository manager utility.
    
    :returns: object implementing 
        :class:`everest.interfaces.IRepositoryManager`
    """
    reg = get_current_registry()
    return reg.getUtility(IRepositoryManager)


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
        is_right_in_left = right_item in self.__left
        is_left_in_right = left_item in self.__right
        in_both = is_right_in_left and is_left_in_right
        if is_right_in_left or is_left_in_right and not in_both:
            raise ValueError('Cannot use the existing item "%s" from the %s '
                             'set as item in the %s set!'
                             % ((left_item, 'right', 'left') if
                                is_left_in_right else
                                (right_item, 'left', 'right')))
        if left_item in self.__left:
            del self.__right[self.__left[left_item]]
        self.__left[left_item] = right_item
        if right_item in self.__right:
            del self.__left[self.__right[right_item]]
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


class WeakList(list):
    """
    List containing weakly referenced items.

    All objects stored in a weak list are only weakly referenced, but
    accessing an element returns a strong reference. If an object referenced
    by an element in a weak list dies, the corresponding weak reference is
    removed automatically.

    :note: only weakly referenceable objects can be stored
    """

    def __init__(self, sequence=None):
        list.__init__(self)
        if not sequence is None:
            self.extend(sequence)

    def __setitem__(self, index, value):
        list.__setitem__(self, index, self.__get_weakref(value))

    def __getitem__(self, index):
        return list.__getitem__(self, index)()

    def __setslice__(self, start, stop, sequence):
        list.__setslice__(self, start, stop,
                          [self.__get_weakref(el) for el in sequence])

    def __getslice__(self, start, stop):
        return [item() for item in list.__getslice__(self, start, stop) ]

    def __contains__(self, value):
        return list.__contains__(self, self.__get_weakref(value))

    def __add__(self, sequence):
        new_weak_list = WeakList(sequence)
        new_weak_list.extend(self)
        return new_weak_list

    def __iter__(self):
        return self.__iterator()

    def append(self, value):
        list.append(self, self.__get_weakref(value))

    def count(self, value):
        return list.count(self, self.__get_weakref(value))

    def index(self, value):
        return list.index(self, self.__get_weakref(value))

    def insert(self, position, value):
        list.insert(self, position, self.__get_weakref(value))

    def pop(self):
        item_weakref = list.pop(self)
        return item_weakref()

    def remove(self, value):
        self.__delitem__(self.index(value))

    def extend(self, sequence):
        list.extend(self, self.__sequence_to_weakref(sequence))

    def sort(self):
        list.sort(self, self.__cmp_items)

    def __get_weakref(self, value):
        return ref(value, self.__remove_by_weakref)

    def __remove_by_weakref(self, weakref):
        # Cleanup callback called on garbage collection.
        while True:
            try:
                self.__delitem__(list.index(self, weakref))
            except ValueError:
                break

    def __sequence_to_weakref(self, sequence):
        if not isinstance(sequence, WeakList):
            weakrefs = [self.__get_weakref(el) for el in sequence]
        else:
            weakrefs = sequence
        return weakrefs

    def __cmp_items(self, left_ref, right_ref):
        return cmp(left_ref(), right_ref())

    def __iterator(self):
        cnt = 0
        while cnt < len(self):
            yield self.__getitem__(cnt)
            cnt += 1
        else:
            raise StopIteration
