"""
Resource link.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 29, 2011.
"""
from everest.resources.interfaces import IResourceLink
from everest.resources.utils import resource_to_url
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['Link',
           ]


@implementer(IResourceLink)
class Link(object):
    """
    A resource link.

    :note: The URL for the linked resource is created lazily; at
      instantiation time, we may not have a request to generate the URL.
    """
    def __init__(self, linked_resource, rel,
                 type=None, title=None, length=None): # pylint: disable=W0622
        self.__linked_resource = linked_resource
        self.rel = rel
        self.type = type
        self.title = title
        self.length = length

    @property
    def href(self):
        return resource_to_url(self.__linked_resource)
