"""
Delete member view.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 24, 2011.
"""
from everest.utils import get_traceback
from everest.views.base import ResourceView
from pyramid.httpexceptions import HTTPOk

__docformat__ = 'reStructuredText en'
__all__ = ['DeleteMemberView',
           ]


class DeleteMemberView(ResourceView):
    """
    A View for processing DELETE requests

    The client sends a DELETE request to the URI of a Member Resource. If the
    deletion is successful, the server responds with a status code of 200.

    In a RESTful server DELETE does not always mean "delete a record from the
    database". See RESTful Web Services and REST in Practice books.

    See http://bitworking.org/projects/atom/rfc5023.html#delete-via-DELETE
    """

    def __call__(self):
        self._logger.debug('DELETE Request received on %s' % self.request.url)
        try:
            self.context.__parent__.remove(self.context)
        except Exception as err: # catch Exception pylint: disable=W0703
            response = self._handle_unknown_exception(str(err),
                                                      get_traceback())
        else:
            response = self.request.get_response(HTTPOk())
        return response

