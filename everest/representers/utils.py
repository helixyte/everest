"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Representer utilities.

Created on May 18, 2011.
"""

from everest.representers.interfaces import IDataElementRegistry
from everest.representers.interfaces import IRepresenter
from pyramid.threadlocal import get_current_registry


__docformat__ = 'reStructuredText en'
__all__ = ['as_representer',
           'get_data_element_registry',
           ]


def as_representer(resource, content_type_string):
    """
    Adapts the given resource and content type to a representer.

    :param resource: resource to adapt.
    :param str content_type_string: content (MIME) type to create a
        representer for.
    """
    reg = get_current_registry()
    return reg.getAdapter(resource, IRepresenter, content_type_string)


def get_data_element_registry(content_type):
    """
    Returns the data element registry for the given content type (a Singleton).

    :Note: This only works after a representer for the given content type
        has been created.
    """
    reg = get_current_registry()
    return reg.getUtility(IDataElementRegistry, content_type.mime_string)
