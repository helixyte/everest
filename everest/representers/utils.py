"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Representer utilities.

Created on May 18, 2011.
"""
from everest.representers.interfaces import IRepresenterRegistry
from pyramid.threadlocal import get_current_registry


__docformat__ = 'reStructuredText en'
__all__ = ['as_representer',
           'get_data_element_registry',
           ]


def as_representer(resource, content_type):
    """
    Adapts the given resource and content type to a representer.

    :param resource: resource to adapt.
    :param str content_type: content (MIME) type to create a
        representer for.
    """
    reg = get_current_registry()
    rpr_reg = reg.queryUtility(IRepresenterRegistry)
    rpr = rpr_reg.create(resource, content_type)
    if rpr is None:
        # Register a representer with default configuration on the fly.
        rpr_reg.register(type(resource), content_type)
        rpr = rpr_reg.create(resource, content_type)
    return rpr


def get_mapping_registry(content_type):
    """
    Returns the data element registry for the given content type (a Singleton).

    :Note: This only works after a representer for the given content type
        has been created.
    """
    reg = get_current_registry()
    rpr_reg = reg.queryUtility(IRepresenterRegistry)
    return rpr_reg.get_mapping_registry(content_type)
