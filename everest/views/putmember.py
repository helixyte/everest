"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from everest.staging import STAGING_CONTEXT_MANAGERS
from everest.url import resource_to_url
from everest.views.base import MemberView
from webob.exc import HTTPOk
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

    def _extract_request_data(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            new_member_data = \
                self.representer.data_from_representation(self.request.body)
        return new_member_data

    def _process_request_data(self, data):
        initial_name = self.context.__name__
        self.context.update_from_data(data)
        current_name = self.context.__name__
        self.request.response_status = self._status(HTTPOk)
        # FIXME: add conflict detection # pylint: disable=W0511
        if initial_name != current_name:
            self.request.response_headerlist = \
                [('Location',
                  resource_to_url(self.context, request=self.request))]
        # We return the representation of the updated member to
        # assist the client in doing the right thing. 
        # Not all clients give access to the Response headers and we 
        # cannot find the new location when HTTP/1.1 301 is returned.
        return {'context' : self.context}


