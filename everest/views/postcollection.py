"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from everest.exceptions import WarningException
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
    A View for processing POST requests.

    The client POSTs a representation of the Member to the URI of the
    Collection. If the Member Resource was created successfully, the server
    responds with a status code of 201 and a Location header that contains the
    IRI of the newly created Entry Resource and a representation of that Entry
    in the body of the response.

    See http://bitworking.org/projects/atom/rfc5023.html#post-to-create
    """

    def __init__(self, collection, request):
        CollectionView.__init__(self, collection, request)

    def __call__(self):
        self._logger.debug('POST Request received on %s' % self.request.url)
        self._logger.debug('POST Request body:\n%s' % self.request.body)

        if len(self.request.body) == 0:
            result = self._handle_empty_body()
        else:
            try:
                member = self._create_member()
            except WarningException, err:
                result = self._handle_warning_exception(err.message)
            except Exception, err:
                result = self._handle_unknown_exception(err.message,
                                                        get_traceback())
            else:
                if self.context.get(member.__name__) is not None:
                    result = self._handle_conflict(member.__name__)
                else:
                    self.context.add(member)
                    self.request.response_status = self._status(HTTPCreated)
                    self.request.response_headerlist = [
                        ('Location',
                         resource_to_url(member, request=self.request))
                        ]
                    result = {'context': member}
        return result

    def _create_member(self):
        """
        Create a new member resource from the incoming request.
        
        If this method raises a :class:`everest.exceptions.WarningException`,
        a 307 response is generated with the LOCATION header pointing to a
        new URL that allows the client to resubmit the same request without
        triggering the warning.
        
        :returns: :class:`everest.resources.base.Member` instance.
        """
        rpr = as_representer(self.context, self.request.content_type)
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = rpr.from_string(self.request.body)
        return member
