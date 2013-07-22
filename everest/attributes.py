"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 22, 2013.
"""
from everest.constants import DomainAttributeKinds
from everest.constants import ResourceAttributeKinds
from pyramid.compat import itervalues_

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
