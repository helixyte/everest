"""
Delete member view.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 24, 2011.
"""
from pyramid.httpexceptions import HTTPOk

from everest.utils import get_traceback
from everest.views.base import ResourceView


__docformat__ = 'reStructuredText en'
__all__ = ['DeleteMemberView',
           ]


class DeleteMemberView(ResourceView):
    """
    A View for processing DELETE requests.

    The client sends a DELETE request to the URI of a Member Resource. If the
    deletion is successful, the server responds with a status code of 200.

    If the parent of the context is a collection, the member is removed from
    it. Only if the parent collection is the root collection this will trigger
    the deletion of the context from the backend. If the parent of the context
    is a member, the relationship between the parent and the context will be
    severed. If the URL referred to a terminal attribute, it is set to None.
    """
    def __call__(self):
        self._logger.debug('DELETE Request received on %s' % self.request.url)
        is_terminal = self.request.view_name != ''
        if not is_terminal:
            try:
                self.context.remove()
            except Exception as err: # catch Exception pylint: disable=W0703
                response = self._handle_unknown_exception(str(err),
                                                          get_traceback())
            else:
                response = self.request.get_response(HTTPOk())
        else:
            # Support for setting member attributes to None.
            attr = self.request.path.split('/')[-1]
            setattr(self.context, attr, None)
            response = self.request.get_response(HTTPOk())
        return response

