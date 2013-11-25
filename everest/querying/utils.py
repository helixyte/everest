"""
Querying utilities.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 19, 2011.
"""
from everest.querying.interfaces import IFilterSpecificationFactory
from everest.querying.interfaces import IOrderSpecificationFactory
from pyramid.threadlocal import get_current_registry

__docformat__ = 'reStructuredText en'
__all__ = ['get_filter_specification_factory',
           'get_order_specification_factory',
           ]


def get_filter_specification_factory():
    """
    Returns the object registered as filter specification factory utility.

    :returns: object implementing
        :class:`everest.querying.interfaces.IFilterSpecificationFactory`
    """
    reg = get_current_registry()
    return reg.getUtility(IFilterSpecificationFactory)


def get_order_specification_factory():
    """
    Returns the object registered as order specification factory utility.

    :returns: object implementing
        :class:`everest.querying.interfaces.IOrderSpecificationFactory`
    """
    reg = get_current_registry()
    return reg.getUtility(IOrderSpecificationFactory)
