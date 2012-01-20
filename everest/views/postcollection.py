"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from everest.staging import STAGING_CONTEXT_MANAGERS
from everest.url import resource_to_url
from everest.views.base import PutOrPostResourceView
from webob.exc import HTTPCreated
from zope.component import createObject as create_object # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['PostCollectionView',
           ]


class PostCollectionView(PutOrPostResourceView):
    """
    View for POST requests on collection resources.

    The client POSTs a representation of the member to the URI of the
    collection. If the new member resource was created successfully, the 
    server responds with a status code of 201 and a Location header that 
    contains the IRI of the newly created resource and a representation 
    of it in the body of the response.

    See http://bitworking.org/projects/atom/rfc5023.html#post-to-create
    """

    def _extract_request_data(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self.representer.from_string(self.request.body)
        return member

    def _process_request_data(self, data):
        if self.context.get(data.__name__) is not None:
            # We have a member with the same name - 409 Conflict.
            response = self._handle_conflict(data.__name__)
        else:
            # All is good - 201 Created.
            self.context.add(data)
            self.request.response_status = self._status(HTTPCreated)
            self.request.response_headerlist = [
                ('Location',
                 resource_to_url(data, request=self.request))
                ]
            response = {'context' : data}
        return response
