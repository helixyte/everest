"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from everest.representers.utils import as_representer
from everest.staging import STAGING_CONTEXT_MANAGERS
from everest.url import resource_to_url
from everest.views.base import CollectionView
from webob.exc import HTTPBadRequest
from webob.exc import HTTPConflict
from webob.exc import HTTPCreated
from webob.exc import HTTPException
from zope.component import createObject as create_object # pylint: disable=E0611,F0401
import logging

__docformat__ = 'reStructuredText en'
__all__ = ['PostCollectionView',
           ]


class PostCollectionView(CollectionView):
    """
    A View for processing POST requests.

    The client POSTs a representation of the Member to the URI of the
    Collection. If the Member Resource was created successfully, the server
    responds with a status code of 201 and a Location header that contains the
    IRI of the newly created Entry Resource and a representation of that Entry
    in the body of the response.

    See http://bitworking.org/projects/atom/rfc5023.html#post-to-create
    """

    __logger = logging.getLogger(__name__)

    def __init__(self, collection, request):
        CollectionView.__init__(self, collection, request)

    def __call__(self):
        self.__logger.debug('POST Request received on %s' % self.request.url)
        self.__logger.debug('POST Request body:\n%s' % self.request.body)

        try:
            member = self.__create_member(self.request.body)
        except HTTPException, err:
            return self.request.get_response(err)
        else:
            self.context.add(member)
            self.request.response_status = self._status(HTTPCreated)
            self.request.response_headerlist = [
                ('Location', resource_to_url(member, request=self.request))
                ]
        return {'context': member}

    def __create_member(self, request_body):
        if len(request_body) == 0:
            raise HTTPBadRequest("Request's body is empty!").exception
        # Create representation and deserialize request.
        rpr = as_representer(self.context, self.request.content_type)
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            try:
                member = rpr.from_string(request_body)
            except Exception, err:
                self.__logger.debug('POST Request errors:\n%s' % err)
                raise HTTPBadRequest(err).exception
        if self.context.get(member.__name__) is not None:
            raise HTTPConflict('Member already exists!').exception
        else:
            return member
