"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from everest.url import resource_to_url
from everest.views.base import PutOrPostResourceView
from webob.exc import HTTPCreated

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
        return self.representer.from_string(self.request.body)

    def _process_request_data(self, data):
        if self.context.get(data.__name__) is not None:
            # We have a member with the same name - 409 Conflict.
            response = self._handle_conflict(data.__name__)
        else:
            # All is good - 201 Created.
            self.context.add(data)
            self.request.response.status = self._status(HTTPCreated)
            self.request.response.headerlist = [
                ('Location',
                 resource_to_url(data, request=self.request))
                ]
            response = {'context' : data}
        return response
