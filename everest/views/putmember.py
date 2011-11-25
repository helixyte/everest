"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from everest.representers.utils import as_representer
from everest.staging import STAGING_CONTEXT_MANAGERS
from everest.url import resource_to_url
from everest.utils import get_traceback
from everest.views.base import MemberView
from webob.exc import HTTPMovedPermanently
from zope.component import createObject as create_object # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['PutMemberView',
           ]


class PutMemberView(MemberView):
    """
    View for PUT requests on member resources.

    The client sends a PUT request to store a representation of a Member
    Resource. If the request is successful, the server responds with a status
    code of 200.

    See http://bitworking.org/projects/atom/rfc5023.html#edit-via-PUT
    """

    def __init__(self, member, request):
        MemberView.__init__(self, member, request)

    def __call__(self):
        self._logger.debug('PUT Request received on %s' % self.request.url)
        self._logger.debug('PUT Request body:\n%s' % self.request.body)
        if len(self.request.body) == 0:
            # Empty body - return 400 Bad Request.
            response = self._handle_empty_body()
        else:
            initial_url = resource_to_url(self.context, request=self.request)
            try:
                self._update_member()
            except Exception, err: # catch Exception pylint: disable=W0703
                response = self._handle_unknown_exception(err.message,
                                                          get_traceback())
            else:
                if self._has_user_messages():
                    # Some user messages were collected during the call - 
                    # possibly return a 307 reponse with a warning.
                    response = self._handle_user_messages()
                    if response is None:
                        # User message ignored - return 301 Created.
                        response = self.__handle_updated(initial_url)
                else:
                    response = self.__handle_updated(initial_url)
        return response

    def _update_member(self):
        """
        Update the context member resource from the incoming request.
        """
        rpr = as_representer(self.context, self.request.content_type)
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            new_member_data = rpr.data_from_representation(self.request.body)
        self.context.update_from_data(new_member_data)

    def __handle_updated(self, initial_url):
        current_url = resource_to_url(self.context, request=self.request)
        # FIXME: pylint:disable=W0511
        #        Return HTTPConflict if the new location exists.
        if initial_url != current_url:
            self.request.response_status = self._status(HTTPMovedPermanently)
            self.request.response_headerlist = [('Location', current_url)]
        # We return the representation of the updated member to
        # assist the client in doing the right thing. 
        # Not all clients give access to the Response headers and we 
        # cannot find the new location when HTTP/1.1 301 is returned.
        return {'context' : self.context}

