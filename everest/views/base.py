"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on Oct 7, 2011.j
"""

from everest.views.interfaces import IResourceView
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = "reStructuredText en"
__all__ = ['ResourceView',
           'CollectionView',
           'MemberView',
           ]


class ResourceView(object):
    """
    Abstract base class for all resource views
    """

    implements(IResourceView)

    __context = None
    __request = None

    def __init__(self, context, request):
        if self.__class__ is ResourceView:
            raise NotImplementedError('Abstract class')
        self.__context = context
        self.__request = request

    @property
    def context(self):
        return self.__context

    @property
    def request(self):
        return self.__request

    def _status(self, wsgi_http_exc_class):
        return '%(code)s %(title)s' % wsgi_http_exc_class.__dict__


class CollectionView(ResourceView):
    """
    Abstract base class for all collection views
    """

    def __init__(self, collection, request):
        if self.__class__ is CollectionView:
            raise NotImplementedError('Abstract class')
        ResourceView.__init__(self, collection, request)


class MemberView(ResourceView):
    """
    Abstract base class for all member views
    """

    def __init__(self, member, request):
        if self.__class__ is MemberView:
            raise NotImplementedError('Abstract class')
        ResourceView.__init__(self, member, request)

