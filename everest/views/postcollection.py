"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from everest.representers.utils import as_representer
from everest.staging import STAGING_CONTEXT_MANAGERS
from everest.url import resource_to_url
from everest.utils import get_traceback
from everest.views.base import CollectionView
from webob.exc import HTTPCreated
from zope.component import createObject as create_object # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['PostCollectionView',
           ]


class PostCollectionView(CollectionView):
    """
    View for POST requests on collection resources.

    The client POSTs a representation of the member to the URI of the
    collection. If the new member resource was created successfully, the 
    server responds with a status code of 201 and a Location header that 
    contains the IRI of the newly created resource and a representation 
    of it in the body of the response.

    See http://bitworking.org/projects/atom/rfc5023.html#post-to-create
    """

    def __init__(self, collection, request):
        CollectionView.__init__(self, collection, request)

    def __call__(self):
        self._logger.debug('POST Request received on %s' % self.request.url)
        self._logger.debug('POST Request body:\n%s' % self.request.body)
        if len(self.request.body) == 0:
            # Empty body - return 400 Bad Request.
            response = self._handle_empty_body()
        else:
            try:
                member = self._create_member()
            except Exception, err: # catch Exception pylint: disable=W0703
                # Unknown exception - return 400 Bad Request. 
                response = self._handle_unknown_exception(err.message,
                                                          get_traceback())
            else:
                if self._has_user_messages():
                    # Some user messages were collected during the call - 
                    # possibly return a 307 reponse with a warning.
                    response = self._handle_user_messages()
                    if response is None:
                        # User message ignored - continue processing.
                        response = self.__handle_created(member)
                else:
                    # All good - continue processing.
                    response = self.__handle_created(member)
        return response

    def _create_member(self):
        """
        Create a new member resource from the incoming request.
        
        If this method raises a :class:`everest.exceptions.WarningException`,
        a 307 response is generated with the LOCATION header pointing to a
        new URL that allows the client to resubmit the same request without
        triggering the warning. The body of the response contains the text
        of the warning.
        
        :returns: :class:`everest.resources.base.Member` instance.
        """
        rpr = as_representer(self.context, self.request.content_type)
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = rpr.from_string(self.request.body)
        return member

    def __handle_created(self, member):
        if self.context.get(member.__name__) is not None:
            # We have a member with the same name - 409 Conflict.
            response = self._handle_conflict(member.__name__)
        else:
            # All is good - 301 Created.
            self.context.add(member)
            self.request.response_status = self._status(HTTPCreated)
            self.request.response_headerlist = [
                ('Location',
                 resource_to_url(member, request=self.request))
                ]
            response = {'context' : member}
        return response
