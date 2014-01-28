"""
General purpose utilities.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.
"""
from collections import MutableSet
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.repositories.interfaces import IRepositoryManager
from functools import update_wrapper
from pyramid.compat import NativeIO
from pyramid.compat import iteritems_
from pyramid.threadlocal import get_current_registry
from weakref import WeakKeyDictionary
from weakref import ref
import re
import traceback
from logging import Formatter
import functools

__docformat__ = 'reStructuredText en'
__all__ = ['BidirectionalLookup',
           'EMAIL_REGEX',
           'WeakList',
           'WeakOrderedSet',
           'check_email',
           'classproperty',
           'generative',
           'get_filter_specification_visitor',
           'get_nested_attribute',
           'get_order_specification_visitor',
           'get_repository_manager',
           'get_traceback',
           'id_generator',
           'resolve_nested_attribute',
           'set_nested_attribute',
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


def resolve_nested_attribute(obj, attribute):
    #: Helper function for dotted attribute resolution.
    tokens = attribute.split('.')
    for token in tokens[:-1]:
        obj = getattr(obj, token)
        if obj is None:
            break
    return (obj, tokens[-1])


def get_nested_attribute(obj, attribute):
    """
    Returns the value of the given (possibly dotted) attribute for the given
    object.

    If any of the parents on the nested attribute's name path are `None`, the
    value of the nested attribute is also assumed as `None`.

    :raises AttributeError: If any attribute access along the attribute path
      fails with an `AttributeError`.
    """
    parent, attr = resolve_nested_attribute(obj, attribute)
    if not parent is None:
        attr_value = getattr(parent, attr)
    else:
        attr_value = None
    return attr_value


def set_nested_attribute(obj, attribute, value):
    """
    Sets the value of the given (possibly dotted) attribute for the given
    object to the given value.

    :raises AttributeError: If any of the parents on the nested attribute's
      name path are `None`.
    """
    parent, attr = resolve_nested_attribute(obj, attribute)
    if parent is None:
        raise AttributeError('Can not set attribute "%s" on None value.'
                             % attr)
    setattr(parent, attr, value)


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
    buf = NativeIO()
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


def get_repository(name=None):
    """
    Returns the repository with the given name or the default repository if
    :param:`name` is `None`.
    """
    repo_mgr = get_repository_manager()
    if name is None:
        repo = repo_mgr.get_default()
    else:
        repo = repo_mgr.get(name)
    return repo


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
            for left, right in iteritems_(init_map):
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
        self.__cmp_key = functools.cmp_to_key(self.__cmp_items)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            wr = [self.__get_weakref(val) for val in value]
        else:
            wr = self.__get_weakref(value)
        list.__setitem__(self, index, wr)

    def __getitem__(self, index):
        if isinstance(index, slice):
            val = [list.__getitem__(self, item)()
                   for item in range(index.start, index.stop)]
        else:
            val = list.__getitem__(self, index)()
        return val

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
        if len(self) == 0:
            raise StopIteration
        else:
            cnt = 0
            while cnt < len(self):
                yield self.__getitem__(cnt)
                cnt += 1

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
        list.extend(self, self.__sequence_to_weakrefs(sequence))

    def sort(self):
        list.sort(self, key=self.__cmp_key)

    def __get_weakref(self, value):
        return ref(value, self.__remove_by_weakref)

    def __remove_by_weakref(self, weakref):
        # Cleanup callback called on garbage collection.
        while True:
            try:
                self.__delitem__(list.index(self, weakref))
            except ValueError:
                break

    def __sequence_to_weakrefs(self, sequence):
        return [self.__get_weakref(el) for el in sequence]

    def __cmp_items(self, left_ref, right_ref):
        return (left_ref() > right_ref()) - (left_ref() < right_ref())


class WeakOrderedSet(MutableSet):
    """
    Ordered set storing weak references to its items.

    Based on a recipe by Raymond Hettinger
    (http://code.activestate.com/recipes/576694-orderedset/).
    """
    def __init__(self, iterable=None):
        MutableSet.__init__(self)
        self.end = end = []
        end += [None, end, end] # sentinel node for doubly linked list
        self.map = WeakKeyDictionary() # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, nxt = self.map.pop(key)
            prev[2] = nxt
            nxt[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __eq__(self, other):
        if isinstance(other, WeakOrderedSet):
            is_eq = len(self) == len(other) and list(self) == list(other)
        else:
            is_eq = set(self) == set(other)
        return is_eq


def generative(func):
    """
    Marks an instance method as generative.
    """
    def wrap(inst, *args, **kw):
        clone = type(inst).__new__(type(inst))
        clone.__dict__ = inst.__dict__.copy()
        return func(clone, *args, **kw)
    return update_wrapper(wrap, func)


def truncate(message, limit=500):
    """
    Truncates the message to the given limit length. The beginning and the
    end of the message are left untouched.
    """
    if len(message) > limit:
        trc_msg = ''.join([message[:limit // 2 - 2],
                           ' .. ',
                           message[len(message) - limit // 2 + 2:]])
    else:
        trc_msg = message
    return trc_msg


class TruncatingFormatter(Formatter):
    """
    Formatter that chops excessive logging argument strings to a defined
    limit. Useful e.g. to restrict logging output from request bodies.

    To use, pass a key "output_limit" to the "extra" argument in your
    logging calls. The logging message will then be truncated to the specified
    length.
    """
    def format(self, record):
        if record.args and hasattr(record, 'output_limit'):
            # Truncate all args to the set limit.
            record.args = tuple([truncate(arg, limit=record.output_limit)
                                 for arg in record.args])
        return Formatter.format(self, record)
