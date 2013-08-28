"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 22, 2013.
"""
from collections import OrderedDict
from everest.constants import CARDINALITY_CONSTANTS
from everest.constants import DomainAttributeKinds
from everest.constants import ResourceAttributeKinds
from pyramid.compat import itervalues_
from pyramid.compat import string_types

__docformat__ = 'reStructuredText en'
__all__ = ['get_attribute_iterator',
           'is_terminal_attribute']


def get_attribute_iterator(obj):
    """
    """
    return itervalues_(obj.__everest_attributes__)


def is_terminal_attribute(attribute):
    return attribute.kind in (DomainAttributeKinds.TERMINAL,
                              ResourceAttributeKinds.TERMINAL)


def get_attribute_cardinality(attribute):
    if attribute.kind in (ResourceAttributeKinds.MEMBER,
                          DomainAttributeKinds.ENTITY):
        card = CARDINALITY_CONSTANTS.ONE
    elif attribute.kind in (ResourceAttributeKinds.COLLECTION,
                            DomainAttributeKinds.AGGREGATE):
        card = CARDINALITY_CONSTANTS.MANY
    else:
        raise ValueError('Can not determine cardinality for non-terminal '
                         'attributes.')
    return card



class AttributeValueMap(OrderedDict):
    def __init__(self, *args, **kw):
        OrderedDict.__init__(self, *args, **kw)
        self.__name_attr_map = {}

    def _get_attribute_attribute(self, attr):
        raise NotImplementedError('Abstract method.')

    def clear(self):
        OrderedDict.clear(self)
        self.__name_attr_map.clear()

    def __setitem__(self, attr, value): # specials not supported pylint: disable=W0221
        OrderedDict.__setitem__(self, attr, value)
        attr_name = self._get_attribute_attribute(attr)
        self.__name_attr_map[attr_name] = attr

    def __delitem__(self, attr): # specials not supported pylint: disable=W0221
        attr_name = self._get_attribute_attribute(attr)
        del self.__name_attr_map[attr_name]
        OrderedDict.__delitem__(self, attr)

    def __getitem__(self, item):
        if isinstance(item, string_types):
            item = self.__name_attr_map[item]
        return OrderedDict.__getitem__(self, item)

    def pop(self, key): # default not supported pylint: disable=W0221
        if isinstance(key, string_types):
            key = self.__name_attr_map.pop(key)
        return OrderedDict.pop(self, key)

