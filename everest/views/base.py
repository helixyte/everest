"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.j
"""

from everest.views.interfaces import IResourceView
from webob.exc import HTTPBadRequest
from zope.interface import implements # pylint: disable=E0611,F0401
from paste.httpexceptions import HTTPTemporaryRedirect
import logging
from webob.exc import HTTPConflict

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
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def context(self):
        return self.__context

    @property
    def request(self):
        return self.__request

    def _status(self, wsgi_http_exc_class):
        return '%(code)s %(title)s' % wsgi_http_exc_class.__dict__

    def _handle_empty_body(self):
        err = HTTPBadRequest("Request's body is empty!").exception
        return self.request.get_response(err)

    def _handle_warning_exception(self, message):
        # Warning exceptions trigger a special 307 "Temporary Redirect"
        # response.
        resubmit_url = None
        http_exc = HTTPTemporaryRedirect(message,
                                         location=resubmit_url)
        return self.request.get_response(http_exc.exception)

    def _handle_unknown_exception(self, message, traceback):
        # Any other exception is responded to with a 400 "Bad Request".
        self._logger.debug('POST Request errors\n'
                           'Error message: %s\nTraceback:%s' %
                           (message, traceback))
        err = HTTPBadRequest(message).exception
        return self.request.get_response(err)

    def _handle_conflict(self, name):
        err = HTTPConflict('Member "%s" already exists!' % name).exception
        return self.request.get_response(err)


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

