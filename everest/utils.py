"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on Oct 7, 2011.
"""

from sqlalchemy.util import OrderedDict as _SqlAlchemyOrderedDict
from weakref import ref
from zope.component import IFactory # pylint: disable=E0611,F0401
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
import re

__docformat__ = 'reStructuredText en'
__all__ = ['BidirectionalLookup',
           'OrderedDict',
           'check_email',
           'classproperty',
           'get_factory',
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


def get_factory(name):
    """
    Returns a factory for the given name.

    :param str name: name of the collection to return
    :retrns: an object implementing :class:`zope.component.IFactory`
    """
    return get_utility(IFactory, name)



class BidirectionalLookup(object):

    def __init__(self, init_map=None):
        self.__left_map = dict()
        self.__right_map = dict()
        if not init_map is None:
            for left, right in init_map.iteritems():
                self.__setitem__(left, right)

    def __setitem__(self, left_item, right_item):
        cls_in_tag_map = right_item in self.__left_map
        tag_in_cls_map = left_item in self.__right_map
        if cls_in_tag_map or tag_in_cls_map \
            and not (cls_in_tag_map and tag_in_cls_map):
            raise ValueError('One of the items %s and %s is '
                             'already included in the '
                             'BirectionalLookup.' % (left_item, right_item))
        else:
            self.__left_map[right_item] = left_item
            self.__right_map[left_item] = right_item

    def __delitem__(self, left_or_right_item):
        if left_or_right_item in self.__left_map:
            del self.__left_map[left_or_right_item]
        elif left_or_right_item in self.__right_map:
            del self.__right_map[left_or_right_item]
        else:
            raise KeyError('%s is not included in the '
                           'BidirectonalLookup.' % (left_or_right_item,))

    def __getitem__(self, left_or_right_item):
        if left_or_right_item in self.__left_map:
            return self.__left_map[left_or_right_item]
        elif left_or_right_item in self.__right_map:
            return self.__right_map[left_or_right_item]
        else:
            raise KeyError('%s is not included in the '
                           'BidirectonalLookup.' % (left_or_right_item,))

    def __contains__(self, left_or_right_item):
        return (left_or_right_item in self.__left_map) or \
            (left_or_right_item in self.__right_map)

    def left_keys(self):
        return self.__left_map.keys()

    def right_keys(self):
        return self.__right_map.keys()

    def left_values(self):
        return self.__left_map.values()

    def right_values(self):
        return self.__right_map.values()

    def left_items(self):
        return self.__left_map.items()

    def right_items(self):
        return self.__right_map.items()


# We just redefine this here - perhaps we want to have our own implementation
# later.
OrderedDict = _SqlAlchemyOrderedDict


class WeakList(list):
    """
    List containing weakly referenced items

    All objects stored in a weak list are only weakly referenced, but
    accessing an element returns a strong reference. If an object referenced
    by an element in a weak list dies, the corresponding weak reference is
    removed automatically.

    @note: only weakly referenceable objects can be stored
    """

    def __init__(self, sequence=None):
        list.__init__(self)
        if not sequence is None:
            self.extend(sequence)

    def __setitem__(self, index, value):
        list.__setitem__(self, index, self.__get_ref(value))

    def __getitem__(self, index):
        return list.__getitem__(self, index)()

    def __setslice__(self, start, stop, sequence):
        list.__setslice__(self, start, stop,
                          map(self.__get_ref, sequence)) # map pylint: disable-msg=W0141

    def __getslice__(self, start, stop):
        return [item() for item in list.__getslice__(self, start, stop)]

    def __contains__(self, value):
        return list.__contains__(self, self.__get_ref(value))

    def __add__(self, sequence):
        new_wl = WeakList(sequence)
        new_wl.extend(self)
        return new_wl

    def __iter__(self):
        return self.__get_iterator()

    def append(self, value):
        list.append(self, self.__get_ref(value))

    def count(self, value):
        return list.count(self, self.__get_ref(value))

    def index(self, value):
        return list.index(self, self.__get_ref(value))

    def insert(self, position, value):
        list.insert(self, position, self.__get_ref(value))

    def pop(self):
        item_ref = list.pop(self)
        return item_ref()

    def remove(self, value):
        self.__delitem__(self.index(value))

    def extend(self, sequence):
        list.extend(self, self.__convert_seq_to_refs(sequence))

    def sort(self):
        list.sort(self, self.__cmp_items)

    def __get_ref(self, value):
        """

        @returns: a weak reference to the given value (:function:`weakref.ref`)
        """
        return ref(value, self.__remove_by_ref)

    def __remove_by_ref(self, item_ref):
        #: Cleanup callback. Removes all occurrences of the given weak ref.
        while True:
            try:
                self.__delitem__(list.index(self, item_ref))
            except ValueError:
                break

    def __convert_seq_to_refs(self, sequence):
        #: Replaces all items in the given sequence with weak references. Does
        #: nothing if :param:`sequence` is already a :class:`WeakList`.
        if not isinstance(sequence, WeakList):
            refs = map(self.__get_ref, sequence) # map pylint: disable-msg=W0141
        else:
            refs = sequence
        return refs

    def __cmp_items(self, left_item_ref, right_item_ref):
        #: Compare function.
        return cmp(left_item_ref(), right_item_ref())

    def __get_iterator(self):
        #: Returns an iterator over the weak list.
        count = 0
        while count < len(self):
            yield self.__getitem__(count)
            count += 1
        else:
            raise StopIteration
