"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.j
"""
from everest.messaging import UserMessageChecker
from everest.messaging import UserMessageHandlingContextManager
from everest.mime import get_registered_mime_type_for_string
from everest.representers.utils import as_representer
from everest.resources.system import UserMessageMember
from everest.utils import get_traceback
from everest.views.interfaces import IResourceView
from paste.httpexceptions import HTTPInternalServerError # pylint: disable=F0401
from paste.httpexceptions import HTTPTemporaryRedirect # pylint: disable=F0401
from pyramid.threadlocal import get_current_request
from webob.exc import HTTPBadRequest
from webob.exc import HTTPConflict
from zope.interface import implements # pylint: disable=E0611,F0401
import logging
import re

__docformat__ = "reStructuredText en"
__all__ = ['ResourceView',
           'CollectionView',
           'MemberView',
           ]


class HttpWarningResubmit(HTTPTemporaryRedirect): # no __init__ pylint: disable=W0232
    """
    Special 307 HTTP Temporary Redirect exception which transports 
    """
    explanation = 'Your request triggered warnings. You may resubmit ' \
                  'the request under the given location to ignore ' \
                  'the warnings.'
    template = '%(explanation)s\r\n' \
               'Location: <a href="%(location)s">%(location)s</a>\r\n' \
               'Warning UserMessage: %(detail)s\r\n' \
               '<!-- %(comment)s -->'


class ResourceView(object):
    """
    Abstract base class for all resource views.
    
    Resource views know how to handle a number of things that can go wrong
    in a REST request.
    """

    implements(IResourceView)

    __context = None
    __request = None

    def __init__(self, context, request):
        if self.__class__ is ResourceView:
            raise NotImplementedError('Abstract class')
        self._logger = logging.getLogger(self.__class__.__name__)
        self.__context = context
        self.__request = request
        self.__representer = None

    @property
    def context(self):
        return self.__context

    @property
    def request(self):
        return self.__request

    @property
    def representer(self):
        if self.__representer is None:
            mime_type = \
              get_registered_mime_type_for_string(self.__request.content_type)
            self.__representer = as_representer(self.__context, mime_type)
        return self.__representer

    def _handle_unknown_exception(self, message, traceback):
        """
        Handles requests that triggered an unknown exception.
        
        Respond with a 500 "Internal Server Error".
        """
        self._logger.error('Request errors\n'
                           'Error message: %s\nTraceback:%s' %
                           (message, traceback))
        http_exc = HTTPInternalServerError(message)
        return self.request.get_response(http_exc)


class GetResourceView(ResourceView): # still abstract pylint: disable=W0223
    """
    Abstract base class for all collection views
    """

    def __init__(self, resource, request):
        if self.__class__ is GetResourceView:
            raise NotImplementedError('Abstract class')
        ResourceView.__init__(self, resource, request)

    def __call__(self):
        raise NotImplementedError('Abstract method.')


class PutOrPostResourceView(ResourceView): # still abstract pylint: disable=W0223
    """
    Abstract base class for all member views
    """

    def __init__(self, resource, request):
        if self.__class__ is PutOrPostResourceView:
            raise NotImplementedError('Abstract class')
        ResourceView.__init__(self, resource, request)

    def __call__(self):
        self._logger.debug('Request received on %s' % self.request.url)
        self._logger.debug('Request body:\n%s' % self.request.body)
        if len(self.request.body) == 0:
            # Empty body - return 400 Bad Request.
            response = self._handle_empty_body()
        else:
            checker = ViewUserMessageChecker()
            try:
                with UserMessageHandlingContextManager(checker):
                    data = self._extract_request_data()
                if not checker.vote is True:
                    response = checker.create_307_response()
                else:
                    with UserMessageHandlingContextManager(checker):
                        response = self._process_request_data(data)
                    if not checker.vote is True:
                        response = checker.create_307_response()
            except Exception, err: # catch Exception pylint: disable=W0703
                response = self._handle_unknown_exception(err.message,
                                                          get_traceback())
        return response

    def _extract_request_data(self):
        """
        Extracts the data from the representation submitted in the request
        body and returns it.
        """
        raise NotImplementedError('Abstract method.')

    def _process_request_data(self, data):
        """
        Processes the data extracted from the representation.
        
        Implementations of this method need to check for a conflict caused
        by the request data (e.g., if the slug for a new member in a POST
        request is already used) and call the :method:`_handle_conflict`
        method in case a conflict was detected.
        
        :param data: data returned by the :method:`_extract_request_data` 
          method.
        :returns: response object or dictionary
        """
        raise NotImplementedError('Abstract method.')

    def _handle_empty_body(self):
        """
        Handles requests with an empty body.
        
        Respond with a 400 "Bad Request".
        """
        http_exc = HTTPBadRequest("Request's body is empty!")
        return self.request.get_response(http_exc)

    def _handle_conflict(self, name):
        """
        Handles requests that triggered a conflict.
        
        Respond with a 409 "Conflict"
        """
        err = HTTPConflict('Member "%s" already exists!' % name).exception
        return self.request.get_response(err)

    def _status(self, wsgi_http_exc_class):
        """
        Convenience method to obtain a status string from the given HTTP
        exception class.
        """
        return '%(code)s %(title)s' % wsgi_http_exc_class.__dict__


class ViewUserMessageChecker(UserMessageChecker):
    """
    Custom user message checker for views.
    """
    __guid_pattern = re.compile(".*ignore-message=([a-z0-9\-]{36})")

    def check(self):
        """
        Implements user message checking for views.
        
        Checks if the current request has an explicit "ignore-message" 
        parameter (a GUID) pointing to a message with identical text from a 
        previous request, in which case further processing is allowed.        
        """
        request = get_current_request()
        ignore_guid = request.params.get('ignore-message')
        coll = request.root['_messages']
        vote = False
        if ignore_guid:
            ignore_mb = coll.get(ignore_guid)
            if not ignore_mb is None and ignore_mb.text == self.message.text:
                vote = True
        return vote

    def create_307_response(self):
        """
        Creates a 307 "Temporary Redirect" response including a HTTP Warning 
        header with code 299 that contains the user message received during
        processing the request.
        """
        request = get_current_request()
        msg_mb = UserMessageMember(self.message)
        coll = request.root['_messages']
        coll.add(msg_mb)
        # Figure out the new location URL.
        qs = self.__get_new_query_string(request.query_string,
                                         self.message.slug)
        resubmit_url = "%s?%s" % (request.path_url, qs)
        headers = [('Location', resubmit_url),
                   ('Warning', '299 %s' % self.message.text),
#                       ('Content-Type', cnt_type),
                   ]
        http_exc = HttpWarningResubmit(self.message.text, headers=headers)
        return request.get_response(http_exc)

    def __get_new_query_string(self, old_query_string, new_guid):
        # In absence of a function to manipulate the URL query string in place
        # (the request URL params are read-only), resorting to explicit
        # string manipulation seems the safest thing to do.
        if old_query_string:
            # Make sure to *replace* any given ignore message.
            match = self.__guid_pattern.match(old_query_string)
            if match:
                cur_guid = match.groups()[0]
                qs = re.sub(cur_guid, new_guid, old_query_string)
            else:
                qs = "%s&ignore-message=%s" % (old_query_string,
                                               new_guid)
        else:
            qs = "ignore-message=%s" % new_guid
        return qs
