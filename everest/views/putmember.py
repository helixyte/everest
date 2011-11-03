"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from everest.representers.utils import as_representer
from everest.staging import STAGING_CONTEXT_MANAGERS
from everest.url import resource_to_url
from everest.views.base import MemberView
from webob.exc import HTTPBadRequest
from webob.exc import HTTPException
from webob.exc import HTTPMovedPermanently
from zope.component import createObject as create_object # pylint: disable=E0611,F0401
import logging

__docformat__ = 'reStructuredText en'
__all__ = ['PutMemberView',
           ]

class PutMemberView(MemberView):
    """
    A View for processing PUT requests

    The client sends a PUT request to store a representation of a Member
    Resource. If the request is successful, the server responds with a status
    code of 200.

    See http://bitworking.org/projects/atom/rfc5023.html#edit-via-PUT
    """

    __logger = logging.getLogger(__name__)

    def __init__(self, member, request):
        MemberView.__init__(self, member, request)

    def __call__(self):
        self.__logger.debug('PUT Request received on %s' % self.request.url)
        self.__logger.debug('PUT Request body:\n%s' % self.request.body)

        initial_url = resource_to_url(self.context, request=self.request)
        try:
            self.__update_context(self.request.body)
        except HTTPException, e:
            return self.request.get_response(e)
        else:
            current_url = resource_to_url(self.context, request=self.request)
            # FIXME: pylint:disable=W0511
            #        Return HTTPConflict if the new location exists.
            if initial_url != current_url:
                self.request.response_status = \
                            self._status(HTTPMovedPermanently)
                self.request.response_headerlist = [('Location', current_url)]
            # It is not neccessary in ATOMPUB to return the representation
            # of the member with a response to PUT but due to Adobe Flex's
            # HTTPService limitations we return the representation to a Member
            # to assist Flex in doing the right thing. Flex does not give
            # access to the Response headers and we cannot find the new
            # location when HTTP/1.1 301 is returned.
            return {'context': self.context}

    def __update_context(self, request_body):
        if len(request_body) == 0:
            raise HTTPBadRequest("Request's body is empty!").exception
        rpr = as_representer(self.context, self.request.content_type)
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            try:
                new_member_data = rpr.data_from_representation(request_body)
            except Exception, err:
                self.__logger.debug('PUT Request errors:\n%s' % err)
                raise HTTPBadRequest(err).exception
        self.context.update_from_data(new_member_data)
