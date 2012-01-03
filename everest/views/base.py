"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.j
"""

from everest.entities.system import Message
from everest.messaging import UserMessageHandler
from everest.representers.utils import as_representer
from everest.resources.system import MessageMember
from everest.utils import get_traceback
from everest.views.interfaces import IResourceView
from paste.httpexceptions import HTTPInternalServerError
from paste.httpexceptions import HTTPTemporaryRedirect
from webob.exc import HTTPBadRequest
from webob.exc import HTTPConflict
from zope.interface import implements
import logging
import os
import re

__docformat__ = "reStructuredText en"
__all__ = ['ResourceView',
           'CollectionView',
           'MemberView',
           ]


class HttpWarningResubmit(HTTPTemporaryRedirect):
    """
    Special 307 HTTP Temporary Redirect exception which transports 
    """
    explanation = 'Your request triggered warnings. You may resubmit ' \
                  'the request under the given location to ignore ' \
                  'the warnings.'
    template = '%(explanation)s\r\n' \
               'Location: <a href="%(location)s">%(location)s</a>\r\n' \
               'Warning Message: %(detail)s\r\n' \
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
    __guid_pattern = re.compile(".*ignore-message=([a-z0-9\-]{36})")

    def __init__(self, context, request):
        if self.__class__ is ResourceView:
            raise NotImplementedError('Abstract class')
        self._logger = logging.getLogger(self.__class__.__name__)
        self.__context = context
        self.__request = request
        self.__representer = None
        self.__message_handler = UserMessageHandler()
        UserMessageHandler.register(self.__message_handler, request)
        request.add_finished_callback(UserMessageHandler.unregister)

    def __call__(self):
        self._logger.debug('Request received on %s' % self.request.url)
        self._logger.debug('Request body:\n%s' % self.request.body)
        if len(self.request.body) == 0:
            # Empty body - return 400 Bad Request.
            response = self._handle_empty_body()
        else:
            try:
                data = self._extract_request_data()
            except Exception, err: # catch Exception pylint: disable=W0703
                response = self._handle_unknown_exception(err.message,
                                                          get_traceback())
            else:
                if self._has_user_messages():
                    # Some user messages were collected during the call - 
                    # possibly return a 307 reponse with a warning.
                    response = self._handle_user_messages()
                    if response is None:
                        # User message ignored - continue processing.
                        try:
                            response = self._process_request_data(data)
                        except Exception, err: # catch Exception pylint: disable=W0703
                            response = \
                                self._handle_unknown_exception(err.message,
                                                               get_traceback())
                else:
                    try:
                        response = self._process_request_data(data)
                    except Exception, err:  # catch Exception pylint: disable=W0703
                        response = \
                            self._handle_unknown_exception(err.message,
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

    @property
    def context(self):
        return self.__context

    @property
    def request(self):
        return self.__request

    @property
    def representer(self):
        if self.__representer is None:
            self.__representer = \
                as_representer(self.__context, self.__request.content_type)
        return self.__representer

    def _handle_empty_body(self):
        """
        Handles requests with an empty body.
        
        Respond with a 400 "Bad Request".
        """
        http_exc = HTTPBadRequest("Request's body is empty!")
        return self.request.get_response(http_exc)

    def _handle_unknown_exception(self, message, traceback):
        """
        Handles requests that triggered an unknown exception.
        
        Respond with a 500 "Internal Server Error".
        """
        self._logger.debug('Request errors\n'
                           'Error message: %s\nTraceback:%s' %
                           (message, traceback))
        http_exc = HTTPInternalServerError(message)
        return self.request.get_response(http_exc)

    def _handle_conflict(self, name):
        """
        Handles requests that triggered a conflict.
        
        Respond with a 409 "Conflict"
        """
        err = HTTPConflict('Member "%s" already exists!' % name).exception
        return self.request.get_response(err)

    def _handle_user_messages(self):
        """
        Handles user messages that were sent during request processing.
        
        Respond with a 307 "Temporary Redirect" including a HTTP Warning 
        header with code 299 that contains the user concatenated user
        messages. If the request has an explicit "ignore-message" parameter 
        pointing to an identical message from a previous request, None is
        returned, indicating that the request should be processed as if no
        warning had occurred.
        """
        text = os.linesep.join(self.__message_handler.get_messages())
        ignore_guid = self.request.params.get('ignore-message')
        coll = self.request.root['_messages']
        modify_response = True
        if ignore_guid:
            ignore_mb = coll.get(ignore_guid)
            if not ignore_mb is None and ignore_mb.text == text:
                modify_response = False
        if modify_response:
            msg = Message(text)
            msg_mb = MessageMember(msg)
            coll.add(msg_mb)
            # Figure out the new location URL.
            qs = self.__get_new_query_string(self.request.query_string,
                                             msg.slug)
            resubmit_url = "%s?%s" % (self.request.path_url, qs)
            headers = [('Location', resubmit_url),
                       ('Warning', '299 %s' % text),
#                       ('Content-Type', cnt_type),
                       ]
            http_exc = HttpWarningResubmit(text, headers=headers)
            response = self.request.get_response(http_exc)
        else:
            response = None
        return response

    def _has_user_messages(self):
        """
        Check if user messages have been sent during request processing. 
        """
        return self.__message_handler.has_messages()

    def _status(self, wsgi_http_exc_class):
        """
        Convenience method to obtain a status string from the given HTTP
        exception class.
        """
        return '%(code)s %(title)s' % wsgi_http_exc_class.__dict__

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


class CollectionView(ResourceView): # still abstract pylint: disable=W0223
    """
    Abstract base class for all collection views
    """

    def __init__(self, collection, request):
        if self.__class__ is CollectionView:
            raise NotImplementedError('Abstract class')
        ResourceView.__init__(self, collection, request)


class MemberView(ResourceView): # still abstract pylint: disable=W0223
    """
    Abstract base class for all member views
    """

    def __init__(self, member, request):
        if self.__class__ is MemberView:
            raise NotImplementedError('Abstract class')
        ResourceView.__init__(self, member, request)

